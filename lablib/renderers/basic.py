from __future__ import annotations
from dataclasses import dataclass, field

import logging
import subprocess
import shutil
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
    name: str

    def get_ffmpeg_args(self) -> List[str]:
        if self.name not in SUPPORTED_CODECS:
            raise ValueError(f"Codec {self.name} not supported!")

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
    # NOTE: can't use default_factory currently since
    #       color_proc requires a Context
    repo_proc: OIIORepositionProcessor = field(default=None)
    color_proc: OCIOConfigFileProcessor = field(default=None)

    # files and directories
    # NOTE: name is used for the output ffolder name of file sequence
    name: str = field(default="lablib_render", init=False, repr=False)
    format: str = field(default_factory=str, init=True, repr=True)
    staging_dir: str = (
        None  # should be an internal only variable, shall i rename to output_dir?
    )
    source_sequence: SequenceInfo = None
    container_name: str = "lablib.mov"

    # rendering options
    # NOTE: currently only used for oiiotool
    threads: int = field(default=4, init=False, repr=False)
    codec: str = None
    audio: str = None
    fps: int = None

    def __post_init__(self) -> None:
        if not self.staging_dir:
            log.warning("No staging directory provided. Rendering to cwd")
            self.staging_dir = Path("lablib_render").resolve().as_posix()
        if not self.codec:
            log.warning("No codec provided.")

        self._codec = Codec(self.codec)

    def setup_staging_dir(self) -> None:
        render_staging_dir = Path(self.staging_dir, self.name)
        if not render_staging_dir.resolve().is_dir():
            shutil.rmtree(render_staging_dir.as_posix(), ignore_errors=True)
            render_staging_dir.mkdir(parents=True, exist_ok=True)

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

        # format the output path
        if self.format:
            dest_path = "{}{}{}".format(
                self.source_sequence.head,
                "#",
                ".{}".format(self.format) if self.format.find(".") < 0 else self.format,
            )
        else:
            dest_path = self.source_sequence.hash_string

        cmd.extend(
            ["-o", Path(self.staging_dir, self.name, dest_path).resolve().as_posix()]
        )

        return cmd

    def get_ffmpeg_cmd(self) -> List[str]:
        if not self.codec:
            raise ValueError(f"Missing codec! Supported codecs are {SUPPORTED_CODECS}")

        # common args
        cmd = ["ffmpeg", "-loglevel", "info", "-hide_banner"]
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

        # input args
        input_path: str = (
            Path(self.source_sequence.path, self.source_sequence.ffmpeg_string)
            .resolve()
            .as_posix()
        )
        input_args = ["-i", input_path]

        # output and codec args
        output_path = Path(self.staging_dir, self.container_name)
        output_args = [output_path.as_posix()]
        codec_args = self._codec.get_ffmpeg_args()

        # chain all args
        # NOTE: ffmpegs output arg is the last one
        chain = [common_args, input_args, codec_args, output_args]
        for args in chain:
            cmd.extend(args)

        return cmd

    def render(self, debug=False) -> SequenceInfo:
        if not self.color_proc and not self.repo_proc:
            raise ValueError("Missing both valid Processors!")
        self.setup_staging_dir()
        cmd = self.get_oiiotool_cmd(debug)
        ffmpeg_cmd = self.get_ffmpeg_cmd()

        # run oiiotool command
        log.info("oiiotool cmd >>> {}".format(" ".join(cmd)))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log.error(result.stderr)
            raise ValueError("Failed to render sequence!")
        if debug:
            log.info(result.stdout)

        # get rendered sequence info
        result = SequenceInfo.scan(Path(self.staging_dir, self.name))[0]
        log.info(f"Rendered sequence info >>> {result}")

        return result
