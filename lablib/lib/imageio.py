from __future__ import annotations

import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List

import opentimelineio.opentime as opentime

from . import utils

IMAGE_INFO_DEFAULTS = {
    "width": 1920,
    "height": 1080,
    "channels": 3,
    "fps": 24.0,
    "par": 1.0,
    "timecode": "00:00:00:00",
    "origin_x": 0,
    "origin_y": 0,
    "display_width": 1920,
    "display_height": 1080,
}

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@dataclass
class ImageInfo:
    """ImageInfo class for reading image metadata."""

    path: Path = field(default_factory=Path)

    # fmt: off
    width: int = field(default=IMAGE_INFO_DEFAULTS["width"], init=False, repr=True)
    height: int = field(default=IMAGE_INFO_DEFAULTS["height"], init=False, repr=True)
    origin_x: int = field(default=IMAGE_INFO_DEFAULTS["origin_x"], init=False, repr=False)
    origin_y: int = field(default=IMAGE_INFO_DEFAULTS["origin_y"], init=False, repr=False)
    display_width: int = field(default=IMAGE_INFO_DEFAULTS["display_width"], init=False, repr=False)
    display_height: int = field(default=IMAGE_INFO_DEFAULTS["display_height"], init=False, repr=False)
    par: float = field(default=IMAGE_INFO_DEFAULTS["par"], init=False, repr=False)
    channels: int = field(default=IMAGE_INFO_DEFAULTS["channels"], init=False, repr=True)

    fps: float = field(default=IMAGE_INFO_DEFAULTS["fps"], init=False, repr=False)
    timecode: str = field(default=IMAGE_INFO_DEFAULTS["timecode"], init=False, repr=False)
    # fmt: on

    def __post_init__(self):
        if not self.path:
            raise ValueError("ImageInfo needs to be initialized with a path")
        self.update()

    def __gt__(self, other: ImageInfo) -> bool:
        return self.frame_number > other.frame_number

    def __lt__(self, other: ImageInfo) -> bool:
        return self.frame_number < other.frame_number

    def update(self, force_ffprobe=False):
        """Update image info from iinfo and ffprobe values.
        NOTE: force_ffprobe overrides iinfo values with ffprobe values.
              It's used since they report different framerates for testing exr
              files.
        """
        iinfo_res = utils.call_iinfo(self.path)
        ffprobe_res = utils.call_ffprobe(self.path)

        for k, v in iinfo_res.items():
            if not v:
                continue
            if ffprobe_res.get(k) and force_ffprobe:
                v = ffprobe_res[k]
            setattr(self, k, v)

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def rational_time(self) -> opentime.RationalTime:
        if not all([self.timecode, self.fps]):
            # NOTE: i should use otio here
            raise Exception("no timecode and fps found")

        return opentime.from_timecode(self.timecode, self.fps)

    @property
    def frame_number(self) -> int:
        if not self.filename:
            raise Exception("needs filename for querying frame number")
        matches = re.findall(r"\.(\d+)\.", self.filename)
        if len(matches) > 1:
            raise ValueError("can't handle multiple found frame numbers")

        result = int(matches[0])

        return result

    @property
    def extension(self) -> str:
        return self.path.suffix

    @property
    def name(self) -> str:
        return f"{self.path.stem}{self.path.suffix}"


class SequenceInfo(ImageIOBase):
    def __init__(self, path: Path, imageinfos: List[ImageInfo]):
        super().__init__(path=path, imageinfos=imageinfos)

    @classmethod
    def scan(cls, directory: str | Path) -> List[SequenceInfo]:
        cls.log.info(f"Scanning {directory}")
        if not isinstance(directory, Path):
            directory = Path(directory)

        if not directory.is_dir():
            raise NotImplementedError(f"{directory} is no directory")

        files_map: Dict[Path, ImageInfo] = {}
        for item in directory.iterdir():
            if not item.is_file():
                continue
            if item.suffix not in (".exr"):
                cls.log.warning(f"{item.suffix} not in (.exr)")
                continue

            _parts = item.stem.split(".")
            if len(_parts) > 2:
                cls.log.warning(f"{_parts = }")
                continue
            seq_key = Path(item.parent, _parts[0])

            if seq_key not in files_map.keys():
                files_map[seq_key] = []
            files_map[seq_key].append(ImageInfo(item))

        return [
            cls(path=seq_key.parent, imageinfos=seq_files)
            for seq_key, seq_files in files_map.items()
        ]

    def update(self, **kwargs):
        if kwargs.get("path"):
            self.path = kwargs["path"]
        if kwargs.get("imageinfos"):
            self.imageinfos = kwargs["imageinfos"]

    @property
    def imageinfos(self) -> List[int]:
        return self._imageinfos

    @imageinfos.setter
    def imageinfos(self, value: List[ImageInfo]):
        self._imageinfos = value

    @property
    def frames(self) -> List[int]:
        return self.imageinfos

    @property
    def start_frame(self) -> int:
        return min(self.frames).frame_number

    @property
    def end_frame(self) -> int:
        return max(self.frames).frame_number

    @property
    def hash_string(self) -> str:
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]

        result = f"{basename}.{self.start_frame}-{self.end_frame}#{ext}"
        return result

    @property
    def padding(self) -> int:
        frame = min(self.frames)
        result = len(str(frame.frame_number))
        return result

    @property
    def frames_missing(self) -> bool:
        start = min(self.frames).frame_number
        end = max(self.frames).frame_number
        expected: int = len(range(start, end)) + 1
        return not expected == len(self.frames)

    @property
    def width(self) -> int:
        return self.imageinfos[0].width

    @property
    def display_width(self) -> int:
        return self.imageinfos[0].display_width

    @property
    def height(self) -> int:
        return self.imageinfos[0].height

    @property
    def display_height(self) -> int:
        return self.imageinfos[0].display_height
