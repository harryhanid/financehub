# tasks/flow_backup.py
import os
import datetime
import shutil
import traceback

import config


def _cleanup_old_files(folder: str, keep_days: int, prefix: str = "", suffix: str = "") -> None:
    """Delete dated files in `folder` older than `keep_days`.

    Files are expected to be named `<prefix><YYYY-MM-DD><suffix>`. Anything that
    doesn't parse as a date after stripping prefix/suffix is left alone.
    """
    if not os.path.exists(folder):
        return
    now = datetime.datetime.now()
    for fname in os.listdir(folder):
        full_path = os.path.join(folder, fname)
        if not os.path.isfile(full_path):
            continue
        stem = fname
        if suffix and stem.endswith(suffix):
            stem = stem[: -len(suffix)]
        elif suffix:
            continue
        else:
            stem, _ = os.path.splitext(stem)
        
        if prefix and stem.startswith(prefix):
            stem = stem[len(prefix):]
        elif prefix:
            continue
        try:
            file_date = datetime.datetime.strptime(stem, "%Y-%m-%d")
        except ValueError:
            continue
        if (now - file_date).days > keep_days:
            os.remove(full_path)
