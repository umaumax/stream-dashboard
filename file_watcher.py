#!/usr/bin/env python3

import glob
import os
import time


class FileWatcher:
    def __init__(self, pattern):
        self.pattern = pattern
        self.previous_mod_times = {}

    def _get_file_modification_times(self, files):
        mod_times = {}
        for file in files:
            mod_times[file] = os.path.getmtime(file)
        return mod_times

    def _compare_file_dicts(self, prev_dict, current_dict):
        changes = {}

        for file, mod_time in current_dict.items():
            if file not in prev_dict:
                status = 'new'
            elif prev_dict[file] != mod_time:
                # Judged as an update even if time is backdated.
                status = 'updated'
            else:
                status = 'unchanged'
            changes[file] = {'status': status, 'mod_time': mod_time}

        for file in prev_dict:
            if file not in current_dict:
                changes[file] = {'status': 'deleted', 'mod_time': None}

        return changes

    def watch(self):
        files = sorted(glob.glob(self.pattern, recursive=True))
        current_mod_times = self._get_file_modification_times(files)
        changes = self._compare_file_dicts(
            self.previous_mod_times, current_mod_times)
        self.previous_mod_times = current_mod_times
        return changes


def main():
    pattern = '**/*.json'
    file_watcher = FileWatcher(pattern)
    while True:
        files = file_watcher.watch()
        print(files)
        time.sleep(1)


if __name__ == '__main__':
    main()
