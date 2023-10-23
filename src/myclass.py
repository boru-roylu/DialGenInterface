import collections
import copy
import dataclasses
import dataclasses_json as dj
import json
from threading import Condition
from typing import List, Dict
import string

import decouple

import config
import utils


@dj.dataclass_json
@dataclasses.dataclass
class CeleryTask:
    task_id: str
    condition = Condition()


@dj.dataclass_json
@dataclasses.dataclass
class Annotation:
    turn_idx: str
    party: str
    role: str
    domain: str
    slot: str
    start: int
    end: int
    referent: str
    color: str = ''
    value: str = ''
    categorical_value: str = ''
    time_value: str = ''
    history_turn_idx: str = ''
    history_start: int = 0
    history_end: int = 0
    states: Dict[int, str] = dataclasses.field(default_factory=dict)

    def __hash__(self):
        translator = str.maketrans('', '', string.punctuation)
        value = self.value.translate(translator)
        categorical_value = self.categorical_value.translate(translator)
        time_value = self.time_value.translate(translator)
        return hash(self.domain + self.slot + value + categorical_value +
                    time_value + self.referent)

    def text(self):
        return utils.parse_tuple({
            'domain': self.domain,
            'slot': self.slot,
            'value': self.value,
            'categorical_value': self.categorical_value,
            'time_value': self.time_value,
            'referent': self.referent
        })


@dj.dataclass_json
@dataclasses.dataclass
class Turn:
    iteration: int
    party: str
    role: str
    text: str
    turn_idx: int
    raw_text: str = None
    annotations: List[Annotation] = dataclasses.field(default_factory=list)
    annotated: bool = False
    deleted: bool = False
    edit: bool = False
    auto_edit: bool = False
    instruction: str = None

    def copy_from_dict(self, other):
        assert self.party == other['party']
        assert self.role == other['role']
        self.text = other['text']
        self.raw_text = other.get('raw_text', None)
        self.deleted = other.get('deleted', False)
        self.edit = other.get('edit', False)
        self.auto_edit = other.get('auto_edit', False)


@dj.dataclass_json
@dataclasses.dataclass
class Subdialog:
    turns: List[Turn] = dataclasses.field(default_factory=list)


@dj.dataclass_json
@dataclasses.dataclass
class Try:
    task_id: str
    iter_idx: int
    idx: int
    worker_name: str = None
    turns: List[Turn] = dataclasses.field(default_factory=list)


def process_instruction_for_llm(instruction):
    instruction = instruction.strip()
    if not instruction:
        return ''
    return config.INSTRUCTION_TEMPLATE.format(instruction=instruction).strip()


def process_summary_for_llm(summary_sentences):
    summary = '\n'.join(summary_sentences)
    return config.SUMMARY_TEMPLATE.format(summary=summary).strip()


def process_chunks_for_llm(chunk):
    TURN_SEP = config.TURN_SEP
    turns = [
        config.TURN_TEMPLATE.format(party=turn.party, turn=turn.text)
        for turn in chunk
    ]
    # Use \n\n in the function `generate_turns`, so we must use \n\n here.
    return TURN_SEP.join(turns).strip()


class Example:

    def __init__(self,
                 subdialogs,
                 summaries,
                 party_to_role,
                 tuples_with_value=None,
                 tuples_without_value=None,
                 curr_try=None,
                 last_subdialog=False,
                 labeling_valid_turn_idx=-1,
                 instruction=''):
        self._subdialogs = subdialogs
        self._summaries = summaries
        self._party_to_role = party_to_role
        self._tuples_with_value = tuples_with_value or dict()
        self._tuples_without_value = tuples_without_value or dict()
        self._curr_try = curr_try
        self._last_subdialog = last_subdialog
        self._labeling_valid_turn_idx = labeling_valid_turn_idx
        self._instruction = instruction

    @property
    def domain_to_dialog_scenario_tuples(self):
        ret = collections.defaultdict(list)
        for t in copy.deepcopy(self._tuples_with_value):
            # For AS, since we merge two words.
            ret[t['domain']].append(t)
        for t in copy.deepcopy(self._tuples_without_value):
            # For AS, since we merge two words.
            t['value'] = ''
            ret[t['domain']].append(t)

        for domain in config.DOMAINS:
            if domain not in ret:
                ret[domain] = []
        return dict(ret)

    @property
    def last_turn_idx_in_history(self):
        # Ignores -1 for deleted turns.
        return max([turn.turn_idx for turn in self.subdialogs[-1].turns])

    @property
    def instruction(self):
        return self._instruction

    @instruction.setter
    def instruction(self, instruction):
        self._instruction = instruction

    @property
    def history_with_deleted_turns(self):
        all_history_turns = copy.deepcopy(
            sum([subdialog.turns for subdialog in self._subdialogs], []))
        if self.curr_valid_turns:
            all_history_turns = \
                (all_history_turns
                 + self.curr_valid_turns[:self.labeling_valid_turn_idx+1])
        return all_history_turns

    @property
    def history(self):
        all_history_turns = copy.deepcopy(
            sum([subdialog.turns for subdialog in self._subdialogs], []))

        if self.curr_valid_turns:
            all_history_turns = \
                (all_history_turns
                 + self.curr_valid_turns[:self.labeling_valid_turn_idx+1])

        return list(filter(lambda turn: not turn.deleted, all_history_turns))

    @property
    def history_text_based_annotations(self):
        list_annotations = []
        for turn in self.history:
            annotations = sorted(turn.annotations, key=lambda ann: ann.domain)
            text_annotations = [ann.text() for ann in annotations]
            list_annotations.append('<br>'.join(text_annotations))
        return list_annotations

    @property
    def reference_history(self):
        all_history_turns = sum(
            [subdialog.turns for subdialog in self._subdialogs], [])
        if self.curr_valid_turns:
            all_history_turns = \
                (all_history_turns
                 + self.reference_curr_valid_turns[:self.labeling_valid_turn_idx+1])
        return list(filter(lambda turn: not turn.deleted, all_history_turns))

    @property
    def reference_curr_valid_turns(self):
        if self.curr_try is None:
            return []
        return [turn for turn in self.curr_try.turns if not turn.deleted]

    @property
    def curr_valid_turns(self):
        if self.curr_try is None:
            return []
        return copy.deepcopy(
            [turn for turn in self.curr_try.turns if not turn.deleted])

    @property
    def party_to_role(self):
        return self._party_to_role

    @property
    def party_to_role_string(self):
        return json.dumps(self.party_to_role)

    @property
    def role_to_party(self):
        return {v: k for k, v in self.party_to_role.items()}

    @property
    def party_name_strings(self):
        return json.dumps(list(self._party_to_role.keys()))

    @property
    def curr_try(self):
        return self._curr_try

    @curr_try.setter
    def curr_try(self, curr_try):
        self._curr_try = curr_try

    @property
    def subdialogs(self):
        return self._subdialogs

    @subdialogs.setter
    def subdialogs(self, subdialogs):
        self._subdialogs = subdialogs

    @property
    def summaries(self):
        return self._summaries

    @summaries.setter
    def summaries(self, summary):
        self._summaries = summary

    @property
    def llm_instruction(self):
        return process_instruction_for_llm(self.instruction)

    @property
    def llm_summaries(self):
        summaries = copy.deepcopy(self.summaries)
        summaries = sum(summaries, [])

        llm_summaries = process_summary_for_llm(summaries)

        return llm_summaries

    @property
    def llm_chunks(self):
        all_turns = copy.deepcopy(self.history)

        MAX_NUM_TURNS_PER_LLM_CHUNCK = decouple.config(
            'MAX_NUM_TURNS_PER_LLM_CHUNCK', default=15, cast=int)

        chunk = []
        chunks = []
        for turn in all_turns:
            if len(chunk) >= MAX_NUM_TURNS_PER_LLM_CHUNCK:
                chunks.append(copy.deepcopy(chunk))
                chunk = []
            chunk.append(turn)

        if chunk:
            chunks.append(copy.deepcopy(chunk))

        return list(map(process_chunks_for_llm, chunks))

    @property
    def last_subdialog(self):
        return self._last_subdialog

    @last_subdialog.setter
    def last_subdialog(self, last_subdialog):
        self._last_subdialog = last_subdialog

    @property
    def labeling_valid_turn_idx(self):
        return self._labeling_valid_turn_idx

    @labeling_valid_turn_idx.setter
    def labeling_valid_turn_idx(self, idx):
        self._labeling_valid_turn_idx = idx

    @property
    def prompt_for_llm(self):
        summaries = self.llm_summaries
        chunks = self.llm_chunks
        instruction = self.llm_instruction

        # Remove chunks if too long.
        MAX_NUM_WORDS_IN_PROMPT = decouple.config('MAX_NUM_WORDS_IN_PROMPT',
                                                  default=5120,
                                                  cast=int)
        num_words = float('inf')
        while num_words > MAX_NUM_WORDS_IN_PROMPT:
            prompt = [summaries]
            for i in range(len(chunks)):
                prompt.append('<div>')
                prompt.append(chunks[i])
                prompt.append('</div>')
            if instruction:
                prompt.append(instruction)
            prompt.append('<div>')
            prompt = '\n\n'.join(prompt)
            num_words = len(prompt.split(' '))
            if num_words > MAX_NUM_WORDS_IN_PROMPT:
                chunks = chunks[1:]

        prompt = [summaries]
        for i in range(len(chunks)):
            prompt.append('<div>')
            prompt.append(chunks[i])
            prompt.append('</div>')

        if instruction:
            prompt.append(instruction)

        div_instruction = config.DIV_PREFIX_INSTRUCTION.replace(
            '[AGENT]', self.role_to_party['agent'])
        if div_instruction:
            prompt.append(div_instruction)

        prompt.append('<div>')

        prompt = '\n\n'.join(prompt)

        return prompt

    def for_rendering_html(self, curr_idx=None):
        dialog_history = list(map(lambda x: x.to_dict(), self.history))
        curr_subdialog = list(map(lambda x: x.to_dict(),
                                  self.curr_valid_turns))
        domain_to_extracted_tuples = self.domain_to_extracted_tuples()
        if curr_idx:
            dialog_history = dialog_history[:curr_idx]
            curr_subdialog = curr_subdialog[:curr_idx]
            domain_to_extracted_tuples = self.domain_to_extracted_tuples(
                curr_idx)

        example = dict(
            dialog_history=dialog_history,
            curr_subdialog=curr_subdialog,
            history_text_based_annotations=self.history_text_based_annotations,
            domain_to_dialog_scenario_tuples=self.
            domain_to_dialog_scenario_tuples,
            cumulative_annotations=self.annotations,
            party_to_role=self.party_to_role,
            role_to_party=self.role_to_party,
            domain_to_extracted_tuples=domain_to_extracted_tuples,
            instruction=self.instruction,
            summaries=self.llm_summaries.split('\n'),
            turn_idxs_with_duplicate_tuples=self.
            turn_idxs_with_duplicate_tuples,
        )
        return example

    def to_dict(self):
        return dict(
            subdialogs=list(
                map(lambda subdialog: subdialog.to_dict(), self.subdialogs)),
            summaries=self._summaries,
            party_to_role=self.party_to_role,
            tuples_with_value=self._tuples_with_value,
            tuples_without_value=self._tuples_without_value,
            curr_try=self._curr_try.to_dict() if self._curr_try else None,
            last_subdialog=self._last_subdialog,
            labeling_valid_turn_idx=self._labeling_valid_turn_idx,
            instruction=self.instruction,
        )

    @staticmethod
    def from_dict(dic):
        dic['subdialogs'] = \
            list(map(lambda subdialog: Subdialog.from_dict(subdialog), dic['subdialogs']))
        if dic['curr_try']:
            dic['curr_try'] = Try.from_dict(dic['curr_try'])
        else:
            dic['curr_try'] = None
        return Example(**dic)

    @property
    def turn_to_be_annotated(self):
        # Returns the turn to be annotated in json string.
        turn_idx = self._labeling_valid_turn_idx + 1
        if turn_idx < len(self.curr_valid_turns):
            turn = copy.deepcopy(self.curr_valid_turns[turn_idx]).to_dict()
            for ann in turn['annotations']:
                curr_idx = len(self.history)
                state = 'keep'
                if len(ann['states'].keys()) != 0:
                    state_idxs = sorted([
                        idx for idx in ann['states'].keys() if idx <= curr_idx
                    ])
                    if state_idxs:
                        state_idx = state_idxs[-1]
                        state = ann['states'][state_idx]
                ann['state'] = state
            return turn
        return None

    def turn_to_be_annotated_by_idx(self, turn_idx):
        # Returns the turn to be annotated in json string.
        turn = copy.deepcopy(self.history[turn_idx]).to_dict()
        for ann in turn['annotations']:
            state = 'keep'
            if len(ann['states'].keys()) != 0:
                state_idxs = sorted(
                    [idx for idx in ann['states'].keys() if idx <= turn_idx])
                if state_idxs:
                    state_idx = state_idxs[-1]
                    state = ann['states'][state_idx]
            ann['state'] = state
        return turn

    @property
    def annotations(self):
        # turn_idx, domain, slot, value, categorical_value referent.
        # Puts annotations with same domain, slot, referent together.
        hash_to_annotations = collections.defaultdict(list)
        for turn in self.history:
            for ann in turn.annotations:
                hash_to_annotations[hash(ann)].append(ann)

        rows = []
        for _, annotations in hash_to_annotations.items():
            # Only need to task the first annotation for hash key
            # because they are sharing the domain and slot. But we take the
            # value of the latest annotation as the value for the hash key.
            ann = copy.deepcopy(annotations[-1])
            latest_value = annotations[-1].value
            ann = ann.to_dict()
            ann.pop('role')
            ann.pop('party')
            rows.append({
                'vlaue': latest_value,
                **ann,
            })
        return rows

    def domain_to_extracted_tuples(self, curr_idx=None):
        domain_to_extracted_tuples = collections.defaultdict(list)
        if curr_idx is None:
            turns = self.history
            curr_idx = len(self.history)
        else:
            turns = self.history[:curr_idx]

        for turn in turns:
            for ann in turn.annotations:
                state = 'keep'
                if len(ann.states.keys()) != 0:
                    state_idxs = sorted(
                        [idx for idx in ann.states.keys() if idx <= curr_idx])
                    if state_idxs:
                        state_idx = state_idxs[-1]
                        state = ann.states[state_idx]
                extract_tuple = {
                    'turn_idx': ann.turn_idx,
                    'slot': ann.slot,
                    'domain': ann.domain,
                    'value': ann.value,
                    'categorical_value': ann.categorical_value,
                    'time_value': ann.time_value,
                    'color': ann.color,
                    'start': ann.start,
                    'end': ann.end,
                    'referent': ann.referent,
                    'state': state,
                }
                domain_to_extracted_tuples[ann.domain].append(extract_tuple)
        return dict(domain_to_extracted_tuples)

    @property
    def turn_idxs_with_duplicate_tuples(self):
        turn_idx_to_duplicate_tuples_indicator = {}
        referent_domain_slot_set = set()
        for turn_idx, turn in enumerate(self.history):
            for ann in turn.annotations:
                key = f'{ann.referent} {ann.domain} {ann.slot}'
                if key in referent_domain_slot_set:
                    turn_idx_to_duplicate_tuples_indicator[turn_idx] = True
                    break
                referent_domain_slot_set.add(key)
            else:
                turn_idx_to_duplicate_tuples_indicator[turn_idx] = False
        return turn_idx_to_duplicate_tuples_indicator

    def update_duplicate_tuples(self, duplicate_tuples):
        history = self.reference_history
        curr_idx = len(history) - 1
        self.update_duplicate_tuples_by_curr_idx(duplicate_tuples, curr_idx)

    def update_duplicate_tuples_by_curr_idx(self, duplicate_tuples, curr_idx):
        history = self.reference_history

        # To put the annotated turns in the history, we shift labeling_valid_turn_idx by 1.
        for tup in duplicate_tuples:
            turn_idx = tup['turn_idx']
            turn = history[turn_idx]
            for ann in turn.annotations:
                if tup['state'] == 'keep':
                    continue
                if (ann.referent != tup['referent']
                        or ann.domain != tup['domain']
                        or ann.slot != tup['slot'] or ann.value != tup['value']
                        or ann.categorical_value != tup['categorical_value']):
                    continue
                ann.states[curr_idx] = tup['state']
                break

    def add_annotations_to_turn(self,
                                annotations,
                                turn_idx=None,
                                add_to_history=False):
        if add_to_history:
            turn = self.reference_history[turn_idx]
        else:
            valid_idx_to_idx = {}
            for i, turn in enumerate(self.curr_try.turns):
                if turn.deleted:
                    continue
                valid_idx_to_idx[len(valid_idx_to_idx)] = i
            curr_subdialog_valid_turn_idx = self._labeling_valid_turn_idx + 1
            turn_idx = len(self.history)

            # Maps to valid index (inclduing deleted turns).
            curr_subdialog_turn_idx = valid_idx_to_idx[
                curr_subdialog_valid_turn_idx]
            turn = self.curr_try.turns[curr_subdialog_turn_idx]
        party = turn.party
        role = self._party_to_role[party]
        turn.annotations = [
            Annotation(turn_idx=turn_idx,
                       party=party,
                       role=role,
                       domain=ann['anno_domain'],
                       slot=ann['anno_slot'],
                       value=utils.clean_text(ann['anno_value']),
                       categorical_value=ann['anno_categorical_value'],
                       time_value=ann['anno_time_value'],
                       start=ann['start_end_pairs'][0][0],
                       end=ann['start_end_pairs'][0][1],
                       referent=ann['anno_referent'],
                       color=ann['color'],
                       history_turn_idx=ann['history_turn_idx'],
                       history_start=ann['history_start_end_pairs'][0][0],
                       history_end=ann['history_start_end_pairs'][0][1])
            for ann in annotations
        ]
        turn.annotated = True

        if not add_to_history:
            self.curr_try.turns[curr_subdialog_turn_idx] = turn

    def add_curr_try_turns_to_subdialogs(self):
        self.subdialogs.append(Subdialog(turns=self.curr_try.turns))

    def update_turns(self, turns, curr_iter_idx):
        turn_idx = self.last_turn_idx_in_history + 1
        for i, turn in enumerate(turns):
            turn.update({
                'iteration': curr_iter_idx,
                'turn_idx': turn_idx if not turn['deleted'] else -1,
            })
            if not turn['deleted']:
                turn['text'] = utils.clean_text(turn['text'])
                turn_idx = turn_idx + 1
            turns[i] = Turn(**turn)
        self.curr_try.turns = copy.deepcopy(turns)

    def update_history_turns(self, turns):
        reference_history = self.reference_history
        for idx, turn in enumerate(turns):
            reference_history[idx].copy_from_dict(turn)

    def clean_annotations_by_turn_idx(self, turn_idx):
        reference_history = self.reference_history
        reference_history[turn_idx].annotations = []

    def get_state_by_turn_idx(self, turn_idx):
        referent_domain_slot_to_annotations = collections.defaultdict(list)
        for turn in self.history[:turn_idx + 1]:
            for ann in turn.annotations:
                referent_domain_slot = f'{ann.referent} {ann.domain} {ann.slot}'
                referent_domain_slot_to_annotations[
                    referent_domain_slot].append(ann)

        final_state = []
        for referent_domain_slot, annotations in referent_domain_slot_to_annotations.items(
        ):
            concat_annotations = []
            for ann in annotations:
                state = 'keep'
                if len(ann.states.keys()) != 0:
                    state_idxs = sorted(
                        [idx for idx in ann.states.keys() if idx <= turn_idx])
                    if state_idxs:
                        state_idx = state_idxs[-1]
                        state = ann.states[state_idx]

                if state == 'delete':
                    continue
                elif state == 'keep':
                    final_state.append(ann)
                else:  #state == 'concat':
                    concat_annotations.append(ann)

            if concat_annotations:
                assert len(concat_annotations) > 1
                for ann in concat_annotations[1:]:
                    concat_annotations[0].value += ' ' + ann.value
                final_state.append(concat_annotations[0])
        return final_state
