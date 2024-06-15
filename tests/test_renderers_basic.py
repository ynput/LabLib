import logging

import pytest

from lablib.lib import SequenceInfo

from lablib.processors import OIIORepositionProcessor
from lablib.renderers import BasicRenderer

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


test_data = [
    {
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results",
    },
    {
        "repo_proc": OIIORepositionProcessor(),
        "source_sequence": SequenceInfo.scan("resources/public/plateMain/v002")[0],
        "output_dir": "test_results",
        "codec": "ProRes422-HQ",
        "fps": 25,
        "keep_only_container": True,
    },
]


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
