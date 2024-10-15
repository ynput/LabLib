from cgi import test
import json
import logging
from pathlib import Path
import pytest

import PyOpenColorIO as OCIO

from lablib import (
    OCIOConfigFileGenerator,
    AYONHieroEffectsFileProcessor
)


log = logging.getLogger(__name__)


class TestConfigExportProcessor:
    # TODO: test for ocio v2 configs

    @pytest.fixture()
    def effect_processor(self):
        path = Path(
            "resources/public/effectPlateMain/v000/"
            "BLD_010_0010_effectPlateMain_v000.json"
        )
        effect_processor = AYONHieroEffectsFileProcessor(path)
        log.debug(f"{effect_processor = }")
        effect_processor.load()
        yield effect_processor

    @pytest.mark.parametrize(
        "mock_data_path", ["resources/public/mock_data.json"])
    def test_OCIOConfigFileGenerator(
        self, mock_data_path,
        effect_processor,
        test_staging_dir,
    ):
        staging_dir_path = test_staging_dir.as_posix()
        log.debug(f"{staging_dir_path = }")

        lablib_root = Path(staging_dir_path).resolve().parent

        # Get data from Asset
        with open(mock_data_path, "r") as f:
            working_data = json.loads(f.read())

        test_context_input = working_data["asset"]

        test_environment_variables = {
            "CONTEXT": test_context_input,
            "PROJECT_ROOT": lablib_root.as_posix(),
        }
        # Compute color transformations
        ocio_config_processor = OCIOConfigFileGenerator(
            operators=effect_processor.color_operators,
            staging_dir=test_staging_dir,
            context=test_context_input,
            target_view_space="Output - sRGB",
            family=working_data["project"]["code"],
            views=["sRGB", "Rec.709", "Log", "Raw"],
            environment_variables=test_environment_variables,
        )

        ocio_config_processor.create_config()

        # test config file path
        resulting_config_path = ocio_config_processor._dest_path
        testing_config_path = Path(staging_dir_path, "config.ocio").as_posix()
        assert resulting_config_path == testing_config_path

        # test color command
        color_cmd = ocio_config_processor.get_oiiotool_cmd()
        assert color_cmd == [
            "--colorconfig",
            testing_config_path,
            '--ociolook:from="ACES - ACEScg":to="ACES - ACEScg"',
            test_context_input,
        ]

        # test content of the config file
        ocio_config = OCIO.Config.CreateFromFile(resulting_config_path)

        # test environment variables
        ocio_env_vars = ocio_config.getEnvironmentVarNames()
        for env_var in test_environment_variables:
            # test key is in the environment variables
            assert env_var in ocio_env_vars

        # test search paths with environment variables
        search_paths = ocio_config.getSearchPaths()
        for path in search_paths:
            log.debug(f"{path = }")
            assert path.startswith("$PROJECT_ROOT")

        # test context related colorspace
        colorspaces = ocio_config.getColorSpaceNames()
        assert test_context_input in colorspaces

        # test context related look
        looks = ocio_config.getLookNames()
        assert test_context_input in looks

        # test context related view
        # TODO: refactor this in future so we are settings display explicitly
        active_display = ocio_config.getActiveDisplays().split(",")[0]
        views = ocio_config.getViews(active_display)
        test_views = list(views)
        assert test_context_input in test_views
