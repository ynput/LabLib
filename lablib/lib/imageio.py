from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

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


class ImageIOBase:
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.update(*args, **kwargs)

    def __getitem__(self, k: str) -> Any:
        return getattr(self, k)

    def __setitem__(self, k: str, v: Any) -> None:
        if hasattr(self, k):
            setattr(self, k, v)
        else:
            raise AttributeError(f"Attribute is not implemented: {k}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{self.__dict__}"

    def update(self, **kwargs) -> None:
        """Update operator attributes by calling implemented setter of keyword argument key."""
        self.log.warning(f"Update not implemented for {self.__class__.__name__}")
        pass

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, path: Union[str, Path]) -> None:
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            raise Exception(f"Path does not exist: {path}")

        self._path = path

    @property
    def filepath(self) -> Path:
        return self.path


class ImageInfo(ImageIOBase):
    """ImageInfo class for reading image metadata."""

    def __init__(self, path: Path):
        super().__init__(path=path)

    def __gt__(self, other: ImageInfo) -> bool:
        return self.frame_number > other.frame_number

    def __lt__(self, other: ImageInfo) -> bool:
        return self.frame_number < other.frame_number

    def update(self, force_ffprobe=True, **kwargs):
        """Update ImageInfo from a given file path.
        NOTE: force_ffprobe overrides iinfo values with ffprobe values.
              It's used since they report different framerates for testing exr
              files.
        """
        if kwargs.get("path"):
            self.path = kwargs["path"]

        iinfo_res = utils.call_iinfo(self.path)
        ffprobe_res = utils.call_ffprobe(self.path)

        for k, v in iinfo_res.items():
            if not v:
                continue
            if ffprobe_res.get(k) and force_ffprobe:
                v = ffprobe_res[k]
            self[k] = v

    @property
    def width(self) -> int:
        if not hasattr(self, "_width"):
            return IMAGE_INFO_DEFAULTS["width"]
        return self._width

    @width.setter
    def width(self, value: int):
        self._width = value

    @property
    def height(self) -> int:
        if not hasattr(self, "_height"):
            return IMAGE_INFO_DEFAULTS["height"]
        return self._height

    @height.setter
    def height(self, value: int):
        self._height = value

    @property
    def display_height(self) -> int:
        if not hasattr(self, "_display_height"):
            return self.height  # default to initial height
        return self._display_height

    @display_height.setter
    def display_height(self, value: int):
        self._display_height = value

    @property
    def display_width(self) -> int:
        if not hasattr(self, "_display_width"):
            return self.width  # default to initial width
        return self._display_width

    @display_width.setter
    def display_width(self, value: int):
        self._display_width = value

    @property
    def channels(self) -> int:
        if not hasattr(self, "_channels"):
            return IMAGE_INFO_DEFAULTS["channels"]
        return self._channels

    @channels.setter
    def channels(self, value: int):
        self._channels = value

    @property
    def fps(self) -> int:
        if not hasattr(self, "_fps"):
            return IMAGE_INFO_DEFAULTS["fps"]
        return self._fps

    @fps.setter
    def fps(self, value: int):
        self._fps = value

    @property
    def par(self) -> int:
        if not hasattr(self, "_par"):
            return IMAGE_INFO_DEFAULTS["par"]
        return self._par

    @par.setter
    def par(self, value: int):
        self._par = value

    @property
    def timecode(self) -> str:
        if not hasattr(self, "_timecode"):
            return IMAGE_INFO_DEFAULTS["timecode"]
        return self._timecode

    @timecode.setter
    def timecode(self, value: int):
        self._timecode = value

    @property
    def origin_x(self) -> int:
        if not hasattr(self, "_origin_x"):
            return IMAGE_INFO_DEFAULTS["origin_x"]
        return self._origin_x

    @origin_x.setter
    def origin_x(self, value: int):
        self._origin_x = value

    @property
    def origin_y(self) -> int:
        if not hasattr(self, "_origin_y"):
            return IMAGE_INFO_DEFAULTS["origin_y"]
        return self._origin_y

    @origin_y.setter
    def origin_y(self, value: int):
        self._origin_y = value

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def rational_time(self) -> opentime.RationalTime:
        if not all([self.timecode, self.fps]):
            # NOTE: i should use otio here
            raise Exception("no timecode and fps found")

        result = opentime.from_timecode(self.timecode, self.fps)
        return result

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
