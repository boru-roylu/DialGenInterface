import collections
import json
import os

import config
import myclass
import utils

# We segment a dialogue into a sequence of llm chunks.
# For each chunk, the maximum number of turns is determined.
# The concept of chunks is different from subdialogs.

WORKER_MAP = utils.read_yaml(config.WORKER_MAP_PATH)


def convert_slot_value_to_string(domain, slot, value):
    if value is None:
        ret = f"{slot}"
    else:
        ret = f"({slot}, {value})"

    return ret


def replace_macro_in_scenario_as_new(summaries, flow):
    role_to_party = flow['role_to_party']
    agent_name = role_to_party['agent']
    user_name = role_to_party['user']

    tuples_with_value = []
    tuples_without_value = []
    domain_to_tuples = collections.defaultdict(list)
    for k, tuples in flow.items():
        if 'TUPLES' not in k:
            continue
        for tup in tuples:
            if tup['slot'] == 'Permission to Record':
                continue
            tuple_string = convert_slot_value_to_string(
                tup['domain'], tup['slot'], tup['value'])
            domain_to_tuples[tup['domain']].append(tuple_string.lower())

            if tup['value']:
                tuples_with_value.append(tup)
            else:
                tuples_without_value.append(tup)

    new_summaries = []
    for s in summaries:
        s = s.replace('[USER]', user_name)
        s = s.replace('[AGENT]', agent_name)

        discard = False
        for domain in config.DOMAINS:
            macro = f'[{domain}_TUPLES]'

            if macro not in s:
                continue

            tuples = domain_to_tuples[domain]

            if not tuples:
                # No preference tuples for this domain.
                discard = True
                continue

            s = s.replace(macro, ', '.join(tuples))

        if not discard:
            new_summaries.append(s)

    return new_summaries, tuples_with_value, tuples_without_value


def replace_macro_in_subdialog(subdialog, flow):
    role_to_party = flow['role_to_party']
    agent_name = role_to_party['agent']
    user_name = role_to_party['user']

    for i, turn in enumerate(subdialog):
        turn['party'] = {'agent': agent_name, 'user': user_name}[turn['party']]
        turn['text'] = turn['text'].replace('[USER]', user_name)
        turn['text'] = turn['text'].replace('[AGENT]', agent_name)
        subdialog[i] = myclass.Turn(**turn)
    return subdialog


def read_init_subdialog(template_path, flow_path):
    template = utils.read_yaml(template_path)
    flow = utils.read_yaml(flow_path)

    if flow.get('summaries', None):
        summaries = flow.pop('summaries')
    else:
        summaries = template['summaries']

    role_to_party = flow['role_to_party']
    summary, tuples_with_value, tuples_without_value = replace_macro_in_scenario_as_new(
        summaries, flow)
    subdialog = replace_macro_in_subdialog(template['subdialogs'][0], flow)

    summaries = [summary]
    subdialogs = [myclass.Subdialog(subdialog)]

    return summaries, subdialogs, role_to_party, tuples_with_value, tuples_without_value


def read_init_subdialog_with_story_generation(template_path, flow_path):
    template = utils.read_yaml(template_path)
    flow = utils.read_yaml(flow_path)

    step_summaries = flow['step_summaries']
    story_summaries = flow['story_summaries']
    information_summaries = flow['information_summaries']
    user_personality = flow['user_personality']
    agent_personality = flow['agent_personality']
    instructions = flow['instructions']
    role_to_party = flow['role_to_party']
    story = flow['story']

    sep = '--------'
    summaries = [
        'story', *story, sep, 'information', *information_summaries, sep,
        'steps', *step_summaries, sep, 'personality', user_personality,
        agent_personality, sep, 'instructions', *instructions
    ]

    summary, tuples_with_value, tuples_without_value = replace_macro_in_scenario_as_new(
        summaries, flow)

    subdialog = replace_macro_in_subdialog(template['subdialogs'][0], flow)

    summaries = [summary]
    subdialogs = [myclass.Subdialog(subdialog)]

    return summaries, subdialogs, role_to_party, tuples_with_value, tuples_without_value


class Task:

    def __init__(self,
                 task_id,
                 template_idx,
                 accident_location,
                 flow_id,
                 story_generation=False,
                 step='generation',
                 curr_iter_idx=0,
                 curr_try_idx=0,
                 example=None,
                 iter_idx_to_step_to_time_spent_on_page=None):

        self._step = step
        self._task_id = task_id
        self._template_idx = template_idx
        self._accident_location = accident_location
        self._flow_id = flow_id
        self._story_generation = story_generation

        self._curr_iter_idx = curr_iter_idx
        self._curr_try_idx = curr_try_idx
        self.iter_idx_to_try_idx_to_celery_task = collections.defaultdict(dict)
        self.example = example

        self._iter_idx_to_step_to_time_spent_on_page = collections.defaultdict(
            lambda: collections.defaultdict(int))
        if iter_idx_to_step_to_time_spent_on_page is not None:
            for iter_idx, time_spent_on_page in iter_idx_to_step_to_time_spent_on_page.items(
            ):
                for step, time_spent in time_spent_on_page.items():
                    self._iter_idx_to_step_to_time_spent_on_page[iter_idx][
                        step] += time_spent

    def __str__(self):
        return f'task id = {self._task_id}'

    @property
    def iter_idx_to_step_to_time_spent_on_page(self):
        ret = {}
        for iter_idx, step_to_time_spent_on_page in self._iter_idx_to_step_to_time_spent_on_page.items(
        ):
            ret[iter_idx] = dict(step_to_time_spent_on_page)
        return ret

    def update_time_spent(self, time):
        self._iter_idx_to_step_to_time_spent_on_page[self.curr_iter_idx][
            self.step] += time

    @property
    def page_time_spent(self):
        return self._iter_idx_to_step_to_time_spent_on_page[
            self.curr_iter_idx][self.step]

    @property
    def total_time_spent(self):
        return sum(
            sum(list(self._iter_idx_to_step_to_time_spent_on_page[i].values()))
            for i in range(self.curr_iter_idx + 1))

    @property
    def curr_iter_idx(self):
        return self._curr_iter_idx

    @curr_iter_idx.setter
    def curr_iter_idx(self, curr_iter_idx):
        self._curr_iter_idx = curr_iter_idx

    @property
    def curr_try_idx(self):
        return self._curr_try_idx

    @curr_try_idx.setter
    def curr_try_idx(self, curr_try_idx):
        self._curr_try_idx = curr_try_idx

    @property
    def step(self):
        return self._step

    @step.setter
    def step(self, step):
        self._step = step

    @property
    def story_generation(self):
        return self._story_generation

    @story_generation.setter
    def story_generation(self, story_generation):
        self._story_generation = story_generation

    @property
    def task_id(self):
        return self._task_id

    @property
    def template_idx(self):
        return self._template_idx

    @property
    def accident_location(self):
        return self._accident_location

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def iter_dir(self):
        return config.ITER_DIR_TEMPLATE.format(self.task_id,
                                               self.curr_iter_idx)

    @property
    def task_dir(self):
        return config.TASK_DIR_TEMPLATE.format(self.task_id)

    @property
    def allow_back(self):
        return self.example.labeling_valid_turn_idx > -1

    @property
    def last_turn_to_be_annotated(self):
        turn_idx = self.example.labeling_valid_turn_idx + 2
        if turn_idx == len(self.example.curr_valid_turns):
            return True
        return False

    def init_from_scratch(self, story_generation=False):
        os.makedirs(self.iter_dir, exist_ok=True)

        assert self.curr_iter_idx == 0
        # First iteration and first try.
        template_path = os.path.join(config.PROMPT_DIR,
                                     f'template_{self.template_idx:03}.yaml')
        flow_path = os.path.join(
            config.FLOW_DIR, f'{self.accident_location}/{self.flow_id}.yaml')

        if story_generation:
            summaries, subdialogs, role_to_party, tuples_with_value, tuples_without_value = \
                read_init_subdialog_with_story_generation(template_path, flow_path)
        else:
            summaries, subdialogs, role_to_party, tuples_with_value, tuples_without_value = \
                read_init_subdialog(template_path, flow_path)

        self._agent_name = role_to_party['agent']
        self._user_name = role_to_party['user']
        party_to_role = {v: k for k, v in role_to_party.items()}
        self.example = myclass.Example(
            subdialogs=subdialogs,
            summaries=summaries,
            party_to_role=party_to_role,
            tuples_with_value=tuples_with_value,
            tuples_without_value=tuples_without_value)

    def set_celery_task(self, iter_idx, try_idxs, celery_task_id):
        for try_idx in try_idxs:
            self.iter_idx_to_try_idx_to_celery_task[iter_idx][try_idx] = \
                myclass.CeleryTask(task_id=celery_task_id)

    def set_dummy_celery_task(self, iter_idx, try_idxs):
        for try_idx in try_idxs:
            self.iter_idx_to_try_idx_to_celery_task[iter_idx][try_idx] = \
                myclass.CeleryTask(task_id=config.FINISHED)

    def get_celery_task(self, iter_idx, try_idx):
        ret = self.iter_idx_to_try_idx_to_celery_task[iter_idx].get(
            try_idx, None)
        return ret

    def wait_for_celery_task(self):
        celery_task = self.get_celery_task(self.curr_iter_idx,
                                           self.curr_try_idx)

        if celery_task is None:
            return False

        if celery_task.task_id == config.FINISHED:
            return True

        with celery_task.condition:
            while celery_task.task_id != config.FINISHED:
                celery_task.condition.wait(timeout=15)
        return True

    def add_curr_try_idx(self):
        self.curr_try_idx += 1

    def update_curr_try(self, wait=True):
        # Makes sure we only update curr_try_idx when we actually discard the
        # current subdialog.
        if wait:
            successful_celery_task = self.wait_for_celery_task()
            assert successful_celery_task
        curr_try_path = os.path.join(self.iter_dir,
                                     f'try_{self.curr_try_idx:03}.yaml')
        assert os.path.exists(curr_try_path), f'{curr_try_path = }'

        curr_try = json.dumps(utils.read_yaml(curr_try_path))
        curr_try = myclass.Try.from_json(curr_try)
        self.example.curr_try = curr_try

    def reset_for_next_iter(self):
        self.curr_iter_idx += 1
        self.curr_try_idx = 0

    def reset_curr_try(self):
        self.example.curr_try = None
        self.example.labeling_valid_turn_idx = -1

    def save_task(self,
                  worker_id,
                  filename=config.SUCCESS_FILENAME,
                  suffix=None):
        assert self.example
        worker_name = WORKER_MAP[worker_id]

        to_save = {
            'worker': {
                'id': worker_id,
                'name': worker_name
            },
            'init': {
                'task_id': self.task_id,
                'template_idx': self.template_idx,
                'accident_location': self.accident_location,
                'flow_id': self.flow_id,
                'story_generation': self.story_generation,
            },
            'status': {
                'step': self.step,
                'curr_iter_idx': self.curr_iter_idx,
                'curr_try_idx': self.curr_try_idx,
            },
            'iter_idx_to_step_to_time_spent_on_page':
            self.iter_idx_to_step_to_time_spent_on_page,
            'example': self.example.to_dict(),
        }

        if suffix:
            bn = os.path.basename(filename).split('.')[0]
            filename = f'{bn}_{suffix}.yaml'
            path = os.path.join(self.iter_dir, filename)
        else:
            path = os.path.join(self.iter_dir, filename)
        utils.save_yaml(path, to_save)

        sym_path = os.path.join(self.task_dir, filename)
        if os.path.islink(sym_path):
            # Remove the existing symbolic link
            os.unlink(sym_path)
        path = './' + '/'.join(path.split('/')[-2:])
        os.symlink(path, sym_path)

    @staticmethod
    def load_task(path):
        success_try = utils.read_yaml(path)
        example = myclass.Example.from_dict(success_try['example'])

        for turn in example.reference_history:
            if turn.raw_text:
                turn.raw_text = utils.clean_text(turn.raw_text)
            turn.text = utils.clean_text(turn.text)

        if example.curr_try:
            for i, turn in enumerate(example.curr_try.turns):
                if turn.raw_text:
                    turn.raw_text = utils.clean_text(turn.raw_text)
                turn.text = utils.clean_text(turn.text)
                example.curr_try.turns[i] = turn

        task = Task(**success_try['init'],
                    **success_try['status'],
                    iter_idx_to_step_to_time_spent_on_page=success_try.get(
                        'iter_idx_to_step_to_time_spent_on_page', None),
                    example=example)

        return task
