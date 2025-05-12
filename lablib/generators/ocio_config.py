from __future__ import annotations

import os
import logging
import uuid
from typing import Union, Optional
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
        ocio_objects (Optional[list[OCIO.Transform]]): A list of OCIO Transform
            objects.
        working_space (Optional[str]): The working space of the OCIO Config
            file.
        target_display (Optional[str]): The target display space of the OCIO
            Config file. Needs to be set together with target_view.
        target_view (Optional[str]): The target view space of the OCIO
            Config file. For views to be using specific color spaces
            different from working space.
        target_colorspace (Optional[str]): The target colorspace of the OCIO
            Config file.
        views (Optional[list[str]]): A list of views.
        description (Optional[str]): The description of the OCIO Config file.
        staging_dir (Optional[str]): The staging directory of the OCIO Config
            file.
        environment_variables (Optional[dict]): A dictionary of environment
            variables.
        search_paths (Optional[list[str]]): A list of search paths.

    Example:
        >>> from lablib.operators import LUT
        >>> from lablib.generators import OCIOConfigFileGenerator
        >>> lut = LUT(src="src", dst="dst").to_ocio_obj()
        >>> ocio = OCIOConfigFileGenerator(
        ...     context="context",
        ...     config_path="config.ocio",
        ...     ocio_objects=[lut],
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
    _vars: dict[str, str] = {}
    _displays: list[str] = []
    _views: list[str] = []
    _config_path: Path  # OCIO Config file
    _ocio_config: OCIO.Config  # OCIO Config object
    _ocio_search_paths: list[str] = []
    _ocio_config_name: str = "config.ocio"
    _dest_path: str = ""
    _ocio_objects: list[OCIO.Transform] = []

    def __init__(
        self,
        context: str,
        family: str | None = None,
        ocio_objects: list[OCIO.Transform] | None = None,
        config_path: Path | None = None,
        data_space: str | None = None,
        working_space: str | None = None,
        target_display: str | None = None,
        target_view: str | None = None,
        target_colorspace: str | None = None,
        displays: list[str] | None = None,
        views: list[str] | None = None,
        description: str | None = None,
        staging_dir: str | None = None,
        environment_variables: dict | None = None,
        search_paths: list[str] | None = None,
        logger: logging.Logger | None = None,
    ):

        # Context is required
        self.context = context
        self.family = family or "LabLib"
        self.data_space = data_space or "lin_ap0"
        self.working_space = working_space or "lin_ap1"

        if all([target_view, target_display]):
            self.target_view_space = {
                "view": target_view,
                "display": target_display,
            }
        else:
            self.target_view_space = {
                "colorspace": target_colorspace,
            }

        # Default views
        if displays:
            self.set_displays(displays)

        # Default views
        if views:
            self.set_views(views)

        # Default ocio_objects
        if ocio_objects:
            self.set_ocio_objects(ocio_objects)
        else:
            self.clear_ocio_objects()

        # Set OCIO config path and with validation
        if config_path is None:
            env = get_vendored_env()

            if OCIO_env_path := env.get("OCIO", None):
                config_path = Path(OCIO_env_path)
            else:
                raise ValueError("OCIO environment variable not set!")

        if config_path.is_file():
            self._config_path = config_path
            self.set_ocio_config_name(config_path.name)
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

    def set_displays(self, *args: Union[str, list[str]]) -> None:
        """Set the displays for the OCIO Config file.

        Attention:
            This will clear any existing displays.

        Arguments:
            *args: A list of displays.
        """
        self.clear_displays()
        self.append_displays(*args)

    def set_views(self, *args: Union[str, list[str]]) -> None:
        """Set the views for the OCIO Config file.

        Attention:
            This will clear any existing views.

        Arguments:
            *args: A list of views.
        """
        self.clear_views()
        self.append_views(*args)

    def set_search_paths(self, *args: Union[str, list[str]]) -> None:
        self.append_search_paths(*args)

    def set_ocio_objects(self, *args) -> None:
        """Set ocio_objects.

        Attention:
            This will clear any existing ocio_objects.

        Arguments:
            *args: A list of :obj:`OCIO.Transform` objects.
        """
        self.clear_ocio_objects()
        self.append_ocio_objects(*args)

    def set_vars(self, **kwargs) -> None:
        """Set the environment variables for the OCIO Config file.

        Attention:
            This will clear any existing environment variables.

        Arguments:
            **kwargs: A key/value map of environment variables.
        """
        self.clear_vars()
        self.append_vars(**kwargs)

    def clear_ocio_objects(self) -> None:
        """Clear the ocio_objects."""
        self._ocio_objects = []

    def clear_displays(self):
        """Clear the displays."""
        self._displays = []

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

    def append_ocio_objects(self, *args) -> None:
        """Append ocio_objects.

        Arguments:
            *args: A list of :obj:`OCIO.Transform` objects.
        """
        for arg in args:
            if isinstance(arg, list):
                self.append_ocio_objects(*arg)
            else:
                self._ocio_objects.append(arg)

    def append_displays(self, *args: Union[str, list[str]]) -> None:
        """Append displays.

        Arguments:
            *args: A list of displays.
        """
        for arg in args:
            if isinstance(arg, list):
                self.append_displays(*arg)
            else:
                self._displays.append(arg)

    def append_views(self, *args: Union[str, list[str]]) -> None:
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

    def _get_search_paths_from_config(self) -> list[str]:
        """Return the search paths from the OCIO Config file.

        Returns:
            list[str]: A list of search paths.
        """
        return list(self._ocio_config.getSearchPaths())

    def _sanitize_search_paths(self, paths: list[str]) -> None:
        """Sanitize the search paths.

        It will check if the path is a file or a directory and add it to the
        search paths. It will also replace any variables found in the path.

        Arguments:
            paths (list[str]): A list of search paths.
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
        for ocio_transform in self._ocio_objects:
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
        for ocio_transform in self._ocio_objects:
            if not hasattr(ocio_transform, "getSrc"):
                continue

            # TODO: this should be probably somewhere else
            if (
                hasattr(ocio_transform, "getCCCId")
                and ocio_transform.getCCCId()
            ):
                ocio_transform.setCCCId(
                    self._swap_variables(ocio_transform.getCCCId()))

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
        group_transform = OCIO.GroupTransform(self._ocio_objects)
        look_transform = OCIO.ColorSpaceTransform(
            src=self.data_space, dst=self.context
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

        # distribute target view space data
        if (
            self.target_view_space.get("view")
            and self.target_view_space.get("display")
        ):
            # config is > v2
            display = self.target_view_space["display"]
            view = self.target_view_space["view"]
            self._ocio_config.addDisplayView(
                display,
                self.context,
                view,
                looks=self.context,
            )
            if display not in self._displays:
                self._displays.insert(0, display)
        else:
            # config is < v2
            view_colorspace = (
                self.target_view_space.get("colorspace")
                or self.working_space
            )
            self._ocio_config.addDisplayView(
                self._ocio_config.getActiveDisplays().split(",")[0],
                self.context,
                view_colorspace,
                looks=self.context,
            )

        if not self._displays:
            displays_value = self._ocio_config.getActiveDisplays()
        else:
            displays_value = ",".join(self._displays)

        if not self._views:
            views_value = self._ocio_config.getActiveViews()
        else:
            views_value = ",".join(self._views)

        self._ocio_config.setActiveViews(f"{self.context},{views_value}")
        self._ocio_config.setActiveDisplays(f"{displays_value}")

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

    def _get_search_paths_lines(self) -> list[str]:
        """Add search paths to the OCIO Config file.

        INFO: This is temporary hacky way to add search paths to the
            OCIO since OCIO is ignoring official api methods `addSearchPath()`.

        Arguments:
            paths (list[str]): A list of search paths.
        """
        return [f"  - {path}" for path in self._ocio_search_paths]

    def _get_environment_variables_lines(self) -> list[str]:
        """Add environment variables to the OCIO Config file.

        INFO: This is temporary hacky way to add environment variables to the
            OCIO since OCIO is ignoring official api
            methods `addEnvironmentVar()`.

        Returns:
            list[str]: A list of environment variables.
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

    def get_oiiotool_cmd(self) -> list:
        """Return arguments for the oiiotool command.

        Returns:
            list: The arguments for the oiiotool command.
        """
        return [
            "--colorconfig",
            self._dest_path,
            (f'--ociolook:from="{self.working_space}"' f':to="{self.data_space}"'),
            self.context,
        ]
