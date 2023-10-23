import copy
import glob
import os
import random
from queue import Queue

import decouple
import tqdm
import threading

from src import llm_gen
from src import config
from src import mytask
from src import utils

PREFAB_N = decouple.config('PREFAB_N', cast=int)


class TaskManager:

    def __init__(self):
        self.task_id_to_task = {}
        self.load_api_keys()
        self._all_tasks_loaded = False

    def __getitem__(self, task_id):
        return self.task_id_to_task[task_id]

    def __iter__(self):
        for task in self.task_id_to_task.values():
            yield task

    @property
    def all_tasks_loaded(self):
        return self._all_tasks_loaded

    @all_tasks_loaded.setter
    def all_tasks_loaded(self):
        return self._all_tasks_loaded

    def init_task_from_scratch(self,
                               task_id,
                               task_json,
                               delay=True,
                               story_generation=False):
        task = mytask.Task(**{'task_id': task_id, **task_json})
        task.init_from_scratch(story_generation)
        last_turn_idx = task.example.last_turn_idx_in_history

        iter_idx = 0
        # Pre-generate N subdialogs (tries) before the website launch.
        try_idxs = list(range(PREFAB_N))
        for path in glob.glob(task.iter_dir + '/try_*'):
            try_idx = int(path.split('_')[-1].split('.')[0])
            if try_idx in try_idxs:
                try_idxs.remove(try_idx)
                task.set_dummy_celery_task(iter_idx, [try_idx])

        if try_idxs:
            api_key = self.get_api_key()
            celery_task_id = llm_gen.generate(
                task_id,
                task.example.prompt_for_llm,
                iter_idx,
                try_idxs,
                last_turn_idx,
                task.example.party_to_role_string,
                api_key,
                delay=delay)
            if delay:
                task.set_celery_task(iter_idx, try_idxs, celery_task_id)
            else:
                task.set_dummy_celery_task(iter_idx, try_idxs)
                self.put_api_key(api_key)

        self.task_id_to_task[task_id] = task

    def load_api_keys(self):
        self.api_key_queue_lock = threading.Condition()
        keys = copy.deepcopy(config.API_KEYS)
        random.shuffle(keys)
        self.api_keys = Queue()
        for key in keys:
            self.api_keys.put(key)

    def get_api_key(self):
        self.api_key_queue_lock.acquire()
        while self.api_keys.qsize() == 0:
            self.api_key_queue_lock.wait()
        api_key = self.api_keys.get()
        self.api_key_queue_lock.release()
        return api_key

    def put_api_key(self, api_key):
        self.api_key_queue_lock.acquire()
        if api_key not in list(self.api_keys.queue):
            self.api_keys.put(api_key)
        self.api_key_queue_lock.notify()
        self.api_key_queue_lock.release()

    def prefab_try_by_task_id(self,
                              task_id,
                              iter_idx,
                              try_idxs,
                              last_turn_idx,
                              api_key,
                              delay=True):
        task = self[task_id]
        celery_task_id = llm_gen.generate(task_id,
                                          task.example.prompt_for_llm,
                                          iter_idx,
                                          try_idxs,
                                          last_turn_idx,
                                          task.example.party_to_role_string,
                                          api_key,
                                          delay=delay)
        if delay:
            task.set_celery_task(iter_idx, try_idxs, celery_task_id)
        else:
            task.set_dummy_celery_task(iter_idx, try_idxs)

    def prefab_try_for_next_iter_by_task_id(self, task_id, delay=True):
        task = self[task_id]

        # Aleady the last subdialog, no need to prefab two subdialogs for
        # the next iteration.
        if task.example.last_subdialog:
            return

        # Pre-generate N subdialog (tries) when the worker is working on the
        # annotation.
        last_turn_idx = (task.example.last_turn_idx_in_history +
                         len(task.example.curr_valid_turns))
        # labeling_valid_turn_idx starts from -1.
        # Since we want to prefab for the next iteration, we set
        # labeling_valid_turn_idx = len(task.example.curr_valid_turns) - 1 to
        # get the entire turns in the current subdialog to prefab the next
        # current subdialog.
        task.example.labeling_valid_turn_idx = len(
            task.example.curr_valid_turns) - 1
        api_key = self.get_api_key()
        iter_idx = task.curr_iter_idx + 1
        num_tries = len(task.iter_idx_to_try_idx_to_celery_task[iter_idx])
        try_idxs = [i for i in range(num_tries, num_tries + PREFAB_N)]
        self.prefab_try_by_task_id(task.task_id,
                                   iter_idx,
                                   try_idxs,
                                   last_turn_idx,
                                   api_key,
                                   delay=delay)
        if not delay:
            self.put_api_key(api_key)
        task.example.labeling_valid_turn_idx = -1

    def load(self):
        task_map = utils.read_yaml(config.TASK_TABLE_PATH)
        load_from_disk = set()

        pbar = tqdm.tqdm(task_map.items(),
                         ncols=80,
                         disable=decouple.config('DISABLE_TQDM',
                                                 cast=bool,
                                                 default=False))
        for task_id, task_json in pbar:
            pbar.set_description(f'Process {task_id}')
            task_json = copy.deepcopy(task_json)
            if not task_json.pop('activate'):
                continue

            story_generation = task_json.get('story_generation', False)

            task_dir = config.TASK_DIR_TEMPLATE.format(task_id)
            last_success_path = os.path.join(task_dir, config.SUCCESS_FILENAME)
            if os.path.exists(last_success_path):
                self.load_from_last_success_by_task_id(task_id,
                                                       last_success_path)
                load_from_disk.add(task_id)
            else:
                self.init_task_from_scratch(task_id,
                                            task_json,
                                            story_generation=story_generation)

        pbar = tqdm.tqdm(task_map.items(),
                         ncols=80,
                         disable=decouple.config('DISABLE_TQDM',
                                                 cast=bool,
                                                 default=False))
        for task_id, task_json in pbar:
            pbar.set_description(f'Process {task_id}')
            if not task_json['activate']:
                continue
            task = self[task_id]

            if task.step == 'done':
                continue

            # When step == 'generation' and load_from_disk, we need to reset
            # iter_idx and try_idx for the next iteration.
            if (task_id in load_from_disk and task.step == 'generation'):
                task.reset_for_next_iter()
                task.reset_curr_try()
                task.update_curr_try()

            if task_id not in load_from_disk:
                task.update_curr_try()

        self._all_tasks_loaded = True

    def load_from_last_success_by_task_id(self, task_id, path):
        task = mytask.Task.load_task(path)
        self.task_id_to_task[task_id] = task

        # No need to prefab subdialogs if it is the last subdialog or
        # the task is done.
        if task.example.last_subdialog or task.step == 'done':
            return

        iter_idx = task.curr_iter_idx + 1
        last_turn_idx = task.example.last_turn_idx_in_history
        iter_dir = config.ITER_DIR_TEMPLATE.format(task.task_id, iter_idx)

        try_idxs = []
        for try_path in glob.glob(os.path.join(iter_dir, 'try*')):
            try_idxs.append(int(try_path.split('_')[-1].split('.')[0]))

        if try_idxs:
            task.set_dummy_celery_task(iter_idx, try_idxs)
        else:
            api_key = self.get_api_key()
            lack_try_idxs = list(set(range(PREFAB_N)) - set(try_idxs))
            self.prefab_try_by_task_id(task.task_id, iter_idx, lack_try_idxs,
                                       last_turn_idx, api_key)

    def regenerate_by_task_id(self, task_id, delay=True):
        task = self[task_id]
        # Save time: Prefab the next try to cache a new subdialogue.
        api_key = self.get_api_key()
        last_turn_idx = task.example.last_turn_idx_in_history
        num_tries = len(
            task.iter_idx_to_try_idx_to_celery_task[task.curr_iter_idx])
        try_idxs = [i for i in range(num_tries, num_tries + PREFAB_N)]
        self.prefab_try_by_task_id(task_id, task.curr_iter_idx, try_idxs,
                                   last_turn_idx, api_key, delay)
        task.add_curr_try_idx()
        task.update_curr_try(wait=delay)
