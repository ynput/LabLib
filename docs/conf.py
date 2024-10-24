import lablib

project = "LabLib"
copyright = "2024, maxpareschi, jakubjezek001, doerp"
author = lablib.__author__
release = lablib.__version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"

todo_include_todos = True

autodoc_typehints = "none"
