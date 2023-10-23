import sys

sys.path.append("src")

import collections
import copy
from dataclasses import dataclass
import re
import string

from fuzzywuzzy import fuzz
from src import config, utils

SIMILAR_VALUE_THRESHOLD = 85

default_frame = {
    "actions": None,
    "service": None,
    "slots": None,
    "state": {
        "active_intent": None,
        "requested_slots": None,
        "slot_values": collections.defaultdict(list),
    },
}

global_slots = {
    "Accident Location",
    "Witnesses",
    "Date of Accident",
    "Time of Accident",
    "Weather Visibility",
    "Num of Lanes",
    "Road Condition",
    "Traffic Condition",
    "Traffic Flow",
    "Police Report",
    "Police Department Name",
}

value_op_sep = " [vo] "

op_to_token = {
    "delete": "[delete]",
    "concat": "[concat]",
    "same": "[same]",
}

version = "v2.1"


def normalize_answer(s):
    """Lower text and remove punctuation, articles and extra whitespace."""

    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def group_similar_strings(lst):
    groups = []
    leaders = []

    for string in lst:
        added_to_group = False
        for leader in leaders:
            if fuzz.ratio(string.lower(),
                          leader.lower()) > SIMILAR_VALUE_THRESHOLD:
                group_index = leaders.index(leader)
                groups[group_index].append(string)
                added_to_group = True
                break

        if not added_to_group:
            leaders.append(string)
            groups.append([string])

    return groups


@dataclass
class AnnotationAndOperation(object):
    referent: str
    domain: str
    slot: str
    value: str
    operation: str
    is_categorical: bool = False

    def __eq__(self, other):
        return hash(other) == hash(self)

    def __hash__(self):
        return hash(
            f"{self.referent} {self.domain} {self.slot} {self.value} {self.operation}"
        )


def get_state_by_turn_idx(
    turn_idx,
    turns,
    apply_ops_at_turn_idx=False,
    start_idx=0,
    ignore_concat=False,
    consider_all_concat=False,
):
    """Gets the dialog state up to the turn_idx."""

    # Uses referent-domain-slot as a key to locate a slot.
    referent_domain_slot_to_annotations = collections.defaultdict(list)
    # for turn in turns[start_idx:turn_idx+1]:
    for curr_turn_idx, turn in enumerate(turns[:turn_idx + 1]):
        for ann in turn.annotations:
            if start_idx > curr_turn_idx:
                if not consider_all_concat:
                    continue

                if "concat" not in list(ann.states.values()):
                    continue

            if ann.slot in global_slots:
                ann.referent = "Global"

            referent_domain_slot = f"{ann.referent}-{ann.domain}-{ann.slot}"
            referent_domain_slot_to_annotations[referent_domain_slot].append(
                ann)

            assert (
                ann.value
                in turn.text), f"{turn_idx = } {ann.value = } {turn.text = }"

    # Merges annotations with the same referent-domain-slot by corresponding operations, keep, concat, delete.
    referent_domain_slot_to_annotations_after_operations = collections.defaultdict(
        list)
    for (
            referent_domain_slot,
            annotations,
    ) in referent_domain_slot_to_annotations.items():
        referent, domain, slot = referent_domain_slot.split("-")
        concat_annotations = []
        for ann in annotations:
            state = "keep"
            if ann.states:
                if len(ann.states.keys()) != 0:
                    state_idxs = sorted(
                        [idx for idx in ann.states.keys() if idx <= turn_idx])
                    if state_idxs:
                        state_idx = state_idxs[-1]
                        state = ann.states[state_idx]

                if state == "concat":
                    state_idx = min(ann.states.keys())
                    assert len(set(ann.states.values())) == 1, set(
                        ann.states.values())

            if state == "delete":
                if turn_idx > state_idx or apply_ops_at_turn_idx:
                    continue
                else:
                    referent_domain_slot_to_annotations_after_operations[
                        referent_domain_slot].append({
                            "annotation": ann,
                            "operation": state,
                        })

            elif state == "keep":
                referent_domain_slot_to_annotations_after_operations[
                    referent_domain_slot].append({
                        "annotation": ann,
                        "operation": state,
                    })

            elif not ignore_concat and state == "concat":  # concat
                # elif state == 'concat': # concat
                if turn_idx > state_idx or apply_ops_at_turn_idx:
                    concat_annotations.append(ann)
                elif turn_idx == state_idx:
                    referent_domain_slot_to_annotations_after_operations[
                        referent_domain_slot].append({
                            "annotation": ann,
                            "operation": state,
                        })
                else:
                    raise ValueError("Impossible state!")

        if concat_annotations:
            assert len(concat_annotations) > 1

            need_concat = True
            concat_values = [ann.value for ann in concat_annotations]
            grouped_values = group_similar_strings(concat_values)
            if len(grouped_values) == 1:
                need_concat = False

            tmp_ann = copy.deepcopy(concat_annotations[0])
            if need_concat:
                concat_values = []

                for group in grouped_values:
                    concat_values.append(group[0])

                concat_value = " ".join(concat_values)
                tmp_ann.value = concat_value

            referent_domain_slot_to_annotations_after_operations[
                referent_domain_slot].append({
                    "annotation": tmp_ann,
                    "operation": "keep",
                })

    # Filters out categorical tuples.
    for (
            referent_domain_slot,
            ann_and_op_pairs,
    ) in referent_domain_slot_to_annotations_after_operations.items():
        first_ann_and_op = ann_and_op_pairs[0]
        first_ann = first_ann_and_op["annotation"]
        is_categorical = first_ann.categorical_value != ""

        if not is_categorical:
            continue

        categorical_value_to_ann_and_op_pairs = collections.defaultdict(list)
        for ann_and_op in ann_and_op_pairs:
            ann = ann_and_op["annotation"]
            categorical_value_to_ann_and_op_pairs[
                ann.categorical_value].append(ann_and_op)

        # Removes mislabeled categorical values.
        # Turn 3: (left lane, keep).
        # Turn 4: (left lane, keep); (left lane, delete).
        problematic_categorical_values = set()
        for (
                categorical_value,
                ann_and_op_pairs,
        ) in categorical_value_to_ann_and_op_pairs.items():
            if len(ann_and_op_pairs) == 1:
                continue

            has_keep_op = False
            has_delete_op = False
            for ann_and_op in ann_and_op_pairs:
                op = ann_and_op["operation"]
                if op == "keep":
                    has_keep_op = True
                elif op == "delete":
                    has_delete_op = True
                else:
                    raise ValueError(
                        "Impossible state for categorical-value slot!")

            if not (has_keep_op and has_delete_op):
                continue

            for ann_and_op in ann_and_op_pairs:
                ann = ann_and_op["annotation"]
                op = ann_and_op["operation"]
                if op == "delete":
                    problematic_categorical_values.add(categorical_value)

        def filter_problematic_categorical_values(ann_and_op):
            ann = ann_and_op["annotation"]
            op = ann_and_op["operation"]
            if ann.categorical_value in problematic_categorical_values:
                if op == "delete":
                    return False
            return True

        ann_and_op_pairs = list(
            filter(filter_problematic_categorical_values, ann_and_op_pairs))
        referent_domain_slot_to_annotations_after_operations[
            referent_domain_slot] = ann_and_op_pairs

    final_state = []
    # Merges annotations with the same referent-domain-slot by values with high fuzzy scores.
    for (
            referent_domain_slot,
            annotations,
    ) in referent_domain_slot_to_annotations_after_operations.items():
        referent, domain, slot = referent_domain_slot.split("-")

        merged_annotations = []
        skip_extractive_concat = False
        skip_extractive_concat_values = []
        # Makes sure dealing with keep first then concat to filter out bad concat.
        sort_order = {"keep": 0, "concat": 1, "delete": 2}
        for ann_and_operation in sorted(
                annotations, key=lambda x: sort_order[x["operation"]]):
            ann = ann_and_operation["annotation"]
            op = ann_and_operation["operation"]

            is_categorical = ann.categorical_value != ""
            values = [temp_ann.value for temp_ann in merged_annotations]

            if slot in {"First Name", "Last Name"}:
                for temp_ann in merged_annotations:
                    values.extend(set(temp_ann.value.split(" ")))

            if is_categorical:
                value = ann.categorical_value
                if value in values:
                    continue
            else:
                value = ann.value

                # Only do fuzzy matching on extractive values.
                if merged_annotations:
                    normalized_values = list(map(normalize_answer, values))
                    normalized_value = normalize_answer(value)
                    fuzz_scores = list(
                        map(
                            lambda nv: fuzz.ratio(normalized_value, nv.lower()
                                                  ),
                            normalized_values,
                        ))
                    if max(fuzz_scores) > SIMILAR_VALUE_THRESHOLD:
                        if not is_categorical and op == "concat":
                            skip_extractive_concat_values.append({
                                "value":
                                value,
                                "prev_values":
                                values
                            })
                            skip_extractive_concat = True
                        continue

            ann_op = AnnotationAndOperation(
                referent=ann.referent,
                domain=ann.domain,
                slot=ann.slot,
                value=value,
                is_categorical=is_categorical,
                operation=op,
            )
            merged_annotations.append(ann_op)

        if skip_extractive_concat:
            print(f"{skip_extractive_concat_values = }")

        # If extractive
        if not is_categorical:
            if len(merged_annotations) == 1:
                if skip_extractive_concat:
                    if merged_annotations[0].operation == "concat":
                        merged_annotations[0].operation = "keep"

        final_state.extend(merged_annotations)
    return final_state


def get_frames_for_state_change(state, add_op_to_value=False):
    frames = {}
    for domain in config.DOMAINS:
        frame = frames.get(domain, copy.deepcopy(default_frame))
        frame["service"] = domain
        frames[domain] = frame

    slot_to_num_concat = {}
    for ann in state:
        if ann.slot in global_slots:
            ann.referent = "Global"

        if ann.operation == "concat":
            slot_to_num_concat[ann.slot] = slot_to_num_concat.get(ann.slot,
                                                                  0) + 1

        referent_slot = f"{ann.referent}-{ann.slot}"
        frame = frames[ann.domain]

        value = ann.value
        if ann.is_categorical:
            value = value.strip(string.punctuation).strip()

        if add_op_to_value and ann.operation != "keep":
            op = op_to_token[ann.operation]
            value = value_op_sep.join([value, op])

        frame["state"]["slot_values"][referent_slot].append(value)
        frames[ann.domain] = frame

    for slot, num_concat in slot_to_num_concat.items():
        assert num_concat > 1, f"{slot = } {num_concat =}"

    return frames


def process_dst_at_time_t(merged_turns, turn_idx, prev_state,
                          most_recent_k_turns_for_state_change):
    assert most_recent_k_turns_for_state_change is None
    state = get_state_by_turn_idx(turn_idx, merged_turns)

    state_change = []
    to_removed_ann = []
    for ann in state:
        if ann in prev_state:
            to_removed_ann.append(ann)
            prev_state.remove(ann)
        else:
            state_change.append(ann)
    for ann in to_removed_ann:
        state.remove(ann)

    frames_state_change = get_frames_for_state_change(state_change)
    prev_state = get_state_by_turn_idx(turn_idx,
                                       merged_turns,
                                       apply_ops_at_turn_idx=True)
    frames_after_ops = get_frames_for_state_change(prev_state)
    return frames_state_change, prev_state, frames_after_ops


def process_state_change_at_time_t(
    merged_turns,
    turn_idx,
    last_turn_idx,
    prev_state,
    most_recent_k_turns_for_state_change,
):
    assert most_recent_k_turns_for_state_change is not None
    start_idx = max(turn_idx - most_recent_k_turns_for_state_change, 0)
    state = get_state_by_turn_idx(
        turn_idx,
        merged_turns,
        start_idx=max(start_idx - 2, 0),
        consider_all_concat=True,
    )

    tmp_prev_state = copy.deepcopy(prev_state)
    state_change = []
    to_removed_ann = []
    for ann in state:
        if ann in tmp_prev_state:
            to_removed_ann.append(ann)
            tmp_prev_state.remove(ann)
        else:
            state_change.append(ann)
    for ann in to_removed_ann:
        state.remove(ann)

    tlb_state = get_state_by_turn_idx(turn_idx,
                                      merged_turns,
                                      start_idx=last_turn_idx + 1,
                                      ignore_concat=True)

    tmp_prev_state = copy.deepcopy(prev_state)
    for ann in tlb_state:
        if ann not in tmp_prev_state:
            continue

        tmp_prev_state.remove(ann)
        already_in_state_change = False
        for ann2 in state_change:
            if ann2.referent != ann.referent:
                continue
            if ann2.domain != ann.domain:
                continue
            if ann2.slot != ann.slot:
                continue

            if ann.value in ann2.value:
                already_in_state_change = True
                break
            if fuzz.ratio(ann.value, ann2.value) > SIMILAR_VALUE_THRESHOLD:
                already_in_state_change = True
                break

        if not already_in_state_change:
            ann.operation = "same"
            state_change.append(ann)

    frames_state_change = get_frames_for_state_change(state_change,
                                                      add_op_to_value=True)

    prev_state = get_state_by_turn_idx(
        turn_idx,
        merged_turns,
        start_idx=start_idx,
        apply_ops_at_turn_idx=True,
        consider_all_concat=True,
    )

    frames_after_ops = get_frames_for_state_change(prev_state)
    last_turn_idx = turn_idx

    return frames_state_change, prev_state, frames_after_ops, last_turn_idx


def process_tlb_at_time_t(merged_turns, turn_idx, last_turn_idx,
                          most_recent_k_turns_for_state_change):
    assert most_recent_k_turns_for_state_change is None
    start_idx = last_turn_idx + 1
    state = get_state_by_turn_idx(turn_idx,
                                  merged_turns,
                                  start_idx=start_idx,
                                  ignore_concat=True)

    frames_after_ops = get_frames_for_state_change(state)
    assert turn_idx - last_turn_idx == 2, f"{last_turn_idx = } {turn_idx = }"
    last_turn_idx = turn_idx
    frames_state_change = {}
    return frames_state_change, frames_after_ops, last_turn_idx


def replace_names(text, name_map):
    for old_name, new_name in name_map.items():
        if old_name in text:
            text = text.replace(old_name, new_name)

        if old_name.upper() in text:
            text = text.replace(old_name.upper(), new_name.upper())
    return text


def replace_sensitive_info(text, sensitive_info):
    for old, new in sensitive_info.items():
        if old in text:
            text = text.replace(old, new)
            print(
                f"[Replace sensitive info] {text = } ||| {old = } ||| {new = } ||| {text = }"
            )

        if old.upper() in text:
            text = text.replace(old.upper(), new.upper())
            print(
                f"Replace sensitive info] {text = } ||| {old.upper() = } ||| {new.upper() = } ||| {text = }"
            )

        if old.title() in text:
            text = text.replace(old.title(), new.title())
            print(
                f"Replace sensitive info] {text = } ||| {old.title() = } ||| {new.title() = } ||| {text = }"
            )
    return text


def dialgen_to_mwoz_format(
    task_name,
    task_id,
    turns,
    most_recent_k_turns_for_state_change,
    name_map=None,
    sensitive_info=None,
):
    """Converts a dialog in DialGen format to a dialog in MultiWOZ format.
    Args:
    task_name(str): One of 'dst', 'state_change', 'tlb'.
    task_id (str): DialGen task_nameid.
    turns (list): A list of Turn objects.
    most_recent_k_turns_for_state_change (int): The number of previous turns for
        creating state to prevent from exceeding length limit. Since T5 token
        limitation, a full state could be too long to fit.
    name_map (Dict[str, str]): A dict mapping old names to new names to avoid leaking private info from the LLM.
    sensitive_info (Dict[str, str]): A dict mapping sensitive info to de-identified info.
        For example, a private comapny name might be added to prompt or
        be generated by the LLM, you can provide the mapping to replace them.
    """

    role_to_mwoz_role = {
        "user": "USER",
        "agent": "SYSTEM",
    }

    turns = utils.merge_neighbor_turns(turns)

    mwoz_turns = []
    unique_domains = set()
    prev_state = []

    last_turn_idx = -1

    # replace annotation by name_map
    if name_map is not None:
        for turn in turns:
            for ann in turn.annotations:
                ann.value = replace_names(ann.value, name_map)
            turn.text = replace_names(turn.text, name_map)

    if sensitive_info is not None:
        for turn in turns:
            for ann in turn.annotations:
                ann.value = replace_sensitive_info(ann.value, sensitive_info)
                ann.categorical_value = replace_sensitive_info(
                    ann.categorical_value, sensitive_info)
            turn.text = replace_sensitive_info(turn.text, sensitive_info)

    for turn_idx, turn in enumerate(turns):
        domains = set([ann.domain for ann in turn.annotations])
        unique_domains.update(domains)

        role = role_to_mwoz_role[turn.role]
        turn_text = turn.text

        if turn.role == "agent":
            # We considers a pair of user and agent turns.
            mwoz_turns.append(
                dict(
                    speaker=role,
                    turn_id=turn_idx,
                    utterance=turn_text,
                    frames=[],
                    frames_state_change=[],
                ))
            continue

        if task_name == "dst":
            frames_state_change, prev_state, frames_after_ops = process_dst_at_time_t(
                turns,
                turn_idx,
                prev_state,
                most_recent_k_turns_for_state_change,
            )

        elif task_name == "state_change":
            (
                frames_state_change,
                prev_state,
                frames_after_ops,
                last_turn_idx,
            ) = process_state_change_at_time_t(
                turns,
                turn_idx,
                last_turn_idx,
                prev_state,
                most_recent_k_turns_for_state_change,
            )

        elif task_name == "tlb":
            (
                frames_state_change,
                frames_after_ops,
                last_turn_idx,
            ) = process_tlb_at_time_t(
                turns,
                turn_idx,
                last_turn_idx,
                most_recent_k_turns_for_state_change,
            )
        else:
            raise ValueError(f"Unknown task: {task}")

        assert turn.role == "user"

        # Converts defaultdict to dict (slot_values).
        copy_frames_state_change = copy.deepcopy(frames_state_change)
        for domain, frame in sorted(copy_frames_state_change.items(),
                                    key=lambda x: config.DOMAINS.index(x[0])):
            frame["state"]["slot_values"] = dict(frame["state"]["slot_values"])

        # Converts defaultdict to dict (slot_values).
        copy_frames_after_ops = copy.deepcopy(frames_after_ops)
        for domain, frame in sorted(copy_frames_after_ops.items(),
                                    key=lambda x: config.DOMAINS.index(x[0])):
            frame["state"]["slot_values"] = dict(frame["state"]["slot_values"])

        mwoz_turns.append(
            dict(
                speaker=role,
                turn_id=turn_idx,
                utterance=turn_text,
                frames=[value for _, value in copy_frames_after_ops.items()],
                frames_state_change=[
                    value for _, value in copy_frames_state_change.items()
                ],
            ))

    unique_domains = sorted(list(unique_domains),
                            key=lambda x: config.DOMAINS.index(x))

    example = dict(
        dialogue_id=task_id,
        services=unique_domains,
        turns=mwoz_turns,
    )
    return example
