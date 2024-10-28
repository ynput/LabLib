"""Utility functions for the lablib library.

TODO:
    Should we refactor the matrix related functions into a class ``Matrix2D``?
"""

from __future__ import annotations
import os
import math
import uuid
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import opentimelineio as otio


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_vendored_env() -> Dict[str, Any]:
    """Get a prepared copy of the current environment.

    Checks for the presence of ``$OCIO``, ``$LABLIB_OIIO`` and ``$LABLIB_FFMPEG`` and adds them to ``$PATH``.
    If these environment variables are not set, it assumes vendored files to be present in ``./vendor``.

    Hint:
        Run ``.\start.ps1 get-dependencies`` to download the vendored files.

    Returns:
        Dict[str, Any]
    """
    _parts = Path(__file__).parts[:-3]
    vendor_root = Path(*_parts, "vendor")

    env = os.environ.copy()
    if ocio_path := env.get("OCIO"):
        log.debug(f"Using OCIO from {ocio_path}")
    else:
        log.warning("OCIO environment variable not set. Using default.")
        ocio_path = Path(
            vendor_root,
            "ocioconfig",
            "OpenColorIO-Config-ACES-1.2",
            "aces_1.2",
            "config.ocio",
        )
        env["OCIO"] = str(ocio_path)
        log.debug(f"{env['OCIO'] = }")

    if oiio_root := env.get("LABLIB_OIIO"):
        log.debug(f"Using oiiotool from {oiio_root}")
    else:
        log.info("LABLIB_OIIO environment variable not set. Using default.")
        oiio_root = Path(vendor_root, "oiio", "windows")

    if ffmpeg_root := env.get("LABLIB_FFMPEG"):
        log.debug(f"Using ffmpeg from {ffmpeg_root}")
    else:
        log.info("LABLIB_FFMPEG environment variable not set. Using default.")
        ffmpeg_root = Path(
            vendor_root, "ffmpeg", "windows", "ffmpeg-7.0.1-full_build-shared", "bin"
        )

    paths = [Path(p) for p in env["PATH"].split(";")]
    if oiio_root not in paths:
        paths.insert(0, oiio_root)
        log.debug(f"Insert into $PATH {oiio_root = }")
    if ffmpeg_root not in paths:
        log.debug(f"Insert into $PATH {ffmpeg_root = }")
        paths.insert(0, ffmpeg_root)

    env["PATH"] = ";".join([str(p) for p in paths])
    log.debug(f"{env['PATH'] = }")
    return env


def call_cmd(cmd: List[str], timeout=None, retries=0) -> Optional[str]:
    """Run a syscall and return the output and error.

    :param cmd: The command to run.
    :type cmd: List[str]
    """
    out, err, proc = None, None, None
    env = get_vendored_env()

    for retry in range(retries + 1):
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                env=env,
                text=True,
            )
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            log.warning(f"{cmd[0]} timed out: retry {retry+1}/{retries}")
            proc.kill()
            continue

    return out, err


def call_iinfo(filepath: str | Path) -> dict:
    """Get image information using OpenImageIO's iinfo.

    :param filepath: The path to the image file.
    :type filepath: Any[str, Path]
    """
    if isinstance(filepath, str):
        filepath = Path(filepath)
    abspath = str(filepath.resolve())

    cmd = ["oiiotool", "--info", "-v", abspath]
    cmd_out, _ = call_cmd(cmd, timeout=3, retries=3)

    result = {}
    for line in cmd_out.splitlines():
        log.debug(f"oiiotool {line = }")
        if abspath in line and line.find(abspath) < 2:
            vars = line.split(": ")[1].split(",")
            size = vars[0].strip().split("x")
            channels = vars[1].strip().split(" ")
            result["width"] = int(size[0].strip())
            result["height"] = int(size[1].strip())
            result["display_width"] = int(size[0].strip())
            result["display_height"] = int(size[1].strip())
            result["channels"] = int(channels[0].strip())
        if "FramesPerSecond" in line or "framesPerSecond" in line:
            vars = line.split(": ")[1].strip().split(" ")[0].split("/")
            result["fps"] = float(round(float(int(vars[0]) / int(vars[1])), 3))
        if "full/display size" in line:
            size = line.split(": ")[1].split("x")
            result["display_width"] = int(size[0].strip())
            result["display_height"] = int(size[1].strip())
        if "pixel data origin" in line:
            origin = line.split(": ")[1].strip().split(",")
            result["origin_x"] = (int(origin[0].replace("x=", "").strip()),)
            result["origin_y"] = (int(origin[1].replace("y=", "").strip()),)
        if "smpte:TimeCode" in line:
            result["timecode"] = line.split(": ")[1].strip()
        if "PixelAspectRatio" in line:
            result["par"] = float(line.split(": ")[1].strip())

    return result


def call_ffprobe(filepath: str | Path) -> dict:
    """Get video information using FFmpeg's ffprobe."""
    if isinstance(filepath, str):
        filepath = Path(filepath)
    abspath = str(filepath.resolve())
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "format_tags=timecode:stream_tags=timecode:stream=width,height,r_frame_rate,sample_aspect_ratio",
        "-of",
        "default=noprint_wrappers=1",
        abspath,
    ]
    cmd_out, _ = call_cmd(cmd, timeout=3, retries=3)

    result = {}
    for line in cmd_out.splitlines():
        log.debug(f"ffprobe {line = }")
        vars = line.split("=")
        if "width" in vars[0]:
            result["display_width"] = int(vars[1].strip())
        if "height" in vars[0]:
            result["display_height"] = int(vars[1].strip())
        if "r_frame_rate" in vars[0]:
            rate = vars[1].split("/")
            result["fps"] = float(
                round(float(int(rate[0].strip()) / int(rate[1].strip())), 3)
            )
        if "timecode" in line:
            result["timecode"] = vars[1]
        if "sample_aspect_ratio" in line:
            par = vars[1].split(":")
            if vars[1] != "N/A":
                result["par"] = float(int(par[0].strip()) / int(par[1].strip()))
            else:
                result["par"] = 1

    return result


def offset_timecode(tc: str, frame_offset: int = None, fps: float = None) -> str:
    if not frame_offset:
        frame_offset = -1
    if not fps:
        fps = 24.0
    is_drop = not fps.is_integer()
    rationaltime = otio.opentime.from_timecode(tc, fps)
    frames = rationaltime.to_frames(fps) + frame_offset
    computed_rationaltime = otio.opentime.from_frames(frames, fps)
    return otio.opentime.to_timecode(computed_rationaltime, fps, is_drop)


def get_staging_dir() -> str:
    return (
        Path(os.environ.get("TEMP", os.environ["TMP"]), "lablib", str(uuid.uuid4()))
        .resolve()
        .as_posix()
    )


def zero_matrix() -> List[List[float]]:
    return [[0.0] * 3 for _ in range(3)]


def identity_matrix() -> List[List[float]]:
    return translate_matrix([0.0, 0.0])


def translate_matrix(t: List[float]) -> List[List[float]]:
    return [[1.0, 0.0, t[0]], [0.0, 1.0, t[1]], [0.0, 0.0, 1.0]]


def rotate_matrix(r: float) -> List[List[float]]:
    rad = math.radians(r)
    cos = math.cos(rad)
    sin = math.sin(rad)
    return [[cos, -sin, 0.0], [sin, cos, 0.0], [0.0, 0.0, 1.0]]


def scale_matrix(s: List[float]) -> List[List[float]]:
    return [[s[0], 0.0, 0.0], [0.0, s[1], 0.0], [0.0, 0.0, 1.0]]


def mirror_matrix(x: bool = False) -> List[List[float]]:
    direction = [1.0, -1.0] if not x else [-1.0, 1.0]
    return scale_matrix(direction)


def mult_matrix(m1: List[List[float]], m2: List[List[float]]) -> List[List[float]]:
    return [
        [sum(a * b for a, b in zip(m1_row, m2_col)) for m2_col in zip(*m2)]
        for m1_row in m1
    ]


def mult_matrix_vector(m: List[List[float]], v: List[float]) -> List[float]:
    result = [0.0, 0.0, 0.0]
    for i in range(len(m)):
        for j in range(len(v)):
            result[i] += m[i][j] * v[j]
    return result


def flip_matrix(w: float) -> List[List[float]]:
    result = identity_matrix()
    chain = [translate_matrix([w, 0.0]), mirror_matrix(x=True)]
    for m in chain:
        result = mult_matrix(result, m)
    return result


def flop_matrix(h: float) -> List[List[float]]:
    result = identity_matrix()
    chain = [translate_matrix([0.0, h]), mirror_matrix()]
    for m in chain:
        result = mult_matrix(result, m)
    return result


def transpose_matrix(m: List[List[float]]) -> List[List[float]]:
    res = identity_matrix()
    for i in range(len(m)):
        for j in range(len(m[0])):
            res[i][j] = m[j][i]
    return res


def matrix_to_44(m: List[List[float]]) -> List[List[float]]:
    result = m
    result[0].insert(2, 0.0)
    result[1].insert(2, 0.0)
    result[2].insert(2, 0.0)
    result.insert(2, [0.0, 0.0, 1.0, 0.0])
    return result


def matrix_to_list(m: List[List[float]]) -> List[float]:
    result = []
    for i in m:
        for j in i:
            result.append(str(j))
    return result


def matrix_to_csv(m: List[List[float]]) -> str:
    l = []
    for i in m:
        for k in i:
            l.append(str(k))
    return ",".join(l)


def matrix_to_cornerpin(
    m: List[List[float]], w: int, h: int, origin_upperleft: bool = True
) -> List:
    cornerpin = []
    if origin_upperleft:
        corners = [[0, h, 1], [w, h, 1], [0, 0, 1], [w, 0, 1]]
    else:
        corners = [[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]]
    transformed_corners = [mult_matrix_vector(m, corner) for corner in corners]
    transformed_corners = [
        [corner[0] / corner[2], corner[1] / corner[2]] for corner in transformed_corners
    ]
    for corner in transformed_corners:
        cornerpin.extend(corner)
    return cornerpin


def calculate_matrix(
    t: List[float], r: float, s: List[float], c: List[float]
) -> List[List[float]]:
    c_inv = [-c[0], -c[1]]
    center = translate_matrix(c)
    center_inv = translate_matrix(c_inv)
    translate = translate_matrix(t)
    rotate = rotate_matrix(r)
    scale = scale_matrix(s)
    result = mult_matrix(translate, center)
    result = mult_matrix(result, scale)
    result = mult_matrix(result, rotate)
    result = mult_matrix(result, center_inv)
    return result
