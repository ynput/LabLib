import json
import logging
from pprint import pformat
import pytest
from pathlib import Path

from lablib import (
    AYONHieroEffectsFileProcessor,
    OCIOConfigFileProcessor,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# Project Constants
STAGING_DIR = "results"


@pytest.fixture(scope="module")
def effect_processor():
    path = Path(
        "resources/public/effectPlateMain/v000/"
        "BLD_010_0010_effectPlateMain_v000.json"
    )
    effect_processor = AYONHieroEffectsFileProcessor(path)
    effect_processor.load()
    yield effect_processor
    effect_processor.clear_operators()


@pytest.mark.parametrize(
    "mock_data_path", ["resources/public/mock_data.json"])
def test_OCIOConfigFileProcessor(mock_data_path, effect_processor):
    test_parent_dir = Path(__file__).resolve().parent.parent
    staging_dir_path = Path(test_parent_dir, STAGING_DIR).as_posix()

    # Get data from Asset
    with open(mock_data_path, "r") as f:
        working_data = json.loads(f.read())

    log.debug(pformat(working_data))

    # Compute color transformations
    ocio_config_processor = OCIOConfigFileProcessor(
        operators=effect_processor.color_operators,
        staging_dir=STAGING_DIR,
        context=working_data["asset"],
        family=working_data["project"]["code"],
        views=["sRGB", "Rec.709", "Log", "Raw"],
    )

    ocio_config_processor.create_config()

    color_cmd = ocio_config_processor.get_oiiotool_cmd()

    log.info(color_cmd)
    assert color_cmd == [
        "--colorconfig",
        f"{staging_dir_path}/config.ocio",
        '--ociolook:from="ACES - ACEScg":to="ACES - ACEScg"',
        "BLD_010_0010",
    ]
    assert ocio_config_processor._dest_path == f"{staging_dir_path}/config.ocio"  # noqa: E501
