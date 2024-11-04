from __future__ import annotations

import json
import logging
import inspect

from typing import List, Dict
from pathlib import Path
import PyOpenColorIO as OCIO

from .. import operators

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AYONHieroEffectsFileProcessor(object):
    """Class for processing an AYON Hiero effects file.

    Arguments:
        filepath (Path): Path to the effects file.
        target_dir_path (Path): Target directory path for the operator.
        logger (logging.Logger): Logger instance.
    """

    filepath: Path = None
    target_dir_path: Path = None
    log: logging.Logger = log

    _wrapper_class_members = dict(
        inspect.getmembers(operators, inspect.isclass))
    _color_ops: List = []
    _repo_ops: List = []

    def __init__(
        self,
        filepath: Path,
        target_dir_path: Path = None,
        logger: logging.Logger = None,
    ) -> None:
        self.filepath = filepath
        self.target_dir_path = target_dir_path
        if logger:
            self.log = logger

        self.load()

    @property
    def ocio_objects(self) -> List:
        """List of OCIO objects to be processed."""
        ops = []
        for op in self._color_ops:
            ops.append(op.to_ocio_obj())
        return ops

    @property
    def repo_operators(self) -> Dict:
        """List of repositioning operators to be processed."""
        return self._repo_ops

    def load(self) -> None:
        """Loads the effects file.
        Attention:
            This method clears the lists of all operators before loading.
        """
        # first clear all operators
        self.clear_operators()

        # load the effect file
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
            # feed data into class object
            class_obj = class_obj.from_node_data(node_value)

            # separate color ops from repo ops
            if isinstance(class_obj, operators.ColorOperator):
                self._color_ops.append(class_obj)
            elif isinstance(class_obj, operators.RepositionOperator):
                self._repo_ops.append(class_obj)

    def _sanitize_file_path(
        self, node_value: dict, all_relative_files: dict
    ) -> None:
        filepath = Path(node_value["file"])

        if self.target_dir_path:
            new_file_path = (
                self.target_dir_path / filepath.name).as_posix()
            # set file with extension
            node_value["file"] = new_file_path
            self.log.debug(f"new_file_path: {new_file_path}")
            return

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
        """Clears lists of all operators."""
        self._color_ops = []
        self._repo_ops = []

    def get_oiiotool_cmd(self) -> List[str]:
        """Returns arguments for oiiotool command."""
        args = []
        for oo in self.ocio_objects:
            if isinstance(oo, OCIO.FileTransform):
                lut = Path(oo.getSrc()).resolve()
                args.extend(["--ociofiletransform", f"{lut.as_posix()}"])
            if isinstance(oo, OCIO.ColorSpaceTransform):
                args.extend(["--colorconvert", oo.getSrc(), oo.getDst()])
        for ro in self.repo_operators:
            args.extend(ro.to_oiio_args())

        return args
