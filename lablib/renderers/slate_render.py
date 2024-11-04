from __future__ import annotations

import subprocess
import shutil
from typing import List

from pathlib import Path

from ..lib.utils import call_iinfo, call_cmd, offset_timecode
from ..generators import SlateHtmlGenerator
from ..lib import SequenceInfo
from .basic import BasicRenderer
from .base import RendererBase


class SlateRenderer(RendererBase):
    """Class for rendering slates.

    .. admonition:: Example

        .. code-block:: python

            # render slate image to 1080p
            slate_generator = SlateHtmlGenerator(
                # data used to fill up the slate template
                {
                    "project": {"name": "test_project"},
                    "intent": {"value": "test_intent"},            
                    "task": {"short": "test_task"},
                    "asset": "test_asset",
                    "comment": "some random comment",
                    "scope": "test_scope",
                    "@version": "123",
                },
                "/templates/slates/slate_generic/slate_generic.html",
            )
            rend = SlateRenderer(
                slate_generator,
                SequenceInfo.scan("resources/public/plateMain/v002")[0],
            )
            rend.render(debug=True)
    """

    def __init__(
        self,
        slate_generator: SlateHtmlGenerator,
        source_sequence: SequenceInfo,
        destination: str = None  # default prepend to the source sequence
    ):
        self._slate_proc = slate_generator
        self._dest = None  # default destination
        self._forced_dest = destination  # explicit destination

        self._source_sequence = None
        self.source_sequence = source_sequence

        self._thumbs: List = None
        self._command: List = []

    @property
    def slate_generator(self) -> SlateHtmlGenerator:
        """
        Returns:
            SlateHtmlGenerator: The generator associated to the renderer.
        """
        return self._slate_proc

    @slate_generator.setter
    def slate_generator(self, generator: SlateHtmlGenerator) -> None:
        """
        Args:
            generator (SlateHtmlGenerator): The new generator for the renderer.
        """
        self._slate_proc = generator
        self._slate_proc.source_files = self._source_sequence.frames

    @property
    def source_sequence(self) -> SequenceInfo:
        """Return the source sequence.

        Returns:
            SequenceInfo. The source sequence.
        """
        return self._source_sequence

    @source_sequence.setter
    def source_sequence(self, source_sequence: SequenceInfo) -> None:
        """Set new source sequence.
        """
        self._source_sequence = source_sequence
        self._slate_proc.source_files = self._source_sequence.frames

        first_frame = self._source_sequence.frames[0]
        frame_number = first_frame.frame_number
        slate_frame = str(frame_number - 1).zfill(source_sequence.padding)
        ext = first_frame.extension
        head, _, __ =  first_frame.filepath.rsplit(".", 3)

        self._dest = f"{head}.{slate_frame}{ext}"

    @property
    def destination(self):
        """
        Returns:
            str: The renderer destination.
        """
        return self._forced_dest or self._dest

    def render(self, debug=False) -> None:
        """Render the slate sequence.

        Arguments:
            debug (Optional[bool]): Whether to increase log verbosity.
        """        
        first_frame = self.source_sequence.frames[0]
        timecode = offset_timecode(
            tc=first_frame.timecode,
            frame_offset=-1,
            fps=first_frame.fps,
        )
        self._slate_proc.create_base_slate()

        cmd = ["oiiotool"]
        cmd.extend(self._slate_proc.get_oiiotool_cmd())
        cmd.extend(
            [
                "--ch",
                "R,G,B",
                "--attrib:type=timecode",
                "smpte:TimeCode",
                f"""'{timecode.replace('"', "")}'""",
            ]
        )
        if debug:
            cmd.extend(["--debug", "-v"])

        cmd.extend(["-o", self.destination])
        call_cmd(cmd)

        slate_base_image_path = Path(self._slate_proc._slate_base_image_path).resolve()
        slate_base_image_path.unlink()
        shutil.rmtree(slate_base_image_path.parent)
