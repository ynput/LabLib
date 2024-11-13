import json
import logging
from pathlib import Path

import pytest

from lablib.lib import SequenceInfo

from lablib.processors import (
    OIIORepositionProcessor,
    AYONHieroEffectsFileProcessor,
    AYONOCIOLookFileProcessor,
)
from lablib.generators import OCIOConfigFileGenerator
from lablib.renderers import BasicRenderer, RendererBase

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

mock_data = json.loads(Path("resources/public/mock_data.json").read_text())

effect_processor = AYONHieroEffectsFileProcessor(
    Path("resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json")
)
effect_processor.load()
ocio_config_generator = OCIOConfigFileGenerator(
    ocio_objects=effect_processor.ocio_objects,
    staging_dir=Path("test_results").resolve().as_posix(),
    context=mock_data["asset"],
    family=mock_data["project"]["code"],
    views=["sRGB", "Rec.709", "Log", "Raw"],
    environment_variables={
        "CONTEXT": "BLD_010_0010",
        "PROJECT_ROOT": "C:/CODE/LabLib/resources",
    },
)
ocio_config_generator.create_config()

test_data = [
    # test reposition processor
    {
        "processor": OIIORepositionProcessor(
            dst_width=1920,
            dst_height=1080,
            fit="letterbox",
        ),
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results/reformat_1080p/letterbox",
        "codec": "ProRes422-HQ",
        "fps": 25,
        "keep_only_container": False,
    },
    # test full hiero effect processor
    {
        "processor": effect_processor,
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results/effectPlateMain/v000",
        "codec": "ProRes4444-XQ",
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
        "codec": "DNxHR-SQ",
        "fps": 25,
        "keep_only_container": False,
    },
    # test burnins
    {
        "burnins": {
            "size": 64,
            "color": (0.5, 0.5, 0.5),  # grey
            "font": "vendor/font/ttf/source-code-pro-latin-700-normal.ttf",
            "outline": 1,
            "data": [
                {
                    "text": "TOP_LEFT",
                    "position": "top_left",
                },
                {
                    "text": "topcenter",
                    "position": "top_center",
                },
                {
                    "text": "topright",
                    "position": "top_right",
                },
                {
                    "text": "bottom_left",
                    "position": "bottom_left",
                },
                {
                    "text": "bottom_center",
                    "position": "bottom_center",
                },
                {
                    "text": "bottom_right",
                    "position": "bottom_right",
                },
            ],
        },
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results/burnins",
        "codec": "ProRes422-HQ",
        "fps": 25,
        "keep_only_container": False,
    },
    # test ocio config generator
    {
        # TODO: i think we need an OCIOLookTransformProcessor that handles oiio args and OCIOConfigFileGenerator
        "processor": ocio_config_generator,
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results/ociolook",
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


def test_inheritance_BasicRenderer():
    """Ensure BasicRenderer inherits from RendererBase
    """
    assert issubclass(BasicRenderer, RendererBase)
