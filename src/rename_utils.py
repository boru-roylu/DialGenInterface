from faker import Faker
import string

from src import utils, myclass

import gender_guesser.detector as gender

gender_detector = gender.Detector().get_gender

fake = Faker()


def my_gender_detector(name):
    dic = {
        "mostly_male": "male",
        "male": "male",
        "mostly_female": "female",
        "female": "female",
    }

    gender = gender_detector(name)

    return dic.get(gender, gender)


def get_name():
    ret = fake.name().split()
    while len(ret) != 2 or ret[0].startswith("Mr.") or ret[0].startswith(
            "Mrs."):
        ret = fake.name().split()

    first = ret[0]
    last = ret[1]
    return first, last


def get_first_name():
    return get_name()[0]


def get_last_name():
    return get_name()[1]


def get_new_first_name(first_name, used_first_names):
    gender = my_gender_detector(first_name)

    while True:
        new_first_name = get_first_name()
        new_gender = my_gender_detector(new_first_name)

        if new_first_name == first_name:
            continue
        if new_first_name in used_first_names:
            continue

        if gender in {"andy", "unknown"}:
            break
        elif new_gender != gender:
            continue
        else:
            break
    return new_first_name


def get_new_last_name(last_name):
    while True:
        new_last_name = get_last_name()
        if new_last_name == last_name:
            continue
        else:
            break
    return new_last_name


def add_hyphen_between_characters(s):
    return "-".join(list(s))


def add_dot_between_characters(s):
    return ".".join(list(s))


def get_name_map(example: myclass.Example):
    translating = str.maketrans("", "", string.punctuation)

    turns = sum([subdialog.turns for subdialog in example.subdialogs], [])
    merged_turns = utils.merge_neighbor_turns(turns)

    agent_first_name = merged_turns[0].party

    # Avoids having the same names in the same conversation.
    used_first_names = {agent_first_name}

    caller_first_names = set()
    caller_last_names = set()
    other_first_names = set()
    other_last_names = set()
    # We only care about the annotated first and last names.
    for turn in merged_turns:
        for ann in turn.annotations:
            if ann.slot not in {"First Name", "Last Name"}:
                continue

            value = ann.value
            if value.endswith("'s"):
                value = value[:-2]

            value = value.translate(translating)
            value = value.title()

            if ann.referent == "Caller":
                if ann.slot == "First Name":
                    caller_first_names.add(value)
                else:
                    caller_last_names.add(value)

            elif ann.referent == "Other Driver":
                if ann.slot == "First Name":
                    other_first_names.add(value)
                else:
                    other_last_names.add(value)

    used_first_names.update(caller_first_names)
    used_first_names.update(other_first_names)
    name_map = {}

    # Caller.
    for caller_first_name in caller_first_names:
        name_map[caller_first_name] = get_new_first_name(
            caller_first_name, used_first_names)

    for caller_last_name in caller_last_names:
        name_map[caller_last_name] = get_new_last_name(caller_last_name)

    # Other driver.
    other_first_names = list(other_first_names)
    for other_first_name in other_first_names:
        name_map[other_first_name] = get_new_first_name(
            other_first_name, used_first_names)

    for other_last_name in other_last_names:
        name_map[other_last_name] = get_new_last_name(other_last_name)

    update = {}
    for old_name, new_name in name_map.items():
        old_name1 = add_hyphen_between_characters(old_name)
        new_name1 = add_hyphen_between_characters(new_name)
        update[old_name1] = new_name1
        old_name2 = add_dot_between_characters(old_name)
        new_name2 = add_dot_between_characters(new_name)
        update[old_name2] = new_name2
    name_map.update(update)

    return name_map
