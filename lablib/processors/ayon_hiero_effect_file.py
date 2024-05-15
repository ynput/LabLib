from __future__ import annotations

import json
import inspect

from typing import Any, List, Dict, Tuple
from dataclasses import dataclass


from ..operators import (
    OCIOFileTransform,
    OCIOCDLTransform,
    OCIOColorSpace,
)

from .. import operators


@dataclass
class AYONHieroEffectsFileProcessor:
    src: str

    @property
    def color_operators(self) -> Dict:
        return self._color_ops

    @color_operators.setter
    def color_operators(self, color_ops: List) -> None:
        self._color_ops = color_ops

    @color_operators.deleter
    def color_operators(self) -> None:
        self._color_ops = []

    @property
    def repo_operators(self) -> Dict:
        return self._repo_ops

    @repo_operators.setter
    def repo_operators(self, repo_ops: List) -> None:
        self._repo_ops = repo_ops

    @repo_operators.deleter
    def repo_operators(self) -> None:
        self._repo_ops = []

    def __post_init__(self) -> None:
        self._wrapper_class_members = dict(
            inspect.getmembers(operators, inspect.isclass))

        self._color_ops: List = []
        self._repo_ops: List = []
        self._class_search_key: str = "class"
        self._index_search_key: str = "subTrackIndex"
        self._data_search_key: str = "node"
        self._valid_attrs: Tuple = (
            "in_colorspace",
            "out_colorspace",
            "file",
            "saturation",
            "display",
            "view",
            "translate",
            "rotate",
            "scale",
            "center",
            "power",
            "offset",
            "slope",
            "direction",
        )
        self._valid_attrs_mapping: Dict[str, str] = {
            "in_colorspace": "src",
            "out_colorspace": "dst",
            "file": "src",
            "saturation": "sat",
        }
        if self.src:
            self.load(self.src)

    def _get_operator_class(self, name: str) -> Any:
        name = "{}Transform".format(name.replace("OCIO", "").replace("Transform", ""))
        if name in self._wrapper_class_members:
            return self._wrapper_class_members[name]

        if "Repo{}".format(name) in self._wrapper_class_members:
            return self._wrapper_class_members["Repo{}".format(name)]

        return None

    def _get_operator_sanitized(self, op: Any, data: Dict) -> Any:
        # sanitize for different source data structures.
        # fix for nuke vs ocio, cdl transform should not have a src field by
        # OCIO specs
        if "CDL" in op.__name__:
            del data["src"]
        return op(**data)

    def _get_operator(self, data: Dict) -> None:
        result = {}
        for key, value in data[self._data_search_key].items():
            if key not in self._valid_attrs:
                continue

            if key in self._valid_attrs_mapping:
                result[self._valid_attrs_mapping[key]] = value
                continue

            if key == "scale" and isinstance(value, float):
                value = [value, value]
            result[key] = value

        op = self._get_operator_class(data[self._class_search_key])
        return self._get_operator_sanitized(op=op, data=result)

    def _load(self) -> None:
        with open(self.src, "r") as f:
            ops_data = json.load(f)

        all_ops = [v for _, v in ops_data.items() if isinstance(v, dict)]

        # TODO: what if there are multiple layer citizens with subTrackIndex
        all_ops.sort(key=lambda op: op[self._index_search_key])

        for value in all_ops:

            class_name = value["class"]

            if class_name not in self._wrapper_class_members.keys():
                continue

            class_obj = self._wrapper_class_members[class_name]
            class_obj = class_obj.from_node_data(value["node"])

            # separate color ops from repo ops
            if "color" in class_obj.__class__.__module__:
                self._color_ops.append(class_obj)
            else:
                self._repo_ops.append(class_obj)

    def clear_operators(self) -> None:
        self.color_ops = []
        self.repo_ops = []

    def load(self, src: str) -> None:
        self.src = src
        self.clear_operators()
        self._load()
