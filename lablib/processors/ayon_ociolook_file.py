from __future__ import annotations

import json
import logging

from typing import List
from pathlib import Path
import PyOpenColorIO as OCIO


from ..operators import AYONOCIOLookProduct

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AYONOCIOLookFileProcessor(object):
    filepath: Path
    operator: AYONOCIOLookProduct

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.load()

    def load(self) -> None:
        self.operator = None  # clear operator
        ociolook_file_path = self.filepath.resolve().as_posix()

        # get all relative files recursively so we can make sure files in
        # transforms are having correct path
        all_relative_files = {f.name: f for f in Path(self.filepath.parent).rglob("*")}

        with open(ociolook_file_path, "r") as f:
            ops_data = json.load(f)

        schema_data_version = ops_data.get("version", 1)

        if schema_data_version != 1:
            raise ValueError(
                f"Schema data version {schema_data_version} is not supported"
            )

        # INFO: This is a temporary fix to handle the case where
        #   the filepath is not found in the data
        # add all relative files to the data
        for item in ops_data["data"]["ocioLookItems"]:
            self._sanitize_file_path(item, all_relative_files)

        self.operator = AYONOCIOLookProduct.from_node_data(ops_data["data"])

    def get_oiiotool_cmd(self) -> List[str]:
        args = []
        for xfm in self.color_operators:
            if isinstance(xfm, OCIO.FileTransform):
                lut = Path(xfm.getSrc()).resolve()
                args.extend(["--ociofiletransform", f"{lut.as_posix()}"])
            if isinstance(xfm, OCIO.ColorSpaceTransform):
                args.extend(["--colorconvert", xfm.getSrc(), xfm.getDst()])
        return args

    def _sanitize_file_path(self, repre_data: dict, all_relative_files: dict) -> None:  # noqa: E501
        extension = repre_data["ext"]

        for file, path in all_relative_files.items():
            if file.endswith(extension):
                repre_data["file"] = path.resolve().as_posix()
                break

        if not repre_data.get("file"):
            log.warning(f"File not found: {repre_data['name']}.{repre_data['ext']}.")
