import os
import pathlib
import tempfile
import shutil

import pytest

from lablib.lib import SequenceInfo
from lablib.generators import SlateHtmlGenerator
from lablib.renderers import SlateRenderer


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
def source_dir():
    """ Prepare are clean source sequence
        and after each tests.
    """
    # Prepare a temporary directory with a copy of default sequence
    temp_dir = tempfile.mkdtemp()
    for img in DEFAULT_SEQUENCE.frames:
        new_path = pathlib.Path(temp_dir) / img.filename

        try:
            new_path.symlink_to(img.path)
        except OSError:
            shutil.copy(img.filepath, new_path)

    yield temp_dir

    # Remove all temporary directory content.
    shutil.rmtree(temp_dir)

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


def test_Slaterenderer_default(source_dir):
    """ Ensure a valid HD slate is generated from default.
    """
    source_sequence =  SequenceInfo.scan(source_dir)[0]
    generator = SlateHtmlGenerator(
        {
            "project": {"name": "test_project"},
            "intent": {"value": "test_intent"},            
            "task": {"short": "test_task"},
            "asset": "test_asset",
            "comment": "some random comment",
            "scope": "test_scope",
            "@version": "123",
        },
        SLATE_TEMPLATE_FILE,
    )
    _run_slate_renderer(generator, sequence=source_sequence)

    edited_sequence = SequenceInfo.scan(source_dir)[0]
    slate_frame = edited_sequence.frames[0]

    assert len(edited_sequence.frames) == len(source_sequence.frames) + 1
    assert slate_frame.width == 1920
    assert slate_frame.height == 1080


def test_Slaterenderer_4K(source_dir):
    """ Ensure a valid 4K slate.
    """
    source_sequence =  SequenceInfo.scan(source_dir)[0]
    generator = SlateHtmlGenerator(
        {
            "project": {"name": "test_project"},
            "intent": {"value": "test_intent"},            
            "task": {"short": "test_task"},
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
    slate_frame = edited_sequence.frames[0]

    assert len(edited_sequence.frames) == len(source_sequence.frames) + 1
    assert slate_frame.width == 4096
    assert slate_frame.height == 2048


def test_Slaterenderer_explicit_output(source_dir):
    """ Ensure a valid HD slate can be generated to a predefined output.
    """
    expected_output = pathlib.Path(source_dir) / "output.exr"
    generator = SlateHtmlGenerator(
        {
            "project": {"name": "test_project"},
            "intent": {"value": "test_intent"},            
            "task": {"short": "test_task"},
            "asset": "test_asset",
            "comment": "some random comment",
            "scope": "test_scope",
            "@version": "123",
        },
        SLATE_TEMPLATE_FILE,
    )
    _run_slate_renderer(generator, output_path=expected_output)

    assert os.path.exists(expected_output)
