from __future__ import annotations

import os
import uuid
from typing import List, Union, Dict
from dataclasses import dataclass, field
from pathlib import Path


import PyOpenColorIO as OCIO

@dataclass
class OCIOConfigFileProcessor:
    operators: List = field(default_factory=list)
    config_path: str = None
    staging_dir: str = None
    context: str = "LabLib"
    family: str = "LabLib"
    working_space: str = "ACES - ACEScg"
    views: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.config_path:
            self.config_path = Path(os.environ.get("OCIO")).as_posix()

        if not self.staging_dir:
            self.staging_dir = (
                Path(
                    os.environ.get("TEMP", os.environ["TMP"]),
                    "LabLib",
                    str(uuid.uuid4()),
                )
                .resolve()
                .as_posix()
            )
        self._description: str = None
        self._vars: Dict = {}
        self._views: List[str] = None
        if self.views:
            self._views: List[str] = self.set_views(self.views)
        self._ocio_config: OCIO.Config = None
        self._ocio_transforms: List = []
        self._ocio_search_paths: List = []
        self._ocio_config_name: str = "config.ocio"
        self._dest_path: str = None

    def set_ocio_config_name(self, name: str) -> None:
        self._ocio_config_name = name

    def set_staging_dir(self, path: str) -> None:
        self.staging_dir = Path(path).resolve().as_posix()

    def set_views(self, *args: Union[str, List[str]]) -> None:
        self.clear_views()
        self.append_views(*args)

    def set_operators(self, *args) -> None:
        self.clear_operators()
        self.append_operators(*args)

    def set_vars(self, **kwargs) -> None:
        self.clear_vars()
        self.append_vars(**kwargs)

    def set_description(self, desc: str) -> None:
        self._description = desc

    def clear_operators(self) -> None:
        self.operators = []

    def clear_views(self):
        self._views = []

    def clear_vars(self):
        self._vars = {}

    def append_operators(self, *args) -> None:
        for arg in args:
            if isinstance(arg, list):
                self.append_operators(*arg)
            else:
                self.operators.append(arg)

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

    def _sanitize_search_paths(self, paths: List[str]) -> List[str]:
        real_paths = []
        for p in paths:
            computed_path = Path(Path(self.config_path).parent, p).resolve()
            if computed_path.is_file():
                computed_path = Path(computed_path.parent).resolve()
                real_paths.append(computed_path.as_posix())
            elif computed_path.is_dir():
                computed_path = computed_path.resolve()
                real_paths.append(computed_path.as_posix())

        real_paths = list(set(real_paths))
        self._search_paths = real_paths
        return real_paths

    def _get_absolute_search_paths_from_ocio(self) -> List[str]:
        paths = self._get_search_paths_from_config()
        for op in self._ocio_transforms:
            try:
                paths.append(op.getSrc())
            except:
                # TODO find out why this crashes and capture explicit
                #   exceptions
                continue
        return self._sanitize_search_paths(paths)

    def _get_absolute_search_paths(self) -> List[str]:
        paths = self._get_search_paths_from_config()
        for op in self.operators:
            if hasattr(op, "src"):
                paths.append(op.src)
        return self._sanitize_search_paths(paths)

    def _read_config(self) -> None:
        self._ocio_config = OCIO.Config.CreateFromFile(self.config_path)

    def load_config_from_file(self, src: str) -> None:
        self.config_path = src
        self._read_config()

    def process_config(self) -> None:
        for op in self.operators:
            self._ocio_transforms.append(op)

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
        self.load_config_from_file(Path(self.config_path).resolve().as_posix())
        self._get_absolute_search_paths()
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
