from __future__ import annotations
from dataclasses import dataclass, field

import logging
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Set, Union

from pathlib import Path

from ..lib import SequenceInfo, utils

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


SUPPORTED_CODECS = ["ProRes422-HQ", "ProRes4444-XQ", "DNxHR-SQ"]


@dataclass
class Codec:
    """Utility class for abstracting ffmpeg codec arguments.

    Currently this only supports 2 flavors of ProRes and 1 of DNxHR but could deserve more.
    Supported codecs are: ``ProRes422-HQ``, ``ProRes4444-XQ``, ``DNxHR-SQ``

    Attributes:
        name (str): The name of the codec.
    """

    name: str = field(default_factory=str, init=True, repr=True)

    def __post_init__(self) -> None:
        if self.name not in SUPPORTED_CODECS:
            raise ValueError(
                f"{self.name} is not found in supported codecs.\n{SUPPORTED_CODECS = }"
            )

    def get_ffmpeg_args(self) -> List[str]:
        """Get the ffmpeg arguments for the codec.

        Returns:
            List[str]: The ffmpeg arguments
        """
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
class Burnin:
    """Utility class for handling burnins with OIIO.

    The data attribute is a structure dict containing the text to be drawn and its positioning.
    An example for an entry showing all positioning options would be:
    ::
        {
            "text": "YOUR_TEXT_HERE",
            "position": [
                "top_left"
                "top_center"
                "top_right"
                "bottom_left"
                "bottom_center"
                "bottom_right"
            ],
        },

    Attributes:
        data (Dict[str, str]): The text to be drawn and its positioning.
        size (int): The size of the text.
        padding (int): The padding around the text.
        color (Set[float]): The color of the text.
        font (Optional[str]): The font to use.
        outline (Optional[int]): The outline size.
    """

    data: Dict[str, str] = field(default_factory=dict)

    size: int = field(default=64)
    padding: int = field(default=30)
    color: Set[float] = field(default=(1, 1, 1))

    font: Optional[str] = field(default=None)
    outline: Optional[int] = field(default=None)

    def __post_init__(self) -> None:
        if not self.data:
            raise ValueError("Burnin data is empty")

        if self.font:
            self._font = Path(self.font).resolve()

    def get_oiiotool_args(self) -> List[str]:
        """Get the OIIO arguments.

        Returns:
            List[str]: The OIIO arguments.
        """
        args = []
        width_token = r"{TOP.width}"
        height_token = r"{TOP.height}"
        _color = ",".join([str(c) for c in self.color])
        for burnin in self.data:
            flag = f"--text:size={self.size}:color={_color}"
            if self.outline:
                _relative_size = int(self.size * 0.05 * self.outline)
                flag += f":shadow={_relative_size}"
            if self.font:
                flag += f':font="{self._font.as_posix()}"'

            if burnin.get("position"):
                if burnin["position"] == "top_left":
                    x = 0
                    y = 0
                    flag += f":x={x}:y={y}:xalign=left:yalign=top"
                if burnin["position"] == "top_center":
                    x = f"{width_token}/2"
                    y = 0
                    flag += f":x={x}:y={y}:xalign=center:yalign=top"
                if burnin["position"] == "top_right":
                    x = width_token
                    y = 0
                    flag += f":x={x}:y={y}:xalign=right:yalign=top"
                if burnin["position"] == "bottom_left":
                    x = 0
                    y = height_token
                    flag += f":x={x}:y={y}:xalign=left"
                if burnin["position"] == "bottom_center":
                    x = f"{width_token}/2"
                    y = height_token
                    flag += f":x={x}:y={y}:xalign=center"
                if burnin["position"] == "bottom_right":
                    x = width_token
                    y = height_token
                    flag += f":x={x}:y={y}:xalign=right"

            args.extend([flag, burnin["text"]])

        return args


class BasicRenderer:
    name: str = "lablib.mov"

    # rendering options
    threads: int = 4

    # cleanup
    keep_only_container: bool = False

    def __init__(
        self,
        source_sequence: SequenceInfo,
        output_dir: Union[Path, str],
        **kwargs,
    ) -> None:
        self.source_sequence = source_sequence
        self.output_dir = Path(output_dir).resolve()

        for k, v in kwargs.items():
            if not hasattr(self.__class__, k):
                raise ValueError(f"Unknown attribute {k}")
            setattr(self, k, v)

        if not kwargs.get("staging_dir"):
            self._staging_dir = Path(tempfile.mkdtemp())

    def __repr__(self) -> str:
        exposed_props = ["source_sequence", "output_dir"]
        props = ""
        for prop in exposed_props:
            props = props + f"{prop}={getattr(self, prop)}, "

        optional_props = ["codec", "audio", "processor"]
        for prop in optional_props:
            if hasattr(self, prop):
                props = props + f"{prop}={getattr(self, prop)}, "

        return f"{self.__class__.__name__}({props[:-2]})"

    def get_oiiotool_cmd(self, debug=False) -> List[str]:
        input_path = Path(
            self.source_sequence.path, self.source_sequence.hash_string
        ).resolve()
        cmd = [  # inits the command with defaults
            "oiiotool.exe",
            "-i",
            input_path.as_posix(),
            "--threads",
            str(self.threads),
        ]

        cmd.extend(["--ch", "R,G,B"])
        if debug:
            cmd.extend(["--debug", "-v"])

        # add processor args
        if self.processor:
            cmd.extend(self.processor.get_oiiotool_cmd())

        if self.burnins:
            log.debug(f"{self.burnins = }")
            cmd.extend(self.burnins.get_oiiotool_args())

        output_path = (self._staging_dir / self.source_sequence.hash_string).resolve()
        self._oiio_out = output_path  # for ffmpeg input
        cmd.extend(["-o", output_path.as_posix()])

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
            str(self.fps),
            "-thread_queue_size",
            "4096",
            "-framerate",
            str(self.fps),
        ]
        cmd.extend(common_args)

        # input args
        input_path = Path(
            self.source_sequence.path, self.source_sequence.format_string
        ).resolve()
        if hasattr(self, "_oiio_out"):
            si = SequenceInfo.scan(self._oiio_out.parent)[0]
            input_path = Path(si.path, si.format_string).resolve()
        input_args = ["-i", input_path.as_posix()]
        if self.audio:
            audio_path: str = Path(self.audio).resolve().as_posix()
            input_args.extend(["-i", audio_path])
            audio_args = ["-map", "0:v", "-map", "1:a"]
            input_args.extend(audio_args)
        cmd.extend(input_args)

        # timecode args
        timecode = min(self.source_sequence.frames).timecode
        cmd.extend(["-timecode", timecode])

        # codec args
        if self.codec:
            codec_args = Codec(name=self.codec).get_ffmpeg_args()
            cmd.extend(codec_args)

        # output args
        # NOTE: ffmpegs output arg needs to be the last one
        output_path = Path(self._staging_dir, self.name)
        output_args = [output_path.as_posix()]
        cmd.extend(output_args)

        return cmd

    def render(self, debug=False) -> None:
        # run oiiotool command
        cmd = self.get_oiiotool_cmd(debug)
        log.info("oiiotool cmd >>> {}".format(" ".join(cmd)))
        oiio_out, oiio_err = utils.call_cmd(cmd)
        if debug:
            for line in oiio_out.splitlines():
                log.info(f"oiio out: {line}")
            for line in oiio_err.splitlines():
                log.info(f"oiio err: {line}")

        # run ffmpeg command
        if self.codec:
            ffmpeg_cmd = self.get_ffmpeg_cmd()
            log.info("ffmpeg cmd >>> {}".format(" ".join(ffmpeg_cmd)))
            # NOTE: ffmpeg only outputs to stderr
            _, ffmpeg_err = utils.call_cmd(ffmpeg_cmd)

            if debug:
                for line in ffmpeg_err.splitlines():
                    log.info(f"ffmpeg out: {line}")

        # copy renders to output directory
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)
        for item in self._staging_dir.iterdir():
            if item.is_file():
                if item.suffix in [".exr"] and self.keep_only_container:
                    continue
                if item.suffix not in [".mov", ".mp4", ".exr"]:
                    continue
                log.info(f"Copying {item} to {self.output_dir}")
                shutil.copy2(item, self.output_dir)

        # cleanup
        shutil.rmtree(self._staging_dir)

    @property
    def processor(self) -> Any:
        if not hasattr(self, "_processor"):
            return None
        return self._processor

    @processor.setter
    def processor(self, value: Any) -> None:
        self._processor = value

    @property
    def codec(self) -> str:
        if not hasattr(self, "_codec"):
            return None
        return self._codec.name

    @codec.setter
    def codec(self, value: str) -> None:
        self._codec = Codec(name=value)

    @property
    def fps(self) -> int:
        if not hasattr(self, "_fps"):
            return min(self.source_sequence.frames).fps
        return self._fps

    @fps.setter
    def fps(self, value: int) -> None:
        self._fps = value

    @property
    def audio(self) -> str:
        if not hasattr(self, "_audio"):
            return None
        return self._audio.as_posix()

    @audio.setter
    def audio(self, value: str) -> None:
        self._audio = Path(value).resolve()

    @property
    def burnins(self) -> Burnin:
        if not hasattr(self, "_burnins"):
            return None
        return self._burnins

    @burnins.setter
    def burnins(self, values: dict) -> None:
        self._burnins = Burnin(**values)
