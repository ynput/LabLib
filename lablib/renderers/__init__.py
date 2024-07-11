"""Renderer module combining Operators, Generators and Processors for final image or video file."""

from .basic import BasicRenderer
from .slate_render import SlateRenderer

__all__ = [
    "BasicRenderer",
    "SlateRenderer",
]
