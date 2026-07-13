# -*- coding: utf-8 -*-
"""Prevent concurrent delivery tasks from sharing browser resources."""
import json
import os
from pathlib import Path


class RunLock:
    def __init__(self, path):
        self.path = Path(path)
        self.acquired = False

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False

        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid()}, handle)
        self.acquired = True
        return True

    def release(self):
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self.acquired = False