from __future__ import annotations

import shutil
from typing import List, Dict
from dataclasses import dataclass, field
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from .. import utils


@dataclass
class SlateHtmlProcessor:
    data: Dict = field(default_factory=dict)
    width: int = 1920
    height: int = 1080
    staging_dir: str = None
    slate_template_path: str = None
    source_files: List = field(default_factory=list)
    is_source_linear: bool = True

    def __post_init__(self):
        if not self.staging_dir:
            self.staging_dir = utils.get_staging_dir()
        self._thumbs = []
        self._charts = []
        self._thumb_class_name: str = "thumb"
        self._chart_class_name: str = "chart"
        self._template_staging_dirname: str = "slate_staging"
        self._slate_staged_path: str = None
        self._slate_computed: str = None
        self._slate_base_image_path: str = None
        self._remove_missing_parents: bool = True
        self._slate_base_name = "slate_base.png"
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

    def get_staging_dir(self) -> str:
        return self.staging_dir

    def get_thumb_placeholder(self) -> str:
        self._driver.get(self._slate_staged_path)
        thumb_placeholder = self._driver.find_elements(
            By.CLASS_NAME, self._thumb_class_name
        )[0]
        src = thumb_placeholder.get_attribute("src").replace("file:///", "")
        return src

    def set_slate_base_name(self, name: str) -> None:
        self._slate_base_name = "{}.png".format(name)

    def set_remove_missing_parent(self, remove: bool = True) -> None:
        self._remove_missing_parents = remove

    def set_linear_working_space(self, is_linear: bool) -> None:
        self.is_source_linear = is_linear

    def set_source_files(self, files: List) -> None:
        self.source_files = files

    def set_template_path(self, path: str) -> None:
        self.slate_template_path = Path(path).resolve().as_posix()

    def set_staging_dir(self, path: str) -> None:
        self.staging_dir = Path(path).resolve().as_posix()

    def set_data(self, data: Dict) -> None:
        self.data = data

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def set_thumb_class_name(self, name: str) -> None:
        self._thumb_class_name = name

    def set_chart_class_name(self, name: str) -> None:
        self._chart_class_name = name

    def set_viewport_size(self, width: int, height: int) -> None:
        window_size = self._driver.execute_script(
            "return [window.outerWidth - window.innerWidth + arguments[0],"
            "window.outerHeight - window.innerHeight + arguments[1]];",
            width,
            height,
        )
        self._driver.set_window_size(*window_size)

    def stage_slate(self) -> str:
        if not self.staging_dir:
            raise ValueError("Missing staging dir!")
        if not self.slate_template_path:
            raise ValueError("Missing slate template path!")
        slate_path = Path(self.slate_template_path).resolve()
        slate_dir = slate_path.parent
        slate_name = slate_path.name
        slate_staging_dir = Path(
            self.staging_dir, self._template_staging_dirname
        ).resolve()
        slate_staged_path = Path(slate_staging_dir, slate_name).resolve()
        shutil.rmtree(slate_staging_dir.as_posix(), ignore_errors=True)
        shutil.copytree(src=slate_dir.as_posix(), dst=slate_staging_dir.as_posix())
        self._slate_staged_path = slate_staged_path.as_posix()
        return self._slate_staged_path

    def format_slate(self) -> None:
        if not self.data:
            raise ValueError("Missing subst_data to format template!")
        with open(self._slate_staged_path, "r+") as f:
            formatted_slate = f.read().format_map(utils.format_dict(self.data))
            f.seek(0)
            f.write(formatted_slate)
            f.truncate()

        self._driver.get(self._slate_staged_path)
        elements = self._driver.find_elements(
            By.XPATH,
            "//*[contains(text(),'{}')]".format(utils.format_dict._placeholder),
        )
        for el in elements:
            self._driver.execute_script(
                "var element = arguments[0];\n" "element.style.display = 'none';", el
            )
            if self._remove_missing_parents:
                parent = el.find_element(By.XPATH, "..")
                self._driver.execute_script(
                    "var element = arguments[0];\n" "element.style.display = 'none';",
                    parent,
                )
        with open(self._slate_staged_path, "w") as f:
            f.write(self._driver.page_source)

    def setup_base_slate(self) -> str:
        self._driver.get(self._slate_staged_path)
        self.set_viewport_size(self.width, self.height)
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
            self._thumbs.append(
                utils.ImageInfo(
                    filename=src_path.replace("file:///", ""),
                    origin_x=thumb.location["x"],
                    origin_y=thumb.location["y"],
                    width=thumb.size["width"],
                    height=thumb_height,
                )
            )

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
                self._charts.append(
                    utils.ImageInfo(
                        filename=src_path.replace("file:///", ""),
                        origin_x=chart.location["x"],
                        origin_y=chart.location["y"],
                        width=chart.size["width"],
                        height=chart.size["height"],
                    )
                )

        for chart in charts:
            self._driver.execute_script(
                "var element = arguments[0];"
                "element.parentNode.removeChild(element);",
                chart,
            )

        template_staged_path = Path(self._slate_staged_path).resolve().parent
        slate_base_path = Path(template_staged_path, self._slate_base_name).resolve()
        self._driver.save_screenshot(slate_base_path.as_posix())
        self._driver.quit()
        self._slate_base_image_path = slate_base_path
        return slate_base_path

    def set_thumbnail_sources(self) -> None:
        thumb_steps = int(len(self.source_files) / (len(self._thumbs) + 1))
        for i, t in enumerate(self._thumbs):
            self._thumbs[i].filename = (
                Path(self.source_files[thumb_steps * (i + 1)]).resolve().as_posix()
            )

    def create_base_slate(self) -> None:
        self.stage_slate()
        self.format_slate()
        # thumb_info = utils.read_image_info(self.get_thumb_placeholder())
        # thumb_cmd = [
        #     "oiiotool",
        #     "-i", thumb_info.filename,
        #     "-resize", "{}x{}".format(self.width, self.height),
        #     "-o", thumb_info.filename
        # ]
        # subprocess.run(thumb_cmd)
        self.setup_base_slate()
        self.set_thumbnail_sources()

    def get_oiiotool_cmd(self) -> List:
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
            cmd.extend(["-i", thumb.filename])
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
                    chart.filename,
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
