from __future__ import annotations
from dataclasses import dataclass

import subprocess
import shutil
from typing import List

from pathlib import Path

from ..lib.utils import call_iinfo, offset_timecode
from ..processors import SlateHtmlProcessor
from ..lib import SequenceInfo


@dataclass
class SlateRenderer:
    slate_proc: SlateHtmlProcessor = None
    source_sequence: SequenceInfo = None
    dest: str = None

    def __post_init__(self) -> None:
        self._thumbs: List = None
        self._debug: bool = False
        self._command: List = []
        if self.source_sequence:
            self.set_source_sequence(self.source_sequence)
            self.slate_proc.source_files = self.source_sequence.frames
        if self.dest:
            self.set_destination(self.dest)

    def set_slate_processor(self, processor: SlateHtmlProcessor) -> None:
        self.slate_proc = processor

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def set_source_sequence(self, source_sequence: SequenceInfo) -> None:
        self.source_sequence = source_sequence
        head, frame, tail = source_sequence._get_file_splits(
            source_sequence.frames[0])
        self.dest = f"{head}{str(int(frame) - 1).zfill(source_sequence.padding)}{tail}"  # noqa

    def set_destination(self, dest: str) -> None:
        self.dest = dest

    def render(self) -> None:
        iinfo_metadata = call_iinfo(self.source_sequence.frames[0])
        timecode = offset_timecode(
            tc=iinfo_metadata["timecode"],
            frame_offset=-1,
            fps=iinfo_metadata["fps"],
        )
        self.slate_proc.create_base_slate()
        if not self.slate_proc:
            raise ValueError("Missing valid SlateHtmlProcessor!")
        cmd = ["oiiotool"]
        cmd.extend(self.slate_proc.get_oiiotool_cmd())
        cmd.extend(
            [
                "--ch",
                "R,G,B",
                "--attrib:type=timecode",
                "smpte:TimeCode",
                f"""'{timecode.replace('"', "")}'""",
            ]
        )
        if self._debug:
            cmd.extend(["--debug", "-v"])
        cmd.extend(["-o", self.dest])
        self._command = cmd
        subprocess.run(cmd)
        slate_base_image_path = Path(self.slate_proc._slate_base_image_path).resolve()
        slate_base_image_path.unlink()
        shutil.rmtree(slate_base_image_path.parent)
