from __future__ import annotations

import json
import inspect

from typing import List, Dict
from pathlib import Path

from .. import operators


class AYONHieroEffectsFileProcessor(object):
    filepath: Path = None

    _wrapper_class_members = dict(
        inspect.getmembers(operators, inspect.isclass))
    _color_ops: List = []
    _repo_ops: List = []

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

    @property
    def color_operators(self) -> List:
        return self._color_ops

    @property
    def repo_operators(self) -> Dict:
        return self._repo_ops

    def _load(self) -> None:
        with open(self.filepath.resolve().as_posix(), "r") as f:
            ops_data = json.load(f)

        all_ops = [v for _, v in ops_data.items() if isinstance(v, dict)]

        # TODO: what if there are multiple layer citizens with subTrackIndex
        all_ops.sort(key=lambda op: op["subTrackIndex"])

        for value in all_ops:

            class_name = value["class"]

            if class_name not in self._wrapper_class_members.keys():
                continue

            class_obj = self._wrapper_class_members[class_name]
            class_obj = class_obj.from_node_data(value["node"])

            # separate color ops from repo ops
            if "color" in class_obj.__class__.__module__:
                self._color_ops.extend(class_obj.to_ocio_obj())
            else:
                self._repo_ops.append(class_obj.to_oiio_args())

    def clear_operators(self) -> None:
        self.color_ops = []
        self.repo_ops = []

    def load(self) -> None:
        self.clear_operators()
        self._load()
