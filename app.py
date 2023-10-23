import collections
import copy
import json
import os

import decouple
from flask import (Flask, request, render_template, url_for, jsonify, redirect,
                   send_file)

from src import (config, convert, myclass, mytask_manager, rename_utils, utils,
                 yaml_to_xlsx)

app = Flask(__name__)

task_manager = mytask_manager.TaskManager()

WORKER_MAP = utils.read_yaml(config.WORKER_MAP_PATH)

domain_to_show_slots = {}
domain_to_condition_slots = {}


def precheck(task_id, worker_id, worker_name, all_tasks_loaded):
    if worker_id not in WORKER_MAP:
        return render_template('error.html',
                               task_id=task_id,
                               worker_id=worker_id,
                               worker_name=worker_name)

    if not all_tasks_loaded:
        return render_template('maintainance.html',
                               task_id=task_id,
                               worker_id=worker_id,
                               worker_name=worker_name)
    return None


@app.route('/receive_signals', methods=['POST'])
def receive_signals():
    """Receives signals from celery task_manager and makes api key available."""
    if request.method == 'POST':
        res = request.json
        api_key = res['api_key']
        task_id = res['task_id']
        iter_idx = res['iter_idx']
        try_idxs = res['try_idxs']
        task_manager.put_api_key(api_key)
        task = task_manager[task_id]

        for try_idx in try_idxs:
            celery_task = task.get_celery_task(iter_idx, try_idx)
            assert celery_task

            with celery_task.condition:
                celery_task.task_id = config.FINISHED
                celery_task.condition.notify_all()
    return 'done'


@app.route('/admin')
def admin():
    if not task_manager.all_tasks_loaded:
        task_manager.load()
    return redirect(url_for("api_keys"))


@app.route('/api_keys')
def api_keys():
    api_keys = list(task_manager.api_keys.queue)
    all_api_keys = set(config.API_KEYS)
    api_keys_in_use = list(all_api_keys - set(api_keys))
    return render_template('api_keys.html',
                           api_keys=api_keys,
                           api_keys_in_use=api_keys_in_use)


@app.route('/thankyou')
def thankyou():
    task_id = request.args.get('task_id')
    worker_id = request.args.get('worker_id')
    worker_name = WORKER_MAP[worker_id]

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]

    return render_template('thankyou.html',
                           task_id=task_id,
                           worker_id=worker_id,
                           worker_name=worker_name,
                           total_time_spent=task.total_time_spent)


@app.route('/main', methods=['GET'])
def main():
    task_id = request.args.get('task_id', None)
    worker_id = request.args.get('worker_id', None)
    worker_name = WORKER_MAP.get(worker_id, None)

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    #try:
    task = task_manager[task_id]
    # TODO (roylu): handling the `relabeled_and_done` case when relaunch the website.
    if task.step in {'done', 'relabeled_and_done', 'done_iaa'}:
        return redirect(
            url_for("thankyou", task_id=task_id, worker_id=worker_id))
    elif task.step == 'generation':
        return redirect(
            url_for("generation", task_id=task_id, worker_id=worker_id))
    elif task.step == 'labeling':
        return redirect(
            url_for("labeling", task_id=task_id, worker_id=worker_id))
    elif task.step == 'final_review':
        return redirect(
            url_for("final_review", task_id=task_id, worker_id=worker_id))
    return render_template('error.html',
                           task_id=task_id,
                           worker_id=worker_id,
                           worker_name=worker_name)


@app.route('/generation')
def generation():
    task_id = request.args.get('task_id')
    worker_id = request.args.get('worker_id')
    scroll_down = request.args.get('scroll_down', False)
    worker_name = WORKER_MAP[worker_id]

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]
    if task.step != 'generation':
        return redirect(url_for("main", task_id=task_id, worker_id=worker_id))

    default_instructions = config.DEFAULT_INSTRUCTIONS
    for i, instruction in enumerate(default_instructions):
        default_instructions[i] = instruction.format(
            user_name=task.example.role_to_party['user'],
            agent_name=task.example.role_to_party['agent'])

    return render_template('generation.html',
                           domains=config.DOMAINS,
                           domain_to_show_slots=domain_to_show_slots,
                           scroll_down=scroll_down,
                           page_time_spent=task.page_time_spent,
                           total_time_spent=task.total_time_spent,
                           default_instructions=default_instructions,
                           **task.example.for_rendering_html())


@app.route('/final_review')
def final_review():
    task_id = request.args.get('task_id')
    worker_id = request.args.get('worker_id')
    worker_name = WORKER_MAP[worker_id]

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]
    #if task.step != 'final_review':
    #    return redirect(url_for("main", task_id=task_id, worker_id=worker_id))

    return render_template(
        'final_review.html',
        domains=config.DOMAINS,
        domain_to_show_slots=domain_to_show_slots,
        scroll_down=False,
        page_time_spent=task.page_time_spent,
        total_time_spent=task.total_time_spent,
        disable_edit=task.step == 'final_review_after_relabeling',
        **task.example.for_rendering_html())


@app.route('/regenerate', methods=['POST'])
def regenerate():
    res = request.json
    task_id = res['task_id']
    worker_id = res['worker_id']
    worker_name = WORKER_MAP[worker_id]
    time_spent_on_page = res['time_spent_on_page']

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]
    task.example.instruction = res['instruction']
    task.update_time_spent(time_spent_on_page)

    task_manager.regenerate_by_task_id(task_id)

    return jsonify(
        url_for("generation",
                task_id=task_id,
                worker_id=worker_id,
                scroll_down=True))


@app.route('/submit', methods=['POST'])
def submit():
    res = request.json
    task_id = res['task_id']
    worker_id = res['worker_id']
    worker_name = WORKER_MAP[worker_id]
    instruction = res['instruction']
    time_spent_on_page = res['time_spent_on_page']

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    turns = res['turns']
    task = task_manager[task_id]
    task.example.update_turns(turns, task.curr_iter_idx)
    task.example.instruction = instruction
    task.update_time_spent(time_spent_on_page)

    task.step = 'labeling'
    task.save_task(worker_id)
    task_manager.prefab_try_for_next_iter_by_task_id(task_id, worker_id)
    return jsonify(url_for("labeling", task_id=task_id, worker_id=worker_id))


@app.route('/labeling', methods=['GET'])
def labeling():
    worker_id = request.args.get('worker_id')
    task_id = request.args.get('task_id')
    worker_name = WORKER_MAP.get(worker_id, None)

    print(f"@@@@@ Enter labeling {task_id = } {worker_id = } @@@@@")

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]
    # Prevents the user entering wrong step
    if task.step != 'labeling':
        return redirect(url_for("main", task_id=task_id, worker_id=worker_id))

    submit_button_display = 'Go to Generation'
    if task.example.last_subdialog:
        submit_button_display = 'Finish the Task'

    return render_template(
        'labeling.html',
        schema=config.SCHEMA['schema'],
        referent_schema=config.SCHEMA['referent_schema'],
        turn_to_be_annotated=task.example.turn_to_be_annotated,
        allow_back=task.allow_back,
        is_submit=task.last_turn_to_be_annotated,
        submit_button_display=submit_button_display,
        domains=config.DOMAINS,
        domain_to_show_slots=domain_to_show_slots,
        page_time_spent=task.page_time_spent,
        total_time_spent=task.total_time_spent,
        **task.example.for_rendering_html())


@app.route('/turn_relabeling_submit', methods=['POST'])
def turn_relabeling_submit():
    res = request.json
    task_id = res['task_id']
    worker_id = res['worker_id']
    turn_idx = res['turn_idx']
    clean_annotations = res.get('clean_annotations', False)
    worker_name = WORKER_MAP.get(worker_id, None)

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    time_spent_on_page = res['time_spent_on_page']
    turns = res['turns']
    task = task_manager[task_id]
    task.example.update_history_turns(turns)
    task.update_time_spent(time_spent_on_page)

    if clean_annotations:
        task.example.clean_annotations_by_turn_idx(turn_idx)

    return jsonify(
        url_for('turn_relabeling',
                turn_idx=turn_idx,
                task_id=task_id,
                worker_id=worker_id))


@app.route('/turn_relabeling', methods=['GET'])
def turn_relabeling():
    worker_id = request.args.get('worker_id')
    task_id = request.args.get('task_id')
    turn_idx = int(request.args.get('turn_idx'))
    worker_name = WORKER_MAP.get(worker_id, None)

    print(f"@@@@@ Enter labeling {task_id = } {worker_id = } @@@@@")

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    # Prevents the user entering wrong step
    task = task_manager[task_id]
    if task.step not in {'final_review', 'final_review_after_relabeling'}:
        return redirect(url_for("main", task_id=task_id, worker_id=worker_id))

    return render_template(
        'turn_relabeling.html',
        schema=config.SCHEMA['schema'],
        referent_schema=config.SCHEMA['referent_schema'],
        turn_to_be_annotated=task.example.turn_to_be_annotated_by_idx(
            turn_idx),
        domains=config.DOMAINS,
        domain_to_show_slots=domain_to_show_slots,
        page_time_spent=task.page_time_spent,
        total_time_spent=task.total_time_spent,
        **task.example.for_rendering_html(curr_idx=turn_idx))


@app.route('/back', methods=['POST'])
def back():
    res = request.json
    task_id = res.pop('task_id')
    worker_id = res.pop('worker_id')
    time_spent_on_page = res.pop('time_spent_on_page')
    worker_name = WORKER_MAP.get(worker_id, None)

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]
    task.example.add_annotations_to_turn(**res)
    task.example.labeling_valid_turn_idx -= 1
    task.update_time_spent(time_spent_on_page)

    # Render a new page for the next-turn annotation.
    # It will enter the function again but execute `render_template`.
    if task.step == 'labeling':
        return jsonify(
            url_for('labeling', task_id=task_id, worker_id=worker_id))


@app.route('/annotation', methods=['POST'])
def annotation():
    res = request.json
    task_id = res.pop('task_id')
    worker_id = res.pop('worker_id')
    time_spent_on_page = res.get('time_spent_on_page', 0)
    worker_name = WORKER_MAP.get(worker_id, None)

    print(f"@@@@@ Enter annotation {task_id = } {worker_id = } @@@@@")

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]
    task.example.add_annotations_to_turn(res['annotations'])
    task.example.labeling_valid_turn_idx += 1
    task.example.update_duplicate_tuples(res['duplicate_tuples'])
    task.update_time_spent(time_spent_on_page)

    # End of the labeling step.
    if task.example.turn_to_be_annotated is None:
        if task.example.last_subdialog:
            # No more turn to be annotated and the subdialog is the last one.
            # Directly return to thank you page.
            task.example.add_curr_try_turns_to_subdialogs()
            task.reset_curr_try()

            task.step = 'final_review'
            task.save_task(worker_id)
        else:
            # No more turn to be annotated. Switchs back to the generation.
            # Switchs back to the generatio and Changes the status to generation.
            task.example.add_curr_try_turns_to_subdialogs()
            task.reset_curr_try()
            task.step = 'generation'
            task.save_task(worker_id)
            # Save task first before setting instruction as empty string.
            task.example.instruction = ''
            task.reset_for_next_iter()
            task.update_curr_try()

    # Render a new page for the next-turn annotation.
    # It will enter the function again but execute `render_template`.
    return jsonify(url_for("main", task_id=task_id, worker_id=worker_id))


@app.route('/turn_annotation', methods=['POST'])
def turn_annotation():
    res = request.json
    task_id = res.pop('task_id')
    worker_id = res.pop('worker_id')
    turn_idx = int(res.pop('turn_idx'))
    time_spent_on_page = res.pop('time_spent_on_page')
    worker_name = WORKER_MAP.get(worker_id, None)

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    task = task_manager[task_id]
    task.example.add_annotations_to_turn(res['annotations'],
                                         turn_idx=turn_idx,
                                         add_to_history=True)
    task.example.update_duplicate_tuples_by_curr_idx(res['duplicate_tuples'],
                                                     turn_idx)
    task.update_time_spent(time_spent_on_page)

    return jsonify(url_for("main", task_id=task_id, worker_id=worker_id))
    #return jsonify(url_for("final_review", task_id=task_id, worker_id=worker_id))


@app.route('/download', methods=['GET'])
def download_file():
    task_id = request.args.get('task_id')
    #worker_id = request.args.get('worker_id')
    task = request.args.get('task')
    replace_names = request.args.get('replace_names', False)
    if replace_names == 'true':
        replace_names = True
    else:
        replace_names = False

    raw_path = f'data/tasks/{task_id}/final_review.yaml'
    if task == 'raw':
        p = raw_path
    elif task == 'xlsx':
        p = f'data/tasks/{task_id}/{task_id}.xlsx'
    else:
        if task == 'tlb':
            most_recent_k_turns_for_state_change = None
        elif task == 'dst':
            most_recent_k_turns_for_state_change = None
        elif task == 'state_change':
            most_recent_k_turns_for_state_change = decouple.config(
                'MOST_RECENT_K_TURNS_FOR_STATE_CHANGE', cast=int)
        else:
            raise ValueError(f'Invalid selected file type: {task}')

        if replace_names:
            output_path = f'data/tasks/{task_id}/{task_id}_{task}_replace_names.json'
        else:
            output_path = f'data/tasks/{task_id}/{task_id}_{task}.json'
        example = utils.read_yaml(raw_path)['example']
        example = myclass.Example.from_dict(example)

        name_map = None
        if replace_names:
            name_map = rename_utils.get_name_map(example)

        turns = sum([subdialog.turns for subdialog in example.subdialogs], [])
        example = convert.dialgen_to_mwoz_format(
            task, task_id, turns, most_recent_k_turns_for_state_change,
            name_map)
        with open(output_path, 'w') as f:
            json.dump(example, f, indent=4)

        p = output_path

    return send_file(p, as_attachment=True)


@app.route('/finish', methods=['POST'])
def finish():
    res = request.json
    task_id = res['task_id']
    worker_id = res['worker_id']
    worker_name = WORKER_MAP[worker_id]
    time_spent_on_page = res.pop('time_spent_on_page')

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    turns = res['turns']
    task = task_manager[task_id]
    task.example.last_subdialog = True
    task.example.update_turns(turns, task.curr_iter_idx)
    task.update_time_spent(time_spent_on_page)

    # All turns are deleted.
    if not task.example.curr_valid_turns:
        task.step = 'final_review'
        task.save_task(worker_id)
    else:
        task.step = 'labeling'
    return jsonify(url_for("main", task_id=task_id, worker_id=worker_id))


@app.route('/finish_review', methods=['POST'])
def finish_review():
    res = request.json
    task_id = res['task_id']
    worker_id = res['worker_id']
    worker_name = WORKER_MAP[worker_id]
    time_spent_on_page = res.pop('time_spent_on_page')

    render_fn = precheck(task_id, worker_id, worker_name,
                         task_manager.all_tasks_loaded)
    if render_fn is not None:
        return render_fn

    turns = res['turns']
    task = task_manager[task_id]
    task.example.last_subdialog = True
    task.example.update_history_turns(turns)
    task.update_time_spent(time_spent_on_page)

    task.step = 'done'
    task.save_task(worker_id, filename=config.FINAL_REVIEW_FILENAME)

    # Create the xlsx file.
    raw_yaml_path = f'data/tasks/{task_id}/{config.FINAL_REVIEW_FILENAME}'
    output_path = f'data/tasks/{task_id}/{task_id}.xlsx'
    print(raw_yaml_path, output_path)
    yaml_to_xlsx.convert_yaml_to_xlsx(task_id, raw_yaml_path, output_path)

    for task_name in ['tlb', 'dst', 'state_change']:
        example = copy.deepcopy(task.example)
        output_path = f'data/tasks/{task_id}/{task_name}.json'

        most_recent_k_turns_for_state_change = None
        if task_name == 'state_change':
            most_recent_k_turns_for_state_change = decouple.config(
                'MOST_RECENT_K_TURNS_FOR_STATE_CHANGE', cast=int)

        name_map = None
        turns = sum([subdialog.turns for subdialog in example.subdialogs], [])
        example = convert.dialgen_to_mwoz_format(
            task_name, task_id, turns, most_recent_k_turns_for_state_change,
            name_map)

        with open(output_path, 'w') as f:
            json.dump(example, f, indent=4)

        example = copy.deepcopy(task.example)
        output_path = f'data/tasks/{task_id}/{task_name}_replace_names.json'
        name_map = rename_utils.get_name_map(task.example)
        turns = sum([subdialog.turns for subdialog in example.subdialogs], [])
        example = convert.dialgen_to_mwoz_format(
            task_name, task_id, turns, most_recent_k_turns_for_state_change,
            name_map)

        with open(output_path, 'w') as f:
            json.dump(example, f, indent=4)

    return jsonify(url_for("thankyou", task_id=task_id, worker_id=worker_id))


@app.route('/reword', methods=['POST'])
def reword():
    res = request.json
    text = res['text']
    role = res['role']

    if role == 'agent':
        prefix = config.AGENT_TURN_REWRITE_TEMPLATE
    elif role == 'user':
        prefix = config.USER_TURN_REWRITE_TEMPLATE
    else:
        raise ValueError(f'Invalid role: {role}')

    prompt = f'{prefix}\n{text}'
    api_key = task_manager.get_api_key()
    text = utils.rewrite_via_chatgpt(prompt, api_key)
    task_manager.put_api_key(api_key)
    text = text.strip('\"')
    ret = {'text': text}
    return jsonify(ret)


@app.route('/modify_turns', methods=['POST'])
def modify_turns():
    res = request.json
    task_id = res.pop('task_id')
    worker_id = res.pop('worker_id')
    instruction = res['instruction']
    time_spent_on_page = res.pop('time_spent_on_page')

    selected_for_modification_idxs = list(
        map(int, res['selected_for_modification_idxs']))
    selected_for_modification_idxs = sorted(selected_for_modification_idxs)

    task = task_manager[task_id]
    task.update_time_spent(time_spent_on_page)
    task.example.instruction = res['instruction']
    curr_subdialog = task.example.for_rendering_html()['curr_subdialog']

    original_turns = [
        curr_subdialog[idx] for idx in selected_for_modification_idxs
    ]
    html_original_turns = [
        config.TURN_TEMPLATE.format(party=turn['party'], turn=turn['text'])
        for turn in original_turns
    ]
    text = config.TURN_SEP.join(html_original_turns).strip()

    prompt = f'{text}\n Follow the instruction to modify the turns in <p> </p>: {instruction} {config.TURN_REWRITE_TURNS_TEMPLATE}'
    api_key = task_manager.get_api_key()
    ret = utils.rewrite_turns_via_chatgpt(prompt,
                                          api_key).split(config.TURN_SEP)
    task_manager.put_api_key(api_key)

    new_turns = utils.extract_turns_from_llm_return(ret,
                                                    task.example.party_to_role)

    idx = selected_for_modification_idxs[0]
    for turn in new_turns[::-1]:
        turn['instruction'] = instruction
        curr_subdialog.insert(idx, turn)

    iter_idx = task.curr_iter_idx
    turn_idx = task.example.last_turn_idx_in_history + 1
    for turn in curr_subdialog:
        turn['turn_idx'] = turn_idx
        turn['iteration'] = iter_idx
        turn_idx += 1

    iter_dir = config.ITER_DIR_TEMPLATE.format(task_id, iter_idx)
    try_idx = task.curr_try_idx + 1
    os.makedirs(iter_dir, exist_ok=True)
    path = os.path.join(iter_dir, f'try_{try_idx:03}.yaml')

    curr_try = collections.OrderedDict(task_id=task_id,
                                       iter_idx=iter_idx,
                                       idx=try_idx,
                                       turns=curr_subdialog)
    utils.save_yaml(path, dict(curr_try))

    task.set_dummy_celery_task(iter_idx, [try_idx])
    task.add_curr_try_idx()
    task.update_curr_try(wait=False)

    return jsonify(
        url_for("generation",
                task_id=task_id,
                worker_id=worker_id,
                scroll_down=True))


if __name__ == '__main__':
    app.run(threaded=True)
