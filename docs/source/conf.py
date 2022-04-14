# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from pathlib import Path

sys.path.insert(0, Path(__file__).parents[2].resolve().as_posix())


# -- Project information -----------------------------------------------------

project = "run-logger"
copyright = "2022, Ethan Brooks"
author = "Ethan Brooks"

# The full version, including alpha/beta/rc tags

import importlib.metadata

release = importlib.metadata.version("run-logger")


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    # "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    # "sphinxext.opengraph",
    "sphinx_copybutton",
    "myst_parser",
]

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

autodoc_typehints = "none"

# Make sure the target is unique
autosectionlabel_prefix_document = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

html_theme = "sphinx_book_theme"
html_theme_options = {
    "repository_url": "https://github.com/run-tracker/run-logger",
    "use_repository_button": True,
    "home_page_in_toc": True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]
