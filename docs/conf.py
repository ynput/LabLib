import lablib

project = "LabLib"
copyright = "2024, maxpareschi, jakubjezek001, doerp"
author = lablib.__author__
release = lablib.__version__

extensions = ["sphinx.ext.autodoc", "sphinx.ext.todo", "sphinx.ext.napoleon"]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"

todo_include_todos = True
