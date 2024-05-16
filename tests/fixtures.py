from typing import List, Union
import pytest

from pathlib import Path
import json
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def _get_reposition_operators(file: Union[Path, str]) -> List[dict]:
    if isinstance(file, str):
        file = Path(file)

    ops = []
    with file.open("r") as f:
        data = json.load(f)
        for k, v in data.items():
            if isinstance(v, dict):
                if "OCIO" not in k:
                    ops.append(v)
    return ops


@pytest.fixture
def transform_op_data():
    file = Path(
        "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"
    )

    transforms = []
    ops = _get_reposition_operators(file)
    for op in ops:
        if op.get("class") == "Transform":
            transforms.append(op)

    for transform in transforms:
        yield transform


@pytest.fixture
def crop_op_data():
    file = Path(
        "resources/public/effectPlateMain/v001/a01vfxd_sh020_effectPlateP01_v002.json"
    )

    crops = []
    ops = _get_reposition_operators(file)
    for op in ops:
        if op.get("class") == "Crop":
            crops.append(op)

    for crop in crops:
        yield crop
