from __future__ import annotations

import json
import logging

from typing import List
from pathlib import Path
import PyOpenColorIO as OCIO

from .. import operators

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AYONOCIOLookFileProcessor(object):
    """Class for processing an AYON OCIO Look file.

    Arguments:
        filepath (Path): Path to the OCIO Look file.

    Attributes:
        target_path (Path): Target path for the operator.
        log (logging.Logger): Logger instance.
    """

    filepath: Path
    target_path: Path = None
    log: logging.Logger = log

    _operators: List[OCIO.Transform] = []

    def __init__(
        self,
        filepath: Path,
        target_path: Path = None,
        logger: logging.Logger = None
    ) -> None:
        self.filepath = filepath
        self.target_path = target_path
        if logger:
            self.log = logger

        self.load()

    @property
    def color_operators(self) -> List:
        """List of color operators to be processed."""
        return self._operators

    def clear_operators(self) -> None:
        """Clears lists of all operators."""
        self._operators = []

    def load(self) -> None:
        """Load the OCIO Look file.

        Note:
            This globs all relative files recursively so we can make sure
            files in transforms are having correct path.

        Attention:
            This method clears the operator before loading the file.
        """
        # first clear all operators
        self.clear_operators()

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

        self._process_look_file_to_color_operators(ops_data["data"])

    def _process_look_file_to_color_operators(self, data: dict) -> None:
        """Process the OCIO Look file to color operators.

        Args:
            data (dict): The OCIO Look data.
        """

        look_working_colorspace = data["ocioLookWorkingSpace"]["colorspace"]
        look_items = data["ocioLookItems"]

        for index, item in enumerate(look_items):
            filepath = item["file"]
            lut_in_colorspace = item["input_colorspace"]["colorspace"]
            lut_out_colorspace = item["output_colorspace"]["colorspace"]
            direction = item["direction"]
            interpolation = item["interpolation"]

            if index == 0:
                # set the first colorspace as the current working colorspace
                current_working_colorspace = look_working_colorspace

            if current_working_colorspace != lut_in_colorspace:
                self._operators.append(
                    OCIO.ColorSpaceTransform(
                        src=current_working_colorspace,
                        dst=lut_in_colorspace,
                    )
                )

            self._operators.append(
                OCIO.FileTransform(
                    src=Path(filepath).as_posix(),
                    interpolation=operators.get_interpolation(interpolation),
                    direction=operators.get_direction(direction),
                )
            )

            current_working_colorspace = lut_out_colorspace

        # making sure we are back in the working colorspace
        if current_working_colorspace != look_working_colorspace:
            self._operators.append(
                OCIO.ColorSpaceTransform(
                    src=current_working_colorspace,
                    dst=look_working_colorspace,
                )
            )

    def get_oiiotool_cmd(self) -> List[str]:
        """Get arguments for the OIIO command."""
        args = []
        for op in self.color_operators:
            if isinstance(op, OCIO.FileTransform):
                lut = Path(op.getSrc()).resolve()
                args.extend(["--ociofiletransform", f"{lut.as_posix()}"])
            if isinstance(op, OCIO.ColorSpaceTransform):
                args.extend(["--colorconvert", op.getSrc(), op.getDst()])
        return args

    def _sanitize_file_path(
        self, repre_data: dict, all_relative_files: dict
    ) -> None:

        extension = repre_data["ext"]

        if repre_data.get("file"):
            return

        if self.target_path:
            # set file with extension
            repre_data["file"] = f"{self.target_path.stem}.{extension}"
        else:
            for file, path in all_relative_files.items():
                if file.endswith(extension):
                    repre_data["file"] = path.resolve().as_posix()
                    break

        if not repre_data.get("file"):
            log.warning(
                f"File not found: {repre_data['name']}.{repre_data['ext']}.")

        self.log.info(f"Added missing file path: {repre_data['file']}")
