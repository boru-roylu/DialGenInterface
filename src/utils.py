import sys

sys.path.append('src')

import json
import os
import time

from bs4 import BeautifulSoup as bs
import decouple
import openai
import yaml

import config

MODEL = decouple.config("LLM_VERSION")
MAX_NUM_OPENAI_API_RETRY = decouple.config("MAX_NUM_OPENAI_API_RETRY",
                                           cast=int)
MAX_NUM_SUBDIALOG_RETRY = decouple.config("MAX_NUM_SUBDIALOG_RETRY", cast=int)
API_COOLDOWN = decouple.config("API_COOLDOWN", cast=int)


def read_yaml(path):
    with open(path, 'r') as f:
        y = yaml.load(f, Loader=yaml.FullLoader)
    return y


def save_yaml(filename, dic):
    with open(filename, 'w') as f:
        yaml.Dumper.ignore_aliases = lambda self, data: True
        yaml.dump(dic, f, Dumper=yaml.Dumper, sort_keys=False)


def save_seed_yaml(summaries, subdialogs, path):
    ret = {'summaries': summaries, 'subdialogs': subdialogs}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        yaml.dump(ret, f)


def chatgpt(scenario, prompt, api_key, n=1, temperature=0.85, stop=None):
    result = None
    cnt = 0
    max_tokens = 512
    while result is None and cnt < MAX_NUM_OPENAI_API_RETRY:
        try:
            msg = openai.ChatCompletion.create(api_key=api_key,
                                               model=MODEL,
                                               messages=[
                                                   {
                                                       "role": "system",
                                                       "content": scenario
                                                   },
                                                   {
                                                       "role": "user",
                                                       "content": prompt
                                                   },
                                               ],
                                               temperature=temperature,
                                               max_tokens=max_tokens,
                                               n=n,
                                               frequency_penalty=0.2,
                                               presence_penalty=0.2,
                                               timeout=60,
                                               request_timeout=60,
                                               stop=stop)
            result = [
                msg['choices'][i]['message']['content'] for i in range(n)
            ]
        except Exception as exception:
            if "This model's maximum context length is 4096 tokens." in str(
                    exception):
                max_tokens = max_tokens // 2
                prompt = prompt[max_tokens:]
            print(f'[Error] ChatGPT API: {exception}')
            print(f'api key = {api_key}')
            # assert type(exception).__name__ == 'RateLimitError'
            # Adds sleep for the sake of preventing too frequent requst error.
            cnt += 1
            sleep_time = API_COOLDOWN * cnt
            print(f'RateLimitError caught! Sleep {sleep_time} seconds')
            time.sleep(sleep_time)
        finally:
            sleep_time = API_COOLDOWN
            time.sleep(sleep_time)

    if result is None:
        return ['[Error] try again later.' for _ in range(n)]

    return result


def story_generation_via_chatgpt(prompt, api_key):
    ret = chatgpt(config.CHATGPT_STORY_GENERATION_SCENARIO, prompt, api_key)
    if ret:
        return ret[0]
    return ''


def rewrite_turns_via_chatgpt(prompt, api_key):
    ret = chatgpt(config.CHATGPT_REWRITE_TURNS_SCENARIO, prompt, api_key)
    if ret:
        return ret[0]
    return ''


def rewrite_via_chatgpt(prompt, api_key, rewrite_instruction=''):
    instruction = f'{config.CHATGPT_REWRITE_SCENARIO} {rewrite_instruction}'
    ret = chatgpt(instruction, prompt, api_key)
    if ret:
        return ret[0]
    return ''


def get_response_from_chatgpt(prompt, n, api_key):
    temperature = decouple.config('TEMPERATURE', cast=float, default=0.8)
    ret = chatgpt(config.CHATGPT_SUBDIALOG_SCENARIO,
                  prompt,
                  api_key,
                  n=n,
                  temperature=temperature,
                  stop=["</div>"])
    return ret


def check_valid_subdialog(subdialog):
    MIN_NUM_TURNS_PER_SUBDIALOG = decouple.config(
        'MIN_NUM_TURNS_PER_SUBDIALOG', default=1, cast=int)
    SHORT_TURN_RATIO = decouple.config('SHORT_TURN_RATIO',
                                       default=0.35,
                                       cast=float)
    SHORT_TURN_STANDARD_NUM_WORDS = decouple.config(
        'SHORT_TURN_STANDARD_NUM_WORDS', default=2, cast=int)
    MAX_NUM_WORDS_PRE_TURN = decouple.config('MAX_NUM_WORDS_PER_TURN',
                                             default=180,
                                             cast=float)

    if len(subdialog) < MIN_NUM_TURNS_PER_SUBDIALOG:
        print(f'!!!! check_valid_subdialog: Less than {len(subdialog) = }')
        return False

    num_short_turns = 0
    num_turns_pass_check = 0
    for turn in subdialog:
        turn = turn.strip()

        num_words = len(turn.split(' '))
        if num_words < SHORT_TURN_STANDARD_NUM_WORDS:
            num_short_turns += 1

        if num_words > MAX_NUM_WORDS_PRE_TURN:
            print(
                f'!!!! check_valid_subdialog: More than {MAX_NUM_WORDS_PRE_TURN = }'
            )
            return False

        num_turns_pass_check += 1

    # Too many short turns, skip the subdialog.
    if num_short_turns / len(subdialog) > SHORT_TURN_RATIO:
        print(f'!!!! check_valid_subdialog: More than {num_short_turns = }')
        return False

    return True


def clean_text(text):
    text = text.strip()
    text = text.replace('\n', ' ').replace('\u0027', '\'')
    text = text.replace('"', '')
    text = text.replace('\\', '')
    text = text.encode("ascii", "ignore")
    text = text.decode().strip()
    return text


def extract_turns_from_llm_return(llm_return, party_to_role):
    extracted_turns = []
    for turn in llm_return:
        turn = turn.strip()
        soup = bs(turn, "lxml")
        if not turn.startswith('<p class='):
            continue
        if not turn.endswith('</p>'):
            continue
        try:
            party = soup.find('p').attrs['class'][0].title()

            if party not in party_to_role:
                continue

            text = soup.get_text()
            text = clean_text(text)
            # Skips empty utterances.
            if not text:
                continue
            extracted_turns.append({
                'party': party,
                'text': text,
                'role': party_to_role[party],
            })
        except:
            print(f'[Error]: {turn}')
            return None
    return extracted_turns


def generate_turns(prompt, api_key, party_to_role_string, num_returns,
                   iter_idx, last_turn_idx):
    TURN_SEP = config.TURN_SEP
    MAX_NUM_TURNS_PER_SUBDIALOG = decouple.config(
        'MAX_NUM_TURNS_PER_SUBDIALOG', default=10, cast=int)

    party_to_role = json.loads(party_to_role_string)

    subdialogs = []
    n = num_returns
    cnt = 0
    while len(subdialogs) < num_returns and cnt < MAX_NUM_SUBDIALOG_RETRY:
        cnt += 1
        candidate_subdialogs = \
            get_response_from_chatgpt(prompt, n, api_key)
        candidate_subdialogs = \
            [list(filter(lambda x: x != "", cand.split(TURN_SEP)))
                for cand in candidate_subdialogs]

        for subdialog in candidate_subdialogs:

            if len(subdialog) > MAX_NUM_TURNS_PER_SUBDIALOG:
                subdialog = subdialog[:MAX_NUM_TURNS_PER_SUBDIALOG]

            if not check_valid_subdialog(subdialog):
                print('@@@@@@@@@@@ Invalid subdialog @@@@@@@@@@@@@@')
                print(f'{prompt = }')
                print(f'{subdialog = }')
                time.sleep(1)
                continue

            extracted_turns = extract_turns_from_llm_return(
                subdialog, party_to_role)

            while extracted_turns and extracted_turns[-1]['role'] != 'user':
                extracted_turns.pop()

            if not extracted_turns:
                print('@@@@@@@@@@@ Empty subdialog @@@@@@@@@@@@@@')
                print(f'{prompt = }')
                print(f'{subdialog = }')
                time.sleep(1)
                continue

            subdialogs.append(extracted_turns)
            n = num_returns - len(subdialogs)

    return subdialogs


def parse_tuple(tup):
    referent = tup.get('referent', None)
    domain = tup['domain']
    slot = tup['slot']
    value = tup['value']
    categorical_value = tup.get('categorical_value', None)

    if categorical_value == '':
        categorical_value = '(non-categorical)'

    if value is None:
        value = '(unassigned)'

    if referent == 'dummy':
        time_value = tup.get('time_value', None)
        if time_value == '':
            time_value = '(non-time-value)'
        return f'({domain} || {slot} || {value} || {categorical_value} || {time_value})'
    elif referent and categorical_value is not None:
        return f'({referent} || {domain} || {slot} || {value} || {categorical_value})'
    else:
        return f'({domain} || {slot} || {value})'


def merge_neighbor_turns(turns):
    """Merge turns with the same role (user or agent) in the consecutive turns.
    Make sure we always have user and agent turns following each other.
    """
    merged_turns = []
    original_idx_to_merged_idx = {}
    for i, turn in enumerate(turns):
        if turn.deleted:
            continue
        if i == 0:
            merged_turns.append(turn)
            continue

        if turn.role == merged_turns[-1].role:
            merged_idx = len(merged_turns) - 1
            original_idx = turn.turn_idx
            original_idx_to_merged_idx[original_idx] = merged_idx
            merged_turns[-1].text += f' {turn.text}'
            merged_turns[-1].raw_text += f' {turn.raw_text}'
            merged_turns[-1].annotations += turn.annotations
            merged_turns[-1].edit |= turn.edit
            merged_turns[-1].auto_edit |= turn.auto_edit
        else:
            merged_turns.append(turn)

    for merged_turn in merged_turns:
        for ann in merged_turn.annotations:
            ann.turn_idx = original_idx_to_merged_idx.get(
                ann.turn_idx, ann.turn_idx)

            new_states = {}
            for idx, ops in ann.states.items():
                new_idx = original_idx_to_merged_idx.get(idx, idx)
                new_states[new_idx] = ops
            ann.states = new_states

    for merged_idx, merged_turn in enumerate(merged_turns):
        merged_turn.turn_idx = merged_idx

    return merged_turns
