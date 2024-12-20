import os
import pathlib
import shutil

import pytest

from lablib.lib import SequenceInfo
from lablib.generators import SlateHtmlGenerator, SlateFillMode
from lablib.renderers import SlateRenderer, RendererBase


SLATE_TEMPLATE_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "templates",
    "slates",
    "slate_generic",
    "slate_generic.html"
)
DEFAULT_SEQUENCE_PATH = "resources/public/plateMain/v002"
DEFAULT_SEQUENCE = SequenceInfo.scan(DEFAULT_SEQUENCE_PATH)[0]


def _run_slate_renderer(
        generator: SlateHtmlGenerator,
        sequence: SequenceInfo = None,
        output_path: str = None,
    ):
    """ Run a renderer associated with the provided
        generator and source sequence.
    """
    sequence = sequence or DEFAULT_SEQUENCE
    renderer = SlateRenderer(
        generator,
        sequence,
        destination=output_path,
    )

    renderer.render()


@pytest.fixture()
def source_dir(test_staging_dir, request):
    """ Prepare are clean source sequence
        and after each tests.
    """
    # Prepare a temporary directory with a copy of default sequence
    temp_dir = test_staging_dir / request.node.name
    
    # remove folder with content
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # create temp folder again
    temp_dir.mkdir()

    for img in DEFAULT_SEQUENCE.imageinfos:
        new_path = pathlib.Path(temp_dir) / img.filename
        shutil.copy(img.filepath, new_path)

    yield temp_dir


def test_Slaterenderer_missing_keys():
    """ An Exception should raise if any key defined in the 
        template but missing in the provided data.
    """
    with pytest.raises(ValueError):
        generator = SlateHtmlGenerator(
            {"missing": "data"},
            SLATE_TEMPLATE_FILE,
        )
        _run_slate_renderer(generator)


def test_Slaterenderer_unknown_mode():
    """ An Exception should raise if the provided slate mode is unknown.
    """
    with pytest.raises(ValueError):
        generator = SlateHtmlGenerator(
            {"missing": "data"},
            SLATE_TEMPLATE_FILE,
            slate_fill_mode="UNKNOWN MODE"
        )
        _run_slate_renderer(generator)


def test_Slaterenderer_missing_keys_hide(source_dir):
    """ Slate should go through even with missing data
        when using HIDE_WHEN_MISSING mode.
    """
    source_sequence =  SequenceInfo.scan(source_dir)[0]    
    generator = SlateHtmlGenerator(
        {"missing": "data"},
        SLATE_TEMPLATE_FILE,
        slate_fill_mode=SlateFillMode.HIDE_FIELD_WHEN_MISSING
    )
    _run_slate_renderer(generator, sequence=source_sequence)

    edited_sequence = SequenceInfo.scan(source_dir)[0]
    slate_frame = edited_sequence.imageinfos[0]

    assert len(edited_sequence.frames) == len(source_sequence.frames) + 1
    assert slate_frame.width == 1920
    assert slate_frame.height == 1080
    assert slate_frame.timecode == "02:10:04:16"


def test_Slaterenderer_default(source_dir):
    """ Ensure a valid HD slate is generated from default.
    """
    source_sequence =  SequenceInfo.scan(source_dir)[0]
    generator = SlateHtmlGenerator(
        {
            "project_name": "test_project",
            "intent": "test_intent",
            "task_short": "test_task",
            "asset": "test_asset",
            "comment": "some random comment",
            "scope": "test_scope",
            "@version": "123",
        },
        SLATE_TEMPLATE_FILE,
    )
    _run_slate_renderer(generator, sequence=source_sequence)

    edited_sequence = SequenceInfo.scan(source_dir)[0]
    slate_frame = edited_sequence.imageinfos[0]

    assert len(edited_sequence.frames) == len(source_sequence.frames) + 1
    assert slate_frame.width == 1920
    assert slate_frame.height == 1080
    assert slate_frame.timecode == "02:10:04:16"


def test_Slaterenderer_4K(source_dir):
    """ Ensure a valid 4K slate.
    """
    source_sequence =  SequenceInfo.scan(source_dir)[0]
    generator = SlateHtmlGenerator(
        {
            "project_name": "test_project",
            "intent": "test_intent",
            "task_short": "test_task",
            "asset": "test_asset",
            "comment": "some random comment",
            "scope": "test_scope",
            "@version": "123",
        },
        SLATE_TEMPLATE_FILE,
        width=4096,
        height=2048,
    )
    _run_slate_renderer(generator, sequence=source_sequence)

    edited_sequence = SequenceInfo.scan(source_dir)[0]
    slate_frame = edited_sequence.imageinfos[0]

    assert len(edited_sequence.frames) == len(source_sequence.frames) + 1
    assert slate_frame.width == 4096
    assert slate_frame.height == 2048
    assert slate_frame.timecode == "02:10:04:16"


def test_Slaterenderer_explicit_output(source_dir):
    """ Ensure a valid HD slate can be generated to a predefined output.
    """
    expected_output = pathlib.Path(source_dir) / "output.exr"
    generator = SlateHtmlGenerator(
        {
            "project_name": "test_project",
            "intent": "test_intent",
            "task_short": "test_task",
            "asset": "test_asset",
            "comment": "some random comment",
            "scope": "test_scope",
            "@version": "123",
        },
        SLATE_TEMPLATE_FILE,
    )
    _run_slate_renderer(generator, output_path=expected_output)

    assert os.path.exists(expected_output)

def test_inheritance_SlateRenderer():
    """Ensure SlateRenderer inherits from RendererBase
    """
    assert issubclass(SlateRenderer, RendererBase)
