import json
import os
import re
import warnings
from pathlib import Path
from random import choice
from string import ascii_letters, digits
from time import asctime

from flask import request

from app.config import cfg

from .exceptions import IngoredWarning, SudoersWarning


def get_sudoers():
    try:
        with cfg.SUDOERS_PATH.open() as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        warnings.warn(f"json decode error: {exc}", SudoersWarning)
        return []
    except FileNotFoundError:
        warnings.warn("Sudoers file not found", SudoersWarning)
        return []


def get_ignored():
    data = cfg.IGNORED_PATH.read_text()
    try:
        data = list(set(json.loads(data)))
        data.sort()
        return data
    except json.decoder.JSONDecodeError as exc:
        warnings.warn(f"json decode error: {exc}", IngoredWarning)
        return []


def add_to_ignored(folder):
    current_ignored = get_ignored()
    if folder in current_ignored:
        return False

    current_ignored.append(folder)
    current_ignored = list(set(current_ignored))
    current_ignored.sort()
    data = json.dumps(current_ignored, indent=4)
    cfg.IGNORED_PATH.write_text(data)
    return True


def remove_from_ignored(folder):
    current_ignored = get_ignored()
    if folder not in current_ignored:
        return False

    current_ignored.remove(folder)
    current_ignored = list(set(current_ignored))
    current_ignored.sort()
    data = json.dumps(current_ignored, indent=4)
    cfg.IGNORED_PATH.write_text(data)
    return True


def log(string, *args):
    timestamp = "[%s] - %s - " % (asctime(), request.remote_addr)
    with cfg.LOG_PATH.open("at") as f:
        f.write(timestamp + string % args + "\n")


def get_user():
    try:
        auth = request.authorization
    except RuntimeError:
        return None

    if not auth:
        return None
    else:
        return auth.username


def get_folders():
    ignored = get_ignored()
    folder_choices = [
        Path(x[0]).relative_to(cfg.CLOUD_PATH)
        for x in os.walk(cfg.CLOUD_PATH, followlinks=True)
    ]

    folders = []
    for folder in folder_choices:
        for pattern in ignored:
            if re.search(pattern, folder.as_posix(), re.IGNORECASE):
                break
        else:
            folders.append(folder)
    folder_choices = folders

    if get_user() not in get_sudoers():
        folder_choices = [x for x in folder_choices if filter_non_admin_folders(x)]

    folder_choices.sort()
    return folder_choices


def filter_non_admin_folders(x):
    return not (x.as_posix().startswith(".") and len(x.as_posix()) > 1)


def gen_random_password(n=16):
    possible = ascii_letters + digits
    return "".join([choice(possible) for x in range(n)])


def get_post_arg(form_name, required=False, strip=False):
    """Gets an arg from a post form and parses it.
    Args:
        form_name (str): key to extract.
        required (bool, optional): Marks the key as required. If it's not
            present, a RunTimeError will be raised. Defaults to False.
        strip (bool, optional): Strip the value before returning. Defaults to False.
    Raises:
        RuntimeError: If `required` is True and the key is not in the form data.
    Returns:
        str: value generated.
    """
    arg = request.form.get(form_name, None)

    if strip and isinstance(arg, str):
        arg = arg.strip()
        if not arg:
            arg = None

    if required and not arg:
        raise RuntimeError("%r is required (%r)" % (form_name, arg))

    return arg
