from __future__ import annotations

import os
import logging
import uuid
from typing import List, Union, Dict
from pathlib import Path

import PyOpenColorIO as OCIO

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OCIOConfigFileGenerator:
    _description: str
    _vars: Dict[str, str] = {}
    _views: List[str] = []
    _config_path: Path  # OCIO Config file
    _ocio_config: OCIO.Config   # OCIO Config object
    _ocio_transforms: List = []
    _ocio_search_paths: List[str]
    _ocio_config_name: str = "config.ocio"
    _dest_path: str
    _operators: List[OCIO.Transform]

    def __init__(
        self,
        context: str = None,
        family: str = None,
        operators: List[OCIO.Transform] = None,
        config_path: str = None,
        working_space: str = None,
        views: List[str] = None,
        description: str = None,
        staging_dir: str = None,
        environment_variables: Dict = None,
    ):
        # Context is required
        if context:
            self.context = context
        else:
            raise ValueError("Context is required!")

        self.family = family or "LabLib"

        # Default working space
        if working_space is None:
            self.working_space = "ACES - ACEScg"
        else:
            self.working_space = working_space

        # Default views
        if views:
            self.set_views(views)

        if operators:
            self.set_operators(operators)

        # Set OCIO config path and with validation
        if config_path is None:
            env = get_vendored_env()

            if OCIO_env_path := env.get("OCIO", None):
                config_path = Path(OCIO_env_path)
            else:
                raise ValueError("OCIO environment variable not set!")

        if config_path.is_file():
            self._config_path = config_path
        else:
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Default staging directory
        if staging_dir is None:
            self.staging_dir = (
                Path(
                    os.environ.get("TEMP", os.environ["TMP"]),
                    "LabLib",
                    str(uuid.uuid4()),
                )
                .resolve()
                .as_posix()
            )
        else:
            self.staging_dir = staging_dir

        self._description = description or "LabLib OCIO Config"

        if environment_variables:
            self.set_vars(**environment_variables)

    def set_ocio_config_name(self, name: str) -> None:
        self._ocio_config_name = name

    def set_views(self, *args: Union[str, List[str]]) -> None:
        self.clear_views()
        self.append_views(*args)

    def set_operators(self, *args) -> None:
        self.clear_operators()
        self.append_operators(*args)

    def set_vars(self, **kwargs) -> None:
        self.clear_vars()
        self.append_vars(**kwargs)

    def clear_operators(self) -> None:
        self._operators = []

    def clear_views(self):
        self._views = []

    def clear_vars(self):
        self._vars = {}

    def append_operators(self, *args) -> None:
        for arg in args:
            if isinstance(arg, list):
                self.append_operators(*arg)
            else:
                self._operators.append(arg)

    def append_views(self, *args: Union[str, List[str]]) -> None:
        for arg in args:
            if isinstance(arg, list):
                self.append_views(*arg)
            else:
                self._views.append(arg)

    def append_vars(self, **kwargs) -> None:
        self._vars.update(kwargs)

    def get_config_path(self) -> str:
        return self._dest_path

    def get_description_from_config(self) -> str:
        return self._ocio_config.getDescription()

    def _get_search_paths_from_config(self) -> List[str]:
        return list(self._ocio_config.getSearchPaths())

    def _sanitize_search_paths(self, paths: List[str]) -> None:
        real_paths = []
        for p in paths:
            computed_path = self._config_path.parent / p
            if computed_path.is_file():
                computed_path = computed_path.parent.resolve()
                real_paths.append(computed_path.as_posix())
            elif computed_path.is_dir():
                computed_path = computed_path.resolve()
                real_paths.append(computed_path.as_posix())

        real_paths = list(set(real_paths))
        var_paths = [self._swap_variables(path) for path in real_paths]
        self._search_paths = var_paths

    def _get_absolute_search_paths(self) -> None:
        paths = self._get_search_paths_from_config()
        for ocio_transform in self._ocio_transforms:
            if not hasattr(ocio_transform, "getSrc"):
                continue
            search_path = Path(ocio_transform.getSrc())
            if not search_path.exists():
                log.warning(f"Path not found: {search_path}")

            paths.append(ocio_transform.getSrc())

        self._sanitize_search_paths(paths)

    def _change_src_paths_to_names(self) -> None:
        for ocio_transform in self._ocio_transforms:
            if not hasattr(ocio_transform, "getSrc"):
                continue

            # TODO: this should be probably somewhere else
            if (
                hasattr(ocio_transform, "getCCCId")
                and ocio_transform.getCCCId()
            ):
                ocio_transform.setCCCId(
                    self._swap_variables(ocio_transform.getCCCId())
                )

            search_path = Path(ocio_transform.getSrc())
            if not search_path.exists():
                log.warning(f"Path not found: {search_path}")

            # Change the src path to the name of the search path
            # and replace any found variables
            ocio_transform.setSrc(
                self._swap_variables(search_path.name))

    def _swap_variables(self, text: str) -> str:
        new_text = text
        for k, v in self._vars.items():
            new_text = text.replace(v, f"${k}")
        return new_text

    def load_config_from_file(self, filepath: str) -> None:
        self._ocio_config = OCIO.Config.CreateFromFile(filepath)

    def process_config(self) -> None:

        for k, v in self._vars.items():
            self._ocio_config.addEnvironmentVar(k, v)

        self._ocio_config.setDescription(self._description)
        group_transform = OCIO.GroupTransform(self._ocio_transforms)
        look_transform = OCIO.ColorSpaceTransform(
            src=self.working_space, dst=self.context
        )
        colorspace = OCIO.ColorSpace()
        colorspace.setName(self.context)
        colorspace.setFamily(self.family)
        colorspace.setTransform(
            group_transform,
            OCIO.ColorSpaceDirection.COLORSPACE_DIR_FROM_REFERENCE
        )
        look = OCIO.Look(
            name=self.context,
            processSpace=self.working_space,
            transform=look_transform
        )
        self._ocio_config.addColorSpace(colorspace)
        self._ocio_config.addLook(look)
        self._ocio_config.addDisplayView(
            self._ocio_config.getActiveDisplays().split(",")[0],
            self.context,
            self.working_space,
            looks=self.context,
        )

        if not self._views:
            views_value = self._ocio_config.getActiveViews()
        else:
            views_value = ",".join(self._views)

        self._ocio_config.setActiveViews(
            f"{self.context},{views_value}"
        )
        self._ocio_config.validate()

    def write_config(self, dest: str = None) -> str:
        search_paths = [f"  - {path}" for path in self._search_paths]

        config_lines = []
        for line in self._ocio_config.serialize().splitlines():
            if "search_path" not in line:
                config_lines.append(line)
                continue
            config_lines.extend(["", "search_path:"] + search_paths + [""])

        final_config = "\n".join(config_lines)
        dest = Path(dest).resolve()
        dest.parent.mkdir(exist_ok=True, parents=True)
        with open(dest.as_posix(), "w") as f:
            f.write(final_config)
        return final_config

    def create_config(self, dest: str = None) -> None:
        if not dest:
            dest = Path(self.staging_dir, self._ocio_config_name)
        dest = Path(dest).resolve().as_posix()
        self.load_config_from_file(self._config_path.resolve().as_posix())

        for op in self._operators:
            self._ocio_transforms.append(op)

        self._get_absolute_search_paths()
        self._change_src_paths_to_names()
        self.process_config()
        self.write_config(dest)
        self._dest_path = dest
        return dest

    def get_oiiotool_cmd(self) -> List:
        return [
            "--colorconfig",
            self._dest_path,
            (
                f"--ociolook:from=\"{self.working_space}\""
                f":to=\"{self.working_space}\""
            ),
            self.context,
        ]
