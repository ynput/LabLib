import pytest

from pathlib import Path
import json
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@pytest.fixture
def transform_op_data():
    file = Path(
        "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"
    )

    with file.open("r") as f:
        data = json.load(f)

    transforms = []
    for key in data.keys():
        if "Transform" in key:
            if "OCIO" not in key:
                transforms.append(data[key])

    for transform in transforms:
        yield transform
