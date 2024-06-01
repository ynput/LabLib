from __future__ import annotations
from dataclasses import dataclass, field

import logging
import subprocess
import shutil
import tempfile
from typing import List

from pathlib import Path

from ..processors import (
    OCIOConfigFileProcessor,
    OIIORepositionProcessor,
)
from ..lib import SequenceInfo

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


SUPPORTED_CODECS = ["ProRes422-HQ", "ProRes4444-XQ", "DNxHR-SQ"]


@dataclass
class Codec:
    name: str = field(default_factory=str, init=True, repr=True)

    def __post_init__(self) -> None:
        if self.name not in SUPPORTED_CODECS:
            raise ValueError(
                f"{self.name} is not found in supported codecs.\n{SUPPORTED_CODECS = }"
            )

    def get_ffmpeg_args(self) -> List[str]:
        args = []
        # fmt: off
        # TODO: i should probably abstract the cmdargs
        if self.name == "ProRes422-HQ":
            args = [
                "-vcodec", "prores_ks",
                "-profile:v", "3",
                "-vendor", "apl0",
                "-pix_fmt", "yuv422p10le",
                "-vtag", "apch",
            ]
        if self.name == "ProRes4444-XQ":
            args = [
                "-vcodec", "prores_ks",
                "-profile:v", "4",
                "-vendor", "apl0",
                "-pix_fmt", "yuva444p10le",
                "-vtag", "ap4h",
                "-vtag", "hvc1",
            ]
        if self.name == "DNxHR-SQ":
            args = [
                "-vcodec", "dnxhd",
                "-profile:v", "2",
                "-pix_fmt", "yuv422p",
            ]
        # fmt: on

        return args


@dataclass
class BasicRenderer:
    # processors
    repo_proc: OIIORepositionProcessor = field(default=None, repr=False)
    color_proc: OCIOConfigFileProcessor = field(default=None, repr=False)

    # files and directories
    output_dir: str = field(default_factory=str)
    source_sequence: SequenceInfo = field(default=None)
    container_name: str = field(default="lablib.mov")

    # rendering options
    fps: int = field(init=False, repr=False)
    codec: str = field(default_factory=str)
    audio: str = field(init=False, repr=False)
    threads: int = field(default=4, repr=False)


    def __post_init__(self) -> None:
        if not self.source_sequence:
            raise ValueError("Missing source sequence!")
        if not any([self.color_proc, self.repo_proc]):
            raise ValueError("Missing valid Processor!")
        if not self.output_dir:
            log.warning("Rendering to $HOME/lablib_render")
            self._output_dir = (Path.home() / "lablib_render").resolve()
            if not self.output_dir.exists():
                self.output_dir.mkdir()

        self._output_dir = Path(self.output_dir).resolve()
        if not self._output_dir.is_dir():
            self._output_dir.mkdir()
            log.info(f"Output directory {self._output_dir} created!")

        self._staging_dir = Path(tempfile.mkdtemp())

    def get_oiiotool_cmd(self, debug=False) -> List[str]:
        # TODO: we should add OIIOTOOL required version into pyproject.toml
        #       since we are using treaded version of OIIOTOOL
        # ? does the python module install the binaries and adds them to PATH
        # maybe define LABLIB_* env vars for the paths and use them in the commands
        cmd = [  # inits the command with defaults
            "oiiotool",
            "-i",
            Path(self.source_sequence.path, self.source_sequence.hash_string)
            .resolve()
            .as_posix(),
            "--threads",
            str(self.threads),
        ]

        cmd.extend(["--ch", "R,G,B"])
        if debug:
            cmd.extend(["--debug", "-v"])

        # add processor args
        if self.repo_proc:
            cmd.extend(self.repo_proc.get_oiiotool_cmd())
        if self.color_proc:
            self.color_proc.create_config()
            cmd.extend(self.color_proc.get_oiiotool_cmd())

        dest_path = self.source_sequence.hash_string
        cmd.extend(["-o", (self._staging_dir / dest_path).as_posix()])

        return cmd

    def get_ffmpeg_cmd(self) -> List[str]:
        cmd = ["ffmpeg", "-loglevel", "info", "-hide_banner"]

        # common args
        common_args = [
            "-y",
            "-xerror",
            "-start_number",
            str(self.source_sequence.start_frame),
            "-r",
            str(min(self.source_sequence.frames).fps),
            "-thread_queue_size",
            "4096",
            "-framerate",
            str(min(self.source_sequence.frames).fps),
        ]
        cmd.extend(common_args)

        # input args
        input_path: str = (
            Path(self.source_sequence.path, self.source_sequence.format_string)
            .resolve()
            .as_posix()
        )
        input_args = ["-i", input_path]
        timecode = min(self.source_sequence.frames).timecode
        input_args.extend(["-timecode", timecode])
        cmd.extend(input_args)

        # codec args
        if self.codec:
            codec_args = Codec(name=self.codec).get_ffmpeg_args()
            cmd.extend(codec_args)

        # output args
        # NOTE: ffmpegs output arg needs to be the last one
        output_path = Path(self._staging_dir, self.container_name)
        output_args = [output_path.as_posix()]
        cmd.extend(output_args)

        return cmd

    def render(self, debug=False) -> SequenceInfo:
        cmd = self.get_oiiotool_cmd(debug)
        ffmpeg_cmd = self.get_ffmpeg_cmd()

        # run oiiotool command
        log.info("oiiotool cmd >>> {}".format(" ".join(cmd)))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log.error(result.stderr)
        if debug:
            log.info(result.stdout)

        # get rendered sequence info
        result = SequenceInfo.scan(Path(self._staging_dir))[0]
        log.info(f"Rendered sequence info >>> {result}")

        # run ffmpeg command
        log.info("ffmpeg cmd >>> {}".format(" ".join(ffmpeg_cmd)))
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        # NOTE: ffmpeg outputs to stderr
        stderr = result.stderr.encode("utf-8").decode()
        if result.returncode != 0:
            log.error(stderr)
        if debug:
            log.info(stderr)

        # copy renders to output directory
        for item in self._staging_dir.iterdir():
            if item.is_file():
                log.debug(f"Copying {item} to {self._output_dir}")
                shutil.copy2(item, self._output_dir)

        # cleanup
        shutil.rmtree(self._staging_dir)

        return result
