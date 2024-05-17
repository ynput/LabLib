import json
from pprint import pformat
import pytest

from lablib import OCIOConfigFileProcessor


from tests.lib.testing_classes import MainTestClass


class TestConfigExportProcessor(MainTestClass):
    @pytest.mark.parametrize(
        "mock_data_path", ["resources/public/mock_data.json"])
    def test_OCIOConfigFileProcessor(
        self, mock_data_path,
        effect_processor,
        test_staging_dir,
    ):
        staging_dir_path = test_staging_dir.as_posix()

        # Get data from Asset
        with open(mock_data_path, "r") as f:
            working_data = json.loads(f.read())

        # Compute color transformations
        ocio_config_processor = OCIOConfigFileProcessor(
            operators=effect_processor.color_operators,
            staging_dir=test_staging_dir,
            context=working_data["asset"],
            family=working_data["project"]["code"],
            views=["sRGB", "Rec.709", "Log", "Raw"],
            environment_variables={
                "CONTEXT": "BLD_010_0010",
                "PROJECT_ROOT": "C:/CODE/LabLib/resources",
            },
        )

        ocio_config_processor.create_config()

        color_cmd = ocio_config_processor.get_oiiotool_cmd()

        self.log.debug(color_cmd)
        assert color_cmd == [
            "--colorconfig",
            f"{staging_dir_path}/config.ocio",
            '--ociolook:from="ACES - ACEScg":to="ACES - ACEScg"',
            "BLD_010_0010",
        ]
        assert ocio_config_processor._dest_path == f"{staging_dir_path}/config.ocio"  # noqa: E501