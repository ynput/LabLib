"""Module providing classes for handling image metadata and sequences."""

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
    """A dataclass for reading image metadata.

    All kwargs are optional and will be set from its ``update`` function or the defaults if they couldn't be found.

    .. admonition:: Example with Defaults

        .. code-block:: python

            image = ImageInfo(
                path=Path("path/to/image.exr"),
                width = 1920
                height = 1080
                channels = 3
                fps = 24.0
                par = 1.0
                timecode = "00:00:00:00"
                origin_x = 0
                origin_y = 0
                display_width = 1920
                display_height = 1080
            )

    Attributes:
        path(Path): Path to the image file.
        width(Optional[int]): Image width.
        height(Optional[int]): Image height.
        origin_x(Optional[int]): Origin x position.
        origin_y(Optional[int]): Origin y position.
        display_width(Optional[int]): Display width.
        display_height(Optional[int]): Display height.
        par(Optional[float]): Pixel aspect ratio.
        channels(Optional[int]): Number of channels.
        fps(Optional[float]): Frames per second.
        timecode(Optional[str]): Timecode.
    """

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
        """Post init function for ImageInfo class.
        Checks if path is set and calls update.

        Raises:
            ValueError if path is not set.
        """
        if not self.path:
            raise ValueError("ImageInfo needs to be initialized with a path")
        self.update()

    def __gt__(self, other: ImageInfo) -> bool:
        return self.frame_number > other.frame_number

    def __lt__(self, other: ImageInfo) -> bool:
        return self.frame_number < other.frame_number

    def update(self, force_ffprobe=False):
        """Updates metadata by calling iinfo and ffprobe.

        Kwargs:
            force_ffprobe bool: If True, ffprobe values will override iinfo values if they're found.
                                It's used since ffprobe reported different framerates for exrs during testing.
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
        """Property for the image file name including extension.

        :returns: str
        """
        return self.path.name

    @property
    def rational_time(self) -> opentime.RationalTime:
        """Property for OTIO rational time from timecode string field.

        :raises: Exception if no timecode and fps found.
        :returns: opentime.RationalTime
        """
        if not all([self.timecode, self.fps]):
            raise Exception("no timecode and fps found")

        return opentime.from_timecode(self.timecode, self.fps)

    @property
    def frame_number(self) -> int:
        """Property for frame number from the filename by using regex lookup.

        Note:
            The regex could use a little love to be more robust.
            Filename should be something like `filename.0001.exr`.

        :raises: Exception if regex lookup wasn't successful.
        :returns: int
        """
        if not self.filename:
            raise Exception("needs filename for querying frame number")
        matches = re.findall(r"\.(\d+)\.", self.filename)
        if len(matches) > 1:
            raise ValueError("can't handle multiple found frame numbers")

        result = int(matches[0])

        return result

    @property
    def extension(self) -> str:
        """Property for the file extension.

        :returns: str
        """
        return self.path.suffix

    @property
    def name(self) -> str:
        """Property for the file name with extension.

        TODO:
            I use this in SequenceInfo but could become obsolete in favor for `filename`.
            Should this be rewritten?

        :returns: str
        """
        return f"{self.path.stem}{self.path.suffix}"

    @property
    def filepath(self) -> str:
        """Property for the file path as posix string.

        Can be used if a string is needed.

        :returns: str
        """

        return self.path.resolve().as_posix()


@dataclass
class SequenceInfo:
    """Class for handling image sequences by using instances of `ImageInfo`.

    Hint:
        If you want to scan a directory for image sequences, you can use the ``scan`` classmethod.

    Attributes:
        path Any[Path, str]: Path to the image sequence directory.
        imageinfos List[ImageInfo]: List of all files as `ImageInfo` to be used.
    """

    path: Path = field(default_factory=Path)
    imageinfos: List[ImageInfo] = field(default_factory=list)

    def __post_init__(self):
        if not all([self.path, self.imageinfos]):
            raise ValueError(
                "SequenceInfo needs to be initialized with path and imageinfos"
            )

    @classmethod
    def scan(cls, directory: str | Path) -> List[SequenceInfo]:
        """Classmethod for scanning a directory for image sequences.

        Attention:
            Currently only supports EXR files. Needs to be extended and tested for other formats.

        Args:
            directory (Any[str, Path]): Path to the directory to be scanned.

        Returns:
            List[SequenceInfo]: List of all found image sequences
                as `SequenceInfo`.
        """
        log.info(f"Scanning {directory}")
        if not isinstance(directory, Path):
            directory = Path(directory)

        if not directory.is_dir():
            raise NotImplementedError(f"{directory} is no directory")

        files_map: Dict[Path, ImageInfo] = {}
        for item in directory.iterdir():
            if not item.is_file():
                continue
            if item.suffix not in (".exr"):
                log.warning(f"{item.suffix} not in (.exr)")
                continue

            _parts = item.stem.split(".")
            if len(_parts) > 2:
                log.warning(f"{_parts = }")
                continue
            seq_key = Path(item.parent, _parts[0])

            if seq_key not in files_map.keys():
                files_map[seq_key] = []
            files_map[seq_key].append(ImageInfo(item))

        return [
            cls(path=seq_key.parent, imageinfos=seq_files)
            for seq_key, seq_files in files_map.items()
        ]

    @property
    def frames(self) -> List[int]:
        """Property for getting a list of all frame numbers in the sequence.

        Returns:
            List[int]: List of all frame numbers in the sequence.
        """
        return self.imageinfos

    @property
    def start_frame(self) -> int:
        """Property for the lowest frame number in the sequence.

        Returns:
            int: The lowest frame number in the sequence.
        """
        return min(self.frames).frame_number

    @property
    def end_frame(self) -> int:
        """Property for the highest frame number in the sequence.

        :returns: int
        """
        return max(self.frames).frame_number

    @property
    def format_string(self) -> str:
        """Property for ffmpeg formatted string.

        :returns: str
        """
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]

        result = f"{basename}.%0{self.padding}d{ext}"
        return result

    @property
    def hash_string(self) -> str:
        """Property for oiio formatted string.

        :returns: str
        """
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]

        result = f"{basename}.{self.start_frame}-{self.end_frame}#{ext}"
        return result

    @property
    def format_string(self) -> str:
        """TODO: That's a duplicate so let's run tests and remove it."""
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]

        result = f"{basename}.%0{self.padding}d{ext}"
        return result

    @property
    def padding(self) -> int:
        """Property for the sequence padding used.

        :returns: int
        """
        frame = min(self.frames)
        result = len(str(frame.frame_number))
        return result

    @property
    def frames_missing(self) -> bool:
        """Property for checking if any frames are missing in the sequence.

        Could be extended to return a list of missing frames.

        :returns: bool
        """
        start = min(self.frames).frame_number
        end = max(self.frames).frame_number
        expected: int = len(range(start, end)) + 1
        return not expected == len(self.frames)

    @property
    def width(self) -> int:
        """Property for the sequence width based on the first found frame.

        :returns: int
        """
        return self.imageinfos[0].width

    @property
    def display_width(self) -> int:
        """Property for the sequence display_width based on the first found frame.

        :returns: int
        """
        return self.imageinfos[0].display_width

    @property
    def height(self) -> int:
        """Property for the sequence height based on the first found frame.

        :returns: int
        """
        return self.imageinfos[0].height

    @property
    def display_height(self) -> int:
        """Property for the sequence display_height based on the first found frame.

        :returns: int
        """
        return self.imageinfos[0].display_height
