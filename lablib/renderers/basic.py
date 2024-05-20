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


@dataclass
class BasicRenderer:
    # processors
    repo_proc: OIIORepositionProcessor = None
    color_proc: OCIOConfigFileProcessor = None

    # files and directories
    name: str = "lablib_render"
    format: str = None
    staging_dir: str = None
    source_sequence: SequenceInfo = None

    # rendering options
    # NOTE: currently only used for oiiotool
    threads: int = field(default=4, init=False, repr=False)

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
            str(self._threads),
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

    def render(self, debug=False) -> SequenceInfo:
        if not self.color_proc and not self.repo_proc:
            raise ValueError("Missing both valid Processors!")
        self.setup_staging_dir()
        cmd = self.get_oiiotool_cmd(debug)

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

    def render_repo_ffmpeg(
        self,
        src: str,
        dst: str,
        cornerpin: List,
        in_args: List = None,
        out_args: List = None,
        resolution: str = None,
        debug: str = "error",
    ) -> SequenceInfo:
        if not resolution:
            resolution = "1920x1080"
        width, height = resolution.split("x")
        cmd = ["ffmpeg"]
        cmd.extend(["-y", "-loglevel", debug, "-hide_banner"])
        if in_args:
            cmd.extend(in_args)
        cmd.extend(["-i", src])
        # QUESTION: shouldn't we add cornerpin optionally?
        cmd.extend(
            [
                "-vf",
                ",".join(
                    [
                        "perspective={}:{}:{}:{}:{}:{}:{}:{}:{}".format(
                            cornerpin[0],
                            cornerpin[1],
                            cornerpin[2],
                            cornerpin[3],
                            cornerpin[4],
                            cornerpin[5],
                            cornerpin[6],
                            cornerpin[7],
                            "sense=destination:eval=init",
                        ),
                        f"scale={width}:-1",
                        f"crop={width}:{height}",
                    ]
                ),
            ]
        )
        if out_args:
            cmd.extend(out_args)
        cmd.append(dst)
        subprocess.run(cmd)
        result = SequenceInfo()
        return result.compute_longest(Path(dst).resolve().parent.as_posix())
