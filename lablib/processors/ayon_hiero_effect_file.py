from __future__ import annotations

import json
import logging
import inspect

from typing import List, Dict
from pathlib import Path

from .. import operators

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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

        effect_file_path = self.filepath.resolve().as_posix()

        # get all relative files recursively so we can make sure files in
        # transforms are having correct path
        all_relative_files = {
            f.name: f for f in Path(self.filepath.parent).rglob("*")}

        with open(effect_file_path, "r") as f:
            ops_data = json.load(f)

        all_ops = [v for _, v in ops_data.items() if isinstance(v, dict)]

        # TODO: what if there are multiple layer citizens with subTrackIndex
        all_ops.sort(key=lambda op: op["subTrackIndex"])

        for value in all_ops:

            class_name = value["class"]

            if class_name not in self._wrapper_class_members.keys():
                continue

            if not value.get("node"):
                continue

            node_value = value["node"]

            if node_value.get("file"):
                self._sanitize_file_path(node_value, all_relative_files)

            class_obj = self._wrapper_class_members[class_name]
            class_obj = class_obj.from_node_data(node_value)

            # separate color ops from repo ops
            if "color" in class_obj.__class__.__module__:
                self._color_ops.extend(class_obj)
            else:
                self._repo_ops.append(class_obj)

    def _sanitize_file_path(self, node_value: dict, all_relative_files: dict) -> None:

        filepath = Path(node_value["file"])
        if filepath.exists():
            node_value["file"] = filepath.as_posix()
            return
        if filepath.name not in all_relative_files.keys():
            return

        relative_file = all_relative_files[filepath.name]
        log.warning(
            f"File not found: {filepath.name}. Using file from "
            f"relative path instead: {relative_file.as_posix()}"
        )
        node_value["file"] = relative_file.resolve().as_posix()

    def clear_operators(self) -> None:
        self._color_ops = []
        self._repo_ops = []

    def load(self) -> None:
        self.clear_operators()
        self._load()
