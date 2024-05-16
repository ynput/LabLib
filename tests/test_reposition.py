import json
import logging
from pathlib import Path
from typing import List, Union

import pytest

from lablib.operators import Transform, Crop, Mirror2

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def __get_reposition_operators(file: Union[Path, str], type: str = None):
    if isinstance(file, str):
        file = Path(file)

    ops = []
    with file.open("r") as f:
        data = json.load(f)
        for k, v in data.items():
            if isinstance(v, dict):
                if "OCIO" not in k:
                    if v.get("class") == type:
                        ops.append(v)
                    # ops[k] = v
    return ops


mirrors = __get_reposition_operators(
    "resources/public/effectPlateMain/v001/a01vfxd_sh020_effectPlateP01_v002.json",
    type="Mirror2",
)
mirrors = [(i, op) for i, op in enumerate(mirrors)]
log.warning(f"{mirrors = }")


@pytest.mark.parametrize(
    "transform_op_data",
    [
        op
        for op in __get_reposition_operators(
            "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json",
            type="Transform",
        )
    ],
)
def test_Transform(transform_op_data):
    xfm = Transform.from_node_data(transform_op_data)
    log.info(f"{xfm = }")
    oiio_args = xfm.to_oiio_args()

    # assert fields
    assert xfm.translate == [0.0, 0.0]
    assert xfm.rotate == 0.0
    assert xfm.scale == [0.0, 0.0]
    assert xfm.center == [0.0, 0.0]
    assert xfm.skewX == 0.0
    assert xfm.skewY == 0.0
    assert not xfm.invert

    # assert argument output
    assert oiio_args == [
        "--translate 0.0 0.0",
        "--rotate 0.0",
        "--scale 0.0 0.0",
        "--center 0.0 0.0",
    ]


@pytest.mark.parametrize(
    "crop_op_data",
    [
        op
        for op in __get_reposition_operators(
            "resources/public/effectPlateMain/v001/a01vfxd_sh020_effectPlateP01_v002.json",
            type="Crop",
        )
    ],
)
def test_Crop(crop_op_data):
    crop = Crop.from_node_data(crop_op_data)
    oiio_args = crop.to_oiio_args()

    # assert fields
    assert crop.box == [0, 0, 1920, 1080]

    # assert argument output
    assert oiio_args == [
        "--crop 0,0,1920,1080",
    ]


@pytest.mark.parametrize(
    "index, mirror_op_data",
    [
        (i, op)
        for i, op in enumerate(
            __get_reposition_operators(
                "resources/public/effectPlateMain/v001/a01vfxd_sh020_effectPlateP01_v002.json",
                type="Mirror2",
            )
        )
    ],
)
def test_Mirror2(index, mirror_op_data):
    log.info(f"{index = }")
    log.info(f"{mirror_op_data = }")
    mirror = Mirror2.from_node_data(mirror_op_data["node"])
    log.info(f"{mirror = }")
    oiio_args = mirror.to_oiio_args()

    if index == 0:
        assert mirror.flop is False
        assert mirror.flip is True
        assert oiio_args == ["--flip"]
    if index == 1:
        assert mirror.flop is True
        assert mirror.flip is False
        assert oiio_args == ["--flop"]
