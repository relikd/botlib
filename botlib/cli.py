#!/usr/bin/env python3
import os
from argparse import ArgumentParser, ArgumentTypeError, FileType, Namespace
from typing import Any


def DirType(string: str) -> str:
    if os.path.isdir(string):
        return string
    raise ArgumentTypeError(
        'Directory does not exist: "{}"'.format(os.path.abspath(string)))


class Cli(ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def arg(self, *args: Any, **kwargs: Any) -> None:
        self.add_argument(*args, **kwargs)

    def arg_bool(self, *args: Any, **kwargs: Any) -> None:
        self.add_argument(*args, **kwargs, action='store_true')

    def arg_dir(self, *args: Any, **kwargs: Any) -> None:
        self.add_argument(*args, **kwargs, type=DirType)

    def arg_file(self, *args: Any, mode: str = 'r', **kwargs: Any) -> None:
        self.add_argument(*args, **kwargs, type=FileType(mode))

    def parse(self) -> Namespace:
        return self.parse_args()
