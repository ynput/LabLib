from __future__ import annotations

import json
import logging

from typing import List, Any
from pathlib import Path

from ..operators import AYONOCIOLookProduct

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AYONOCIOLookFileProcessor(object):
    filepath: Path = None

    _color_ops: List = []

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

    @property
    def color_operators(self) -> List:
        return self._color_ops

    @color_operators.setter
    def color_operators(self, value: Any[List, str]) -> None:
        if isinstance(value, list):
            self._color_ops.extend(value)
        elif isinstance(value, str):
            self._color_ops.append(value)

    def _load(self) -> None:

        ociolook_file_path = self.filepath.resolve().as_posix()

        # get all relative files recursively so we can make sure files in
        # transforms are having correct path
        all_relative_files = {
            f.name: f for f in Path(self.filepath.parent).rglob("*")}

        with open(ociolook_file_path, "r") as f:
            ops_data = json.load(f)

        schema_data_version = ops_data.get("version", 1)

        if schema_data_version != 1:
            raise ValueError(
                f"Schema data version {schema_data_version} is not supported")

        # INFO: This is a temporary fix to handle the case where
        #   the filepath is not found in the data
        # add all relative files to the data
        for item in ops_data["data"]["ocioLookItems"]:
            self._sanitize_file_path(item, all_relative_files)

        class_obj = AYONOCIOLookProduct.from_node_data(ops_data["data"])

        self.color_operators = class_obj.to_ocio_obj()

    def _sanitize_file_path(self, repre_data: dict, all_relative_files: dict) -> None:  # noqa: E501

        extension = repre_data["ext"]

        for file, path in all_relative_files.items():
            if file.endswith(extension):
                repre_data["file"] = path.resolve().as_posix()
                break

        if not repre_data.get("file"):
            log.warning(
                f"File not found: {repre_data['name']}.{repre_data['ext']}."
            )

    def _clear_operators(self) -> None:
        self._color_ops = []

    def load(self) -> None:
        self._clear_operators()
        self._load()
