import json
import logging
import pytest
from pathlib import Path

from lablib.processors import (
    EffectsFileProcessor,
    ColorProcessor,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# Project Constants
SOURCE_DIR = "resources/public/plateMain/v000"
DATA_PATH = "resources/public/mock_data.json"
EFFECT_PATH = "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"
SLATE_TEMPLATE_PATH = "templates/slates/slate_generic/slate_generic.html"
STAGING_DIR = "results"
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080

# Get data from Asset
with open(DATA_PATH, "r") as f:
    working_data = json.loads(f.read())


@pytest.mark.parametrize(
    "path",
    [
        "resources/public/effectPlateMain/v000/"
        "BLD_010_0010_effectPlateMain_v000.json"
    ],
)
def test_EffectsFileProcessor(path: str):
    path = Path(path)
    effect_processor = EffectsFileProcessor(path)
    assert effect_processor.src == path
    assert len(effect_processor.color_operators) == 4


# # Compute Effects file from AYON
# epr = EffectsFileProcessor(EFFECT_PATH)

# # Compute color transformations
# color_processor = ColorProcessor(
#     operators=epr.color_operators,
#     staging_dir=STAGING_DIR,
#     context=working_data["asset"],
#     family=working_data["project"]["code"],
#     views=["sRGB", "Rec.709", "Log", "Raw"],
# )

# color_processor.create_config()

# color_cmd = color_processor.get_oiiotool_cmd()

# print(color_cmd)
