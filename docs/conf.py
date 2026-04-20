# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the project source directories to the path for autodoc
sys.path.insert(0, os.path.abspath('../controller_components'))
sys.path.insert(0, os.path.abspath('../controller_components/ai_nn_controller'))
sys.path.insert(0, os.path.abspath('../controller_components/register'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'ai_nn_controller'
copyright = '2025, Merim Dzaferagic'
author = 'Merim Dzaferagic'
release = '1.0.0'
version = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',           # Auto-generate docs from docstrings
    'sphinx.ext.viewcode',          # Add links to source code
    'sphinx.ext.napoleon',          # Support for Google/NumPy style docstrings
    'sphinx.ext.intersphinx',       # Link to other project docs
    'sphinx.ext.todo',              # Support for TODO items
    'sphinx.ext.coverage',          # Check documentation coverage
    'sphinx.ext.graphviz',          # Support for Graphviz diagrams
    'myst_parser',                  # Support for Markdown files
]

# MyST parser configuration for Markdown support
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]

# Templates path
templates_path = ['_templates']

# Patterns to exclude from documentation
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Source file extensions
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master document
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options for Read the Docs theme
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}

# Custom CSS
html_css_files = [
    'custom.css',
]

# Logo and favicon (create these files in _static if you have them)
# html_logo = '_static/logo.png'
# html_favicon = '_static/favicon.ico'

# -- Options for autodoc -----------------------------------------------------

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
}

# Mock imports for modules that may not be installed
autodoc_mock_imports = [
    'zmq',
    'redis',
    'fastapi',
    'uvicorn',
    'pydantic',
    'sse_starlette',
]

# -- Options for intersphinx -------------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'fastapi': ('https://fastapi.tiangolo.com/', None),
}

# -- Options for TODO extension ----------------------------------------------

todo_include_todos = True

# -- Napoleon settings for Google-style docstrings ---------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None
