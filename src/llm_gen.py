import collections
import os
import httplib2
import json

from celery import Celery
from celery import signals

from src import config
from src import utils

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL",
                                        "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND",
                                            "redis://localhost:6379")


@celery.task(name='generate_try')
def generate_try(task_id, prompt, iter_idx, try_idxs, last_turn_idx,
                 party_to_role_string, api_key):

    print(prompt)

    iter_dir = config.ITER_DIR_TEMPLATE.format(task_id, iter_idx)
    os.makedirs(iter_dir, exist_ok=True)

    # Generates N new subdialog.
    # N = len(try_idxs).
    num_returns = len(try_idxs)
    batched_extract_turns = utils.generate_turns(prompt, api_key,
                                                 party_to_role_string,
                                                 num_returns, iter_idx,
                                                 last_turn_idx)
    while len(batched_extract_turns) < num_returns:
        batched_extract_turns.append([])

    for try_idx, extracted_turns in zip(try_idxs, batched_extract_turns):

        path = os.path.join(iter_dir, f'try_{try_idx:03}.yaml')
        if os.path.exists(path):
            continue

        for turn in extracted_turns:
            last_turn_idx += 1
            turn['iteration'] = iter_idx
            turn['turn_idx'] = last_turn_idx

        curr_try = collections.OrderedDict(task_id=task_id,
                                           iter_idx=iter_idx,
                                           idx=try_idx,
                                           turns=extracted_turns)
        utils.save_yaml(path, dict(curr_try))

    return task_id, path, api_key, iter_idx, try_idxs


def post_dict(url, dictionary):
    '''
    Pass the whole dictionary as a json body to the url.
    Make sure to use a new Http object each time for thread safety.
    '''
    http = httplib2.Http()
    resp, content = http.request(
        uri=url,
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=json.dumps(dictionary),
    )
    print(resp)
    print(content)
    print("Response Content Body")


@signals.task_success.connect
def task_success_notifier(result,
                          sender=None,
                          task_id=None,
                          task=None,
                          **kwargs):
    dg_task_id, path, api_key, iter_idx, try_idxs = result
    res = {
        'celery_task_id': task_id,
        'task_id': dg_task_id,
        'path': path,
        'api_key': api_key,
        'iter_idx': iter_idx,
        'try_idxs': try_idxs,
    }
    #post_dict('http://127.0.0.1:5001/receive_signals', res)
    post_dict('http://web:5001/receive_signals', res)


def generate(task_id,
             prompt_for_llm,
             iter_idx,
             try_idxs,
             last_turn_idx,
             party_to_role_string,
             api_key,
             delay=True):
    if delay:
        gen = generate_try.delay(task_id, prompt_for_llm, iter_idx, try_idxs,
                                 last_turn_idx, party_to_role_string, api_key)
        celery_task_id = gen.task_id
    else:
        gen = generate_try(task_id, prompt_for_llm, iter_idx, try_idxs,
                           last_turn_idx, party_to_role_string, api_key)
        celery_task_id = config.FINISHED
    return celery_task_id
