import json
import logging
from pathlib import Path

import pytest

from lablib.lib import SequenceInfo

from lablib.processors import (
    OIIORepositionProcessor,
    AYONHieroEffectsFileProcessor,
    OCIOConfigFileProcessor,
    AYONOCIOLookFileProcessor,
)
from lablib.renderers import BasicRenderer

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

mock_data = json.loads(Path("resources/public/mock_data.json").read_text())

effect_processor = AYONHieroEffectsFileProcessor(
    Path("resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json")
)
effect_processor.load()
ocio_config_processor = OCIOConfigFileProcessor(
    operators=effect_processor.color_operators,
    staging_dir=Path("test_results").resolve().as_posix(),
    context=mock_data["asset"],
    family=mock_data["project"]["code"],
    views=["sRGB", "Rec.709", "Log", "Raw"],
    environment_variables={
        "CONTEXT": "BLD_010_0010",
        "PROJECT_ROOT": "C:/CODE/LabLib/resources",
    },
)
ocio_config_processor.create_config()

test_data = [
    # test reformat with hiero effectsfile only repositions
    {
        # "processor": ocio_config_processor,   # can't read generated config.ocio
        "processor": OIIORepositionProcessor(
            effect_processor.repo_operators,
            dst_width=1920,
            dst_height=1080,
        ),
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results/effectPlateMain/v000/onlyRepositions",
        "codec": "ProRes422-HQ",
        "fps": 25,
        "keep_only_container": False,
    },
    # test full hiero effect processor
    {
        "processor": effect_processor,
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results/effectPlateMain/v000",
        "codec": "ProRes422-HQ",
        "fps": 25,
        "keep_only_container": False,
    },
    # test with ayon ociolookfile
    {
        "processor": AYONOCIOLookFileProcessor(
            Path("resources/public/ociolookMain/v005/jp03_john_ociolookMain_v005.json")
        ),
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results/ociolookMain/v005",
        "codec": "ProRes422-HQ",
        "fps": 25,
        "keep_only_container": False,
    },
]
log.info(f"{test_data = }")


@pytest.mark.parametrize(
    "test_index, test_data",
    enumerate(test_data),
)
def test_BasicRenderer(test_index, test_data):
    rend = BasicRenderer(**test_data)
    log.info(f"{test_index = }")
    log.info(f"renderer = {rend}")
    rend.render(debug=True)

    # TODO: assertions
