#!/usr/bin/env python3
import os
from argparse import ArgumentParser, ArgumentTypeError, FileType


def DirType(string):
    if os.path.isdir(string):
        return string
    raise ArgumentTypeError(
        'Directory does not exist: "{}"'.format(os.path.abspath(string)))


class Cli(ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def arg(self, *args, **kwargs):
        self.add_argument(*args, **kwargs)

    def arg_bool(self, *args, **kwargs):
        self.add_argument(*args, **kwargs, action='store_true')

    def arg_dir(self, *args, **kwargs):
        self.add_argument(*args, **kwargs, type=DirType)

    def arg_file(self, *args, mode='r', **kwargs):
        self.add_argument(*args, **kwargs, type=FileType(mode))

    def parse(self):
        return self.parse_args()
