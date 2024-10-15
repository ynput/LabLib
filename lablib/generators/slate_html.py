from __future__ import annotations

import datetime
import os
import shutil
from typing import List, Dict
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from ..lib import utils, imageio


class SlateHtmlGenerator:
    """Class to generate a slate from a template.

    Attributes:
        slate_template_path: The path to the template.
        data: A dictionary containing the data to be formatted in the template.
        width: The width of the slate.
        height: The height of the slate.
        staging_dir: The directory where the slate will be staged.
        source_files: A list of source files.
        is_source_linear: A boolean to set whether the source files are linear.

    Raises:
        ValueError: When the provided slate template path is invalid.
    """
    def __init__(
        self,
        data: Dict,
        slate_template_path: str,
        width: int = None,
        height: int = None,
        staging_dir: str = None,
        source_files: List = None,
        is_source_linear: bool = None
    ):
        self.data = data
        self.width = width or 1920
        self.height = height or 1080
        self._staging_dir =  staging_dir or utils.get_staging_dir()
        self.source_files = source_files or []
        self.is_source_linear = is_source_linear if is_source_linear is not None else True

        try:
            slate_template_path = slate_template_path
            self._slate_template_path = Path(slate_template_path).resolve().as_posix()

        except Exception as error:
            raise ValueError(
                "Could not load slate template"
                f" from {slate_template_path}"
            ) from error

        self._thumbs = []
        self._charts = []
        self._thumb_class_name: str = "thumb"
        self._chart_class_name: str = "chart"
        self._template_staging_dirname: str = "slate_staging"
        self._slate_staged_path: str = None
        self._slate_computed: str = None
        self._slate_base_image_path: str = None
        self.remove_missing_parents: bool = True
        self.slate_base_name = "slate_base"
        self.slate_extension = "png"

        options = Options()
        # THIS WILL NEED TO BE SWITCHED TO NEW MODE, BUT THERE ARE BUGS.
        # WE SHOULD BE FINE FOR A COUPLE OF YEARS UNTIL DEPRECATION.
        # --headless=new works only with 100% display size,
        # if you use a different display scaling (for hidpi monitors)
        # the resizing of the screenshot will not work.
        options.add_argument("--headless")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--show-capture=no")
        options.add_argument("--log-level=OFF")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self._driver = webdriver.Chrome(options=options)

    @property
    def staging_dir(self) -> str:
        """Return the path to the staging directory.

        Returns:
            str: The path to the staging directory.
        """
        return self._staging_dir

    @property
    def slate_filename(self) -> str:
        """Return the slate filename.

        Returns:
            str: The slate filename.
        """
        return f"{self.slate_base_name}.{self.slate_extension}"

    @property
    def template_path(self):
        """Return the slate template path.

        Returns:
            str: The slate template path.
        """
        return self._slate_template_path

    @template_path.setter
    def template_path(self, path: str) -> None:
        """Set the slate template path.

        Arguments:
            path (str): The new path to the slate template path.    
        """
        self._slate_template_path = Path(path).resolve().as_posix()

    def set_size(self, width: int, height: int) -> None:
        """Set the slate resolution.

        Args:
            width (int): The width of the slate.
            height (int): The height of the slate.
        """
        self.width = width
        self.height = height

    def _stage_slate(self) -> str:
        """Prepare staging content for slate generation.

        Returns:
            str: The path to the prepped staging directory.

        Raises:
            ValueError: When the provided template path is invalid.
        """
        slate_path = Path(self.template_path).resolve()
        slate_dir = slate_path.parent
        slate_name = slate_path.name
        slate_staging_dir = Path(
            self.staging_dir, self._template_staging_dirname
        ).resolve()
        slate_staged_path = Path(slate_staging_dir, slate_name).resolve()

        # Clear staging path directory
        shutil.rmtree(slate_staging_dir.as_posix(), ignore_errors=True)

        # Copy over template root directory
        shutil.copytree(src=slate_dir.as_posix(), dst=slate_staging_dir.as_posix())

        self._slate_staged_path = slate_staged_path.as_posix()
        return self._slate_staged_path

    def _format_slate(self) -> None:
        """Format template with generator data values.

        Raises:
            ValueError: When the provided data is incomplete.
        """
        now = datetime.datetime.now()
        default_data = {
            "dd": now.day,
            "mmm": now.month,
            "yyyy": now.year,
            "frame_start": self.source_files[0].frame_number,
            "frame_end": self.source_files[-1].frame_number,
            "resolution_width": self.width,
            "resolution_height": self.height,
        }
        formatted_dict = default_data.copy()
        formatted_dict.update(self.data) # overides with provided data.

        # Read template content
        with open(self._slate_staged_path, "r+") as f:
            template_content = f.read()

        # Attempt to replace/format template with content.
        try:
            content = template_content.format(**formatted_dict)
        except KeyError as error:
            raise ValueError(
                f"Key mismatch, cannot fill template: {error}"
            ) from error

        # Override template file content with formatted data.
        with open(self._slate_staged_path, "w+") as f:
            f.seek(0)
            f.write(content)
            f.truncate()

        self._driver.get(self._slate_staged_path)

        # TODO: Revisit this.
        # Currently this function will fail with a KeyError
        # if any data expected by the template is missing from
        # the data dict.
        #
        # The code below turns this into a silent fails where
        # missig fields are hidden from the resulting slate.
#        elements = self._driver.find_elements(
#            By.XPATH,
#            "//*[contains(text(),'{}')]".format("**MISSING"),
#        )
#        for el in elements:
#            self._driver.execute_script(
#                "var element = arguments[0];\n" "element.style.display = 'none';", el
#            )
#            if self._remove_missing_parents:
#                parent = el.find_element(By.XPATH, "..")
#                self._driver.execute_script(
#                    "var element = arguments[0];\n" "element.style.display = 'none';",
#                    parent,
#                )
        with open(self._slate_staged_path, "w") as f:
            f.write(self._driver.page_source)

    def _setup_base_slate(self) -> str:
        """Setup the slate template in selenium.

        Returns:
            str: The slate final destination path.
        """
        self._driver.get(self._slate_staged_path)

        window_size = self._driver.execute_script(
            "return [window.outerWidth - window.innerWidth + arguments[0],"
            "window.outerHeight - window.innerHeight + arguments[1]];",
            self.width,
            self.height,
        )
        self._driver.set_window_size(*window_size)

        thumbs = self._driver.find_elements(By.CLASS_NAME, self._thumb_class_name)
        for thumb in thumbs:
            src_path = thumb.get_attribute("src")
            if not src_path:
                continue

            aspect_ratio = self.width / self.height
            thumb_height = int(thumb.size["width"] / aspect_ratio)
            self._driver.execute_script(
                "var element = arguments[0];" "element.style.height = '{}px'".format(
                    thumb_height
                ),
                thumb,
            )

            path = src_path.replace("file:///", "")
            thumb_image = imageio.ImageInfo(path=path)
            thumb_image.origin_x = thumb.location["x"]
            thumb_image.origin_y = thumb.location["y"]
            thumb_image.width = thumb.size["width"]
            thumb_image.height = thumb_height
            self._thumbs.append(thumb_image)

        for thumb in thumbs:
            self._driver.execute_script(
                "var element = arguments[0];"
                "element.parentNode.removeChild(element);",
                thumb,
            )

        charts = self._driver.find_elements(By.CLASS_NAME, self._chart_class_name)
        for chart in charts:
            src_path = chart.get_attribute("src")
            if src_path:
                path=src_path.replace("file:///", "")
                chart_image = imageio.ImageInfo(path=path)
                chart_image.origin_x = chart.location["x"]
                chart_image.origin_y = chart.location["y"]
                chart_image.width = chart.size["width"]
                chart_image.height = chart.size["height"]
                self._charts.append(chart_image)

        for chart in charts:
            self._driver.execute_script(
                "var element = arguments[0];"
                "element.parentNode.removeChild(element);",
                chart,
            )

        template_staged_path = Path(self._slate_staged_path).resolve().parent
        slate_base_path = Path(template_staged_path, self.slate_filename).resolve()
        self._driver.save_screenshot(slate_base_path.as_posix())
        self._driver.quit()
        self._slate_base_image_path = slate_base_path
        return slate_base_path

    def _set_thumbnail_sources(self) -> None:
        """Set thumbnail sources before processing slate.
        """
        thumb_steps = int(len(self.source_files) / (len(self._thumbs) + 1))
        for i, t in enumerate(self._thumbs):
            src_file = self.source_files[thumb_steps * (i + 1)]
            src_file_path = src_file.filepath
            self._thumbs[i].path = (
                Path(src_file_path).resolve().as_posix()
            )

    def create_base_slate(self) -> None:
        """Prepare and create base slate. 
        """
        self._stage_slate()
        self._format_slate()
        self._setup_base_slate()
        self._set_thumbnail_sources()

    def get_oiiotool_cmd(self) -> List:
        """ Get the oiiotool command to run for slate generation.

        Returns:
            list: The oiiotool command to run.
        """
        label = "base"
        cmd = [
            "-i",
            Path(self._slate_base_image_path).resolve().as_posix(),
            "--colorconvert",
            "sRGB",
            "linear",
            "--ch",
            "R,G,B,A=1.0",
            "--label",
            "slate",
            "--create",
            "{}x{}".format(self.width, self.height),
            "4",
            "--ch",
            "R,G,B,A=0.0",
            "--label",
            label,
        ]
        for thumb in self._thumbs:
            cmd.extend(["-i", thumb.path])
            if not self.is_source_linear:
                cmd.extend(["--colorconvert", "sRGB", "linear"])

            cmd.extend(
                [
                    "--ch",
                    "R,G,B,A=1.0",
                    "--resample",
                    "{}x{}+{}+{}".format(
                        thumb.width, thumb.height, thumb.origin_x, thumb.origin_y
                    ),
                    label,
                    "--over",
                    "--label",
                    "imgs",
                ]
            )
            label = "imgs"

        for chart in self._charts:
            cmd.extend(
                [
                    "-i",
                    chart.path,
                    "--colorconvert",
                    "sRGB",
                    "linear",
                    "--ch",
                    "R,G,B,A=1.0",
                    "--resample",
                    "{}x{}+{}+{}".format(
                        chart.width, chart.height, chart.origin_x, chart.origin_y
                    ),
                    "imgs",
                    "--over",
                    "--label",
                    "imgs",
                ]
            )

        cmd.extend(
            [
                "slate",
                "--over",
                "--label",
                "complete_slate",
            ]
        )
        if not self.is_source_linear:
            cmd.extend(
                [
                    "--colorconvert",
                    "linear",
                    "sRGB",
                ]
            )

        return cmd
