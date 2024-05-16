import logging
import pytest
from pathlib import Path

from lablib import (
    AYONHieroEffectsFileProcessor,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# Project Constants
STAGING_DIR = "results"


@pytest.fixture()
def effect_processor():
    path = Path(
        "resources/public/effectPlateMain/v000/"
        "BLD_010_0010_effectPlateMain_v000.json"
    )
    effect_processor = AYONHieroEffectsFileProcessor(path)
    effect_processor.load()
    yield effect_processor
