import json
from pprint import pformat
import pytest
from pathlib import Path

from lablib import OCIOConfigFileProcessor


from tests.lib.testing_classes import MainTestClass


class TestConfigExportProcessor(MainTestClass):
    @pytest.mark.parametrize(
        "mock_data_path", ["resources/public/mock_data.json"])
    def test_OCIOConfigFileProcessor(self, mock_data_path, effect_processor):  # noqa: F811, E501
        test_parent_dir = Path(__file__).resolve().parent.parent
        staging_dir_path = Path(test_parent_dir, self.STAGING_DIR).as_posix()

        # Get data from Asset
        with open(mock_data_path, "r") as f:
            working_data = json.loads(f.read())

        self.log.debug(pformat(working_data))

        # Compute color transformations
        ocio_config_processor = OCIOConfigFileProcessor(
            operators=effect_processor.color_operators,
            staging_dir=self.STAGING_DIR,
            context=working_data["asset"],
            family=working_data["project"]["code"],
            views=["sRGB", "Rec.709", "Log", "Raw"],
            environment_variables={
                "PROJECT_ROOT": "C:/CODE/LabLib/resources",
                "CONTEXT": "BLD_010_0010",
            },
        )

        ocio_config_processor.create_config()

        color_cmd = ocio_config_processor.get_oiiotool_cmd()

        self.log.info(color_cmd)
        assert color_cmd == [
            "--colorconfig",
            f"{staging_dir_path}/config.ocio",
            '--ociolook:from="ACES - ACEScg":to="ACES - ACEScg"',
            "BLD_010_0010",
        ]
        assert ocio_config_processor._dest_path == f"{staging_dir_path}/config.ocio"  # noqa: E501
