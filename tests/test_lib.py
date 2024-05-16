import pytest
import logging
from pathlib import Path

from opentimelineio.opentime import RationalTime

from lablib.lib import (
    ImageInfo,
    SequenceInfo,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "path", ["resources/public/plateMain/v000/BLD_010_0010_plateMain_v000.1001.exr"]
)
def test_ImageInfo(path: str):
    path = Path(path)
    image_info = ImageInfo(path)
    assert image_info.par == 1.0
    assert image_info.fps == 24.0
    assert image_info.width == 4382
    assert image_info.height == 2310
    assert image_info.channels == 3
    assert image_info.filepath == path
    assert image_info.filename == path.name
    assert image_info.timecode == "02:10:04:17"
    assert image_info.rational_time == RationalTime(187313, 24)


def test_single_frame_sequence():
    path = Path("resources/public/plateMain/v000")
    seq_info = SequenceInfo.scan(path)[0]
    log.info(f"{seq_info = }")
    print(seq_info)
    assert seq_info.path == path
    assert seq_info.hash_string == "BLD_010_0010_plateMain_v000.1001#1.exr"
    assert seq_info.start_frame == 1001
    assert seq_info.end_frame == 1001
    assert seq_info.padding == 4
    assert not seq_info.frames_missing


def test_SequenceInfo_missing_frames():
    path = Path("resources/public/plateMain/v001")
    seq_info = SequenceInfo.scan(path)[0]
    log.info(f"{seq_info = }")
    assert seq_info.path == path
    assert seq_info.start_frame == 1001
    assert seq_info.end_frame == 1003
    assert seq_info.frames_missing
    # TODO: which missing frames