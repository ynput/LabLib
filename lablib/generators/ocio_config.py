from __future__ import annotations

import os
import logging
import uuid
from typing import List, Union, Dict, Optional
from pathlib import Path

import PyOpenColorIO as OCIO
from ..lib import get_vendored_env

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OCIOConfigFileGenerator:
    """Class for generating and manipulating OCIO Config files.

    Attributes:
        context (str): The context of the OCIO Config file.
        config_path (Optional[str]): The path to the OCIO Config file.
        family (Optional[str]): The family of the OCIO Config file.
        operators (Optional[List[OCIO.Transform]]): A list of OCIO Transform
            objects.
        working_space (Optional[str]): The working space of the OCIO Config
            file.
        target_view_space (Optional[str]): The target view space of the OCIO
            Config file. For views to be using specific color spaces
            different from working space.
        views (Optional[List[str]]): A list of views.
        description (Optional[str]): The description of the OCIO Config file.
        staging_dir (Optional[str]): The staging directory of the OCIO Config
            file.
        environment_variables (Optional[Dict]): A dictionary of environment
            variables.
        search_paths (Optional[List[str]]): A list of search paths.

    Example:
        >>> from lablib.operators import LUT
        >>> from lablib.generators import OCIOConfigFileGenerator
        >>> lut = LUT(src="src", dst="dst")
        >>> ocio = OCIOConfigFileGenerator(
        ...     context="context",
        ...     config_path="config.ocio",
        ...     operators=[lut],
        ...     working_space="working_space",
        ...     views=["view1", "view"],
        ...     description="description",
        ...     staging_dir="staging_dir",
        ...     environment_variables={"key": "value"},
        ... )
        >>> ocio.create_config()
        '<staging_dir_path>/config.ocio'

    Raises:
        ValueError: If :attr:`config_path` is not set and the OCIO
            environment variable is not set.
        FileNotFoundError: If the OCIO Config file is not found.

    """
    log: logging.Logger = log

    _description: str
    _vars: Dict[str, str] = {}
    _views: List[str] = []
    _config_path: Path  # OCIO Config file
    _ocio_config: OCIO.Config  # OCIO Config object
    _ocio_search_paths: List[str] = []
    _ocio_config_name: str = "config.ocio"
    _dest_path: str = ""
    _operators: List[OCIO.Transform] = []

    def __init__(
        self,
        context: str,
        family: Optional[str] = None,
        operators: Optional[List[OCIO.Transform]] = None,
        config_path: Optional[str] = None,
        working_space: Optional[str] = None,
        target_view_space: Optional[str] = None,
        views: Optional[List[str]] = None,
        description: Optional[str] = None,
        staging_dir: Optional[str] = None,
        environment_variables: Optional[Dict] = None,
        search_paths: Optional[List[str]] = None,
        logger: logging.Logger = None,
    ):

        # Context is required
        self.context = context

        self.family = family or "LabLib"

        # Default working space
        if working_space is None:
            self.working_space = "ACES - ACEScg"
        else:
            self.working_space = working_space

        # Default target view space
        if target_view_space is None:
            self.target_view_space = self.working_space
        else:
            self.target_view_space = target_view_space

        # Default views
        if views:
            self.set_views(views)

        # Default operators
        if operators:
            self.set_operators(operators)
        else:
            self.clear_operators()

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

        # first clear all search paths
        self._ocio_search_paths = []
        if search_paths:
            # add additional search paths
            self.set_search_paths(search_paths)

        if logger:
            self.log = logger

    def set_ocio_config_name(self, name: str) -> None:
        """Set the name of the OCIO Config file.

        Arguments:
            name (str): The name of the OCIO Config file.
        """
        self._ocio_config_name = name

    def set_views(self, *args: Union[str, List[str]]) -> None:
        """Set the views for the OCIO Config file.

        Attention:
            This will clear any existing views.

        Arguments:
            *args: A list of views.
        """
        self.clear_views()
        self.append_views(*args)

    def set_search_paths(self, *args: Union[str, List[str]]) -> None:
        self.append_search_paths(*args)

    def set_operators(self, *args) -> None:
        """Set operators.

        Attention:
            This will clear any existing operators.

        Arguments:
            *args: A list of :obj:`lablib.operators` objects.
        """
        self.clear_operators()
        self.append_operators(*args)

    def set_vars(self, **kwargs) -> None:
        """Set the environment variables for the OCIO Config file.

        Attention:
            This will clear any existing environment variables.

        Arguments:
            **kwargs: A key/value map of environment variables.
        """
        self.clear_vars()
        self.append_vars(**kwargs)

    def clear_operators(self) -> None:
        """Clear the operators."""
        self._operators = []

    def clear_views(self):
        """Clear the views."""
        self._views = []

    def clear_vars(self):
        """Clear the environment variables."""
        self._vars = {}

    def append_search_paths(self, *args) -> None:
        """Append search paths.

        Arguments:
            *args: A list of search paths.
        """
        for arg in args:
            if isinstance(arg, list):
                self.append_search_paths(*arg)
            else:
                self._ocio_search_paths.append(self._swap_variables(arg))

    def append_operators(self, *args) -> None:
        """Append operators.

        Arguments:
            *args: A list of :obj:`lablib.operators` objects.
        """
        for arg in args:
            if isinstance(arg, list):
                self.append_operators(*arg)
            else:
                self._operators.append(arg)

    def append_views(self, *args: Union[str, List[str]]) -> None:
        """Append views.

        Arguments:
            *args: A list of views.
        """
        for arg in args:
            if isinstance(arg, list):
                self.append_views(*arg)
            else:
                self._views.append(arg)

    def append_vars(self, **kwargs) -> None:
        """Append environment variables.

        Arguments:
            **kwargs: A key/value map of environment variables.
        """
        self._vars.update(kwargs)

    def get_config_path(self) -> str:
        """Return the path to the OCIO Config file.

        Returns:
            str: The path to the OCIO Config file.
        """
        return self._dest_path

    def get_description_from_config(self) -> str:
        """Return the description from the OCIO Config file.

        Returns:
            str: The description text.
        """
        return self._ocio_config.getDescription()

    def _get_search_paths_from_config(self) -> List[str]:
        """Return the search paths from the OCIO Config file.

        Returns:
            List[str]: A list of search paths.
        """
        return list(self._ocio_config.getSearchPaths())

    def _sanitize_search_paths(self, paths: List[str]) -> None:
        """Sanitize the search paths.

        It will check if the path is a file or a directory and add it to the
        search paths. It will also replace any variables found in the path.

        Arguments:
            paths (List[str]): A list of search paths.
        """
        real_paths = []
        for p in paths:
            computed_path = self._config_path.parent / p
            if computed_path.is_file():
                computed_path = computed_path.parent.resolve()
                real_paths.append(computed_path.as_posix())
            elif computed_path.is_dir():
                computed_path = computed_path.resolve()
                real_paths.append(computed_path.as_posix())

        self.append_search_paths(list(set(real_paths)))

    def _get_absolute_search_paths(self) -> None:
        """Get the absolute search paths from the OCIO Config file."""
        paths = self._get_search_paths_from_config()
        for ocio_transform in self._operators:
            if not hasattr(ocio_transform, "getSrc"):
                continue
            search_path = Path(ocio_transform.getSrc())
            if not search_path.exists():
                self.log.warning(f"Path not found: {search_path}")

            paths.append(ocio_transform.getSrc())

        self._sanitize_search_paths(paths)

    def _change_src_paths_to_names(self) -> None:
        """Change the abs paths to file names only in the OCIO Config file.

        This will also replace any variables found in the path.
        """
        for ocio_transform in self._operators:
            if not hasattr(ocio_transform, "getSrc"):
                continue

            # TODO: this should be probably somewhere else
            if hasattr(ocio_transform, "getCCCId") and ocio_transform.getCCCId():
                ocio_transform.setCCCId(self._swap_variables(ocio_transform.getCCCId()))

            search_path = Path(ocio_transform.getSrc())
            if not search_path.exists():
                self.log.warning(f"Path not found: {search_path}")

            # Change the src path to the name of the search path
            # and replace any found variables
            ocio_transform.setSrc(self._swap_variables(search_path.name))

    def _swap_variables(self, text: str) -> str:
        """Replace variables in a string with their values.

        Arguments:
            text (str): The text to replace variables in.

        Returns:
            str: The text with the variables replaced.
        """
        new_text = text
        for k, v in self._vars.items():
            v = v.replace("\\", "/")
            text = text.replace("\\", "/")
            if v in text:
                new_text = text.replace(v, f"${k}")
                # and stop the loop since it had already found a match
                break

        return new_text

    def load_config_from_file(self, filepath: str) -> None:
        """Load an OCIO Config file from a file.

        Arguments:
            filepath (str): The path to the OCIO Config file.
        """
        self._ocio_config = OCIO.Config.CreateFromFile(filepath)

    def process_config(self) -> None:
        """Process the OCIO Config file.

        This will add the environment variables, description, group transform,
        color space transform, color space, look, display view, active views,
        and validate the OCIO Config object.
        """
        self._ocio_config.setDescription(self._description)
        group_transform = OCIO.GroupTransform(self._operators)
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
            self.target_view_space,
            looks=self.context,
        )

        if not self._views:
            views_value = self._ocio_config.getActiveViews()
        else:
            views_value = ",".join(self._views)

        self._ocio_config.setActiveViews(f"{self.context},{views_value}")

        for env_key, env_value in self._vars.items():
            self._ocio_config.addEnvironmentVar(env_key, env_value)

        # adding all search paths doesn't serialize for some reason
        # so setting the first one and adding the rest
        self._ocio_config.setSearchPath(self._ocio_search_paths[0])
        for i in range(1, len(self._ocio_search_paths)):
            self._ocio_config.addSearchPath(self._ocio_search_paths[i])

        self._ocio_config.validate()

    def write_config(self, dest: str = None) -> str:
        """Write the OCIO Config object to file.

        Arguments:
            dest (str): The destination path to write the OCIO Config file.
        """

        dest = Path(dest).resolve()
        dest.parent.mkdir(exist_ok=True, parents=True)
        with open(dest.as_posix(), "w") as f:
            f.write(self._ocio_config.serialize())

    def _get_search_paths_lines(self) -> List[str]:
        """Add search paths to the OCIO Config file.

        INFO: This is temporary hacky way to add search paths to the
            OCIO since OCIO is ignoring official api methods `addSearchPath()`.

        Arguments:
            paths (List[str]): A list of search paths.
        """
        return [f"  - {path}" for path in self._ocio_search_paths]

    def _get_environment_variables_lines(self) -> List[str]:
        """Add environment variables to the OCIO Config file.

        INFO: This is temporary hacky way to add environment variables to the
            OCIO since OCIO is ignoring official api
            methods `addEnvironmentVar()`.

        Returns:
            List[str]: A list of environment variables.
        """
        return [f"  {k}: {v}" for k, v in self._vars.items()]

    def create_config(self, dest: str = None) -> str:
        """Create an OCIO Config file.

        Arguments:
            dest (str): The destination path to write the OCIO Config file.

        Returns:
            str: The destination path to the OCIO Config file.
        """
        if not dest:
            dest = Path(self.staging_dir, self._ocio_config_name)
        dest = Path(dest).resolve().as_posix()
        self.load_config_from_file(self._config_path.resolve().as_posix())

        self._get_absolute_search_paths()
        self._change_src_paths_to_names()
        self.process_config()
        self.write_config(dest)
        self._dest_path = dest
        return dest

    def get_oiiotool_cmd(self) -> List:
        """Return arguments for the oiiotool command.

        Returns:
            List: The arguments for the oiiotool command.
        """
        return [
            "--colorconfig",
            self._dest_path,
            (f'--ociolook:from="{self.working_space}"' f':to="{self.working_space}"'),
            self.context,
        ]
