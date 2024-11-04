""" Base renderer.
"""
from abc import ABC, abstractmethod


class RendererBase(ABC):
    """Base class for all renderers.

    This should not be instanciated directly.
    """

    @abstractmethod
    def render(self, debug=False) -> None:
        """Trigger the render process.

        Arguments:
            debug (Optional[bool]): Whether to increase log verbosity.
        """
