"""Module providing classes for handling image metadata and sequences."""

from __future__ import annotations

import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional

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

    Note:
        All attributes are optional and will be set from calling ``iinfo`` and ``ffprobe`` in :obj:`ImageInfo.update()` if found.
        Defaults are set if not found and set by user. See the next example for defaults.

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
    width: int = field(
        default=IMAGE_INFO_DEFAULTS["width"], init=False, repr=True)
    height: int = field(
        default=IMAGE_INFO_DEFAULTS["height"], init=False, repr=True)
    origin_x: int = field(
        default=IMAGE_INFO_DEFAULTS["origin_x"], init=False, repr=False)
    origin_y: int = field(
        default=IMAGE_INFO_DEFAULTS["origin_y"], init=False, repr=False)
    display_width: int = field(
        default=IMAGE_INFO_DEFAULTS["display_width"], init=False, repr=False)
    display_height: int = field(
        default=IMAGE_INFO_DEFAULTS["display_height"], init=False, repr=False)
    par: float = field(
        default=IMAGE_INFO_DEFAULTS["par"], init=False, repr=False)
    channels: int = field(
        default=IMAGE_INFO_DEFAULTS["channels"], init=False, repr=True)

    fps: float = field(
        default=IMAGE_INFO_DEFAULTS["fps"], init=False, repr=False)
    timecode: str = field(
        default=IMAGE_INFO_DEFAULTS["timecode"], init=False, repr=False)
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

    def update(self, force_ffprobe: Optional[bool] = False) -> None:
        """Updates metadata by calling iinfo and ffprobe.

        Attention:
            During testing it was found that ``ffprobe`` reported different
            framerates on different systems. Therefore we added the
            ``force_ffprobe=False`` flag to silently disable ``ffprobe``.

        Arguments:
            force_ffprobe (Optional[bool]): whether to override attributes with
                ``ffprobe`` output if found.
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
        """:obj:`str`: The image file name including extension."""
        return self.path.name

    @property
    def rational_time(self) -> opentime.RationalTime:
        """:obj:`opentime.RationalTime`: Retrieved from :obj:`ImageInfo.timecode` using otio library."""
        if not all([self.timecode, self.fps]):
            raise Exception("no timecode and fps found")

        return opentime.from_timecode(self.timecode, self.fps)

    @property
    def frame_number(self) -> int:
        """:obj:`int`: Retrieved from the filename by using regex lookup.

        Note:
            The regex could use a little love to be more robust.
            Filename should be something like ``filename.0001.exr``.
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
        """:obj:`str`: The file extension."""
        return self.path.suffix

    @property
    def name(self) -> str:
        """:obj:`str`: The file name with extension.

        Note:
            Used in SequenceInfo but could become obsolete in favor
            for `filename`.
        """
        return f"{self.path.stem}{self.path.suffix}"

    @property
    def filepath(self) -> str:
        """:obj:`str`: The file path as posix string."""

        return self.path.resolve().as_posix()


@dataclass
class SequenceInfo:
    """Class for handling image sequences by using instances of `ImageInfo`.

    Hint:
        If you want to scan a directory for image sequences, you can use the
        ``scan`` classmethod.

    Attributes:
        path Any[Path, str]: Path to the image sequence directory.
        imageinfos List[ImageInfo]: List of all files as `ImageInfo` to be
            used.
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
        """Scan a directory for a list of images.

        Attention:
            Currently only supports EXR files. Needs to be extended and tested
            for other formats.

        Arguments:
            directory (Any[str, Path]): Path to the directory
                to be scanned.

        Returns:
            List[SequenceInfo]: List of all found sequences.
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
        """:obj:`List[int]`: List of all available frame numbers in the sequence."""  # noqa
        return [ii.frame_number for ii in self.imageinfos]

    @property
    def start_frame(self) -> int:
        """:obj:`int`: the lowest frame number in the sequence."""
        return min(self.frames).frame_number

    @property
    def end_frame(self) -> int:
        """:obj:`int`: the highest frame number in the sequence."""
        return max(self.frames).frame_number

    @property
    def format_string(self) -> str:
        """:obj:`str`: A sequence representation used for ``ffmpeg`` arguments formatting."""  # noqa
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]

        result = f"{basename}.%0{self.padding}d{ext}"
        return result

    @property
    def hash_string(self) -> str:
        """:obj:`str`: A sequence representation used for ``oiiotool`` arguments formatting."""  # noqa
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]

        result = f"{basename}.{self.start_frame}-{self.end_frame}#{ext}"
        return result

    @property
    def format_string(self) -> str:
        """:obj:`str`: A sequence representation used for ``ffmpeg`` arguments formatting.  # noqa

        Error:
            That's a duplicate so let's run tests and remove it.
        """
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]

        result = f"{basename}.%0{self.padding}d{ext}"
        return result

    @property
    def padding(self) -> int:
        """:obj:`int`: The sequence's frame padding."""
        frame = min(self.frames)
        result = len(str(frame.frame_number))
        return result

    @property
    def frames_missing(self) -> bool:
        """:obj:`bool`: Property for checking if any frames are missing in the sequence.  # noqa

        Note:
            Could be extended to also return which frames are missing.
        """
        start = min(self.frames).frame_number
        end = max(self.frames).frame_number
        expected: int = len(range(start, end)) + 1
        return not expected == len(self.frames)

    @property
    def width(self) -> int:
        """:obj:`int`: the sequence's width based on the first frame found."""
        return self.imageinfos[0].width

    @property
    def display_width(self) -> int:
        """:obj:`int`: the sequence's display_width based on the first frame found."""  # noqa
        return self.imageinfos[0].display_width

    @property
    def height(self) -> int:
        """:obj:`int`: the sequence's height based on the first frame found."""
        return self.imageinfos[0].height

    @property
    def display_height(self) -> int:
        """:obj:`int`: the sequence's display_height based on the first frame found."""  # noqa
        return self.imageinfos[0].display_height
