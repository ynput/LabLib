from __future__ import annotations
from dataclasses import dataclass

import subprocess
import shutil
from typing import List

from pathlib import Path

from ..processors import (
    OCIOConfigFileProcessor,
    OIIORepositionProcessor,
)
from ..operators import SequenceInfo


@dataclass
class BasicRenderer:
    color_proc: OCIOConfigFileProcessor = None
    repo_proc: OIIORepositionProcessor = None
    source_sequence: SequenceInfo = None
    staging_dir: str = None
    name: str = None
    format: str = None

    def __post_init__(self) -> None:
        self._debug: bool = False
        self._threads: int = 4
        self._command: List[str] = []
        if not self.name:
            self.name = "lablib_render"

    def setup_staging_dir(self) -> None:
        render_staging_dir = Path(self.staging_dir, self.name)
        if not render_staging_dir.resolve().is_dir():
            shutil.rmtree(render_staging_dir.as_posix(), ignore_errors=True)
            render_staging_dir.mkdir(parents=True, exist_ok=True)

    def set_color_processor(self, processor: OCIOConfigFileProcessor) -> None:
        self.color_proc = processor

    def set_repo_processor(self, processor: OIIORepositionProcessor) -> None:
        self.repo_proc = processor

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def set_source_sequence(self, sequence: SequenceInfo) -> None:
        self.source_sequence = sequence

    def set_staging_dir(self, dir: str) -> None:
        self.staging_dir = dir

    def set_threads(self, threads: int) -> None:
        self._threads = threads

    def get_oiiotool_cmd(self) -> List[str]:
        return self._command

    def render(self) -> SequenceInfo:
        if not self.color_proc and not self.repo_proc:
            raise ValueError("Missing both valid Processors!")
        self.setup_staging_dir()
        # TODO: we should add OIIOTOOL required version into pyproject.toml
        #       since we are using treaded version of OIIOTOOL
        cmd = [
            "oiiotool",
            "-i",
            Path(self.source_sequence.path, self.source_sequence.hash_string)
            .resolve()
            .as_posix(),
            "--threads",
            str(self._threads),
        ]
        if self.repo_proc:
            cmd.extend(self.repo_proc.get_oiiotool_cmd())

        if self.color_proc:
            self.color_proc.create_config()
            cmd.extend(self.color_proc.get_oiiotool_cmd())

        cmd.extend(["--ch", "R,G,B"])
        if self._debug:
            cmd.extend(["--debug", "-v"])

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
        self._command = cmd
        if self._debug:
            print("oiiotool cmd >>> {}".format(" ".join(self._command)))
        subprocess.run(cmd)
        result = SequenceInfo()
        Path(self.color_proc._dest_path).resolve().unlink()
        return result.compute_longest(
            Path(self.staging_dir, self.name).resolve().as_posix()
        )

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
