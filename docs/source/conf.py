# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))

project = "endf-parserpy"
copyright = "2022-2024, International Atomic Energy Agency"
author = "Georg Schnabel"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx_design",
    "myst_parser",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("http://docs.scipy.org/doc/numpy/", None),
}

extlinks = {
    "endf6manpage": (
        "https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf#page=%s",
        "ENDF-6 formats manual (page  %s)",
    ),
    "endf6manshort": (
        "https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf#page=%s",
        "manual page %s",
    ),
    "endf6recipe": (
        "https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf6/endf_recipe_%s.py",
        "ENDF-6 recipe (%s)",
    ),
}

templates_path = ["_templates"]
exclude_patterns = []
autoclass_content = "both"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

napoleon_use_rtype = True

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

master_doc = "index"


# hack to make external links open in new tab/window
# taken from https://stackoverflow.com/a/61669375

from sphinx.writers.html import HTMLTranslator
from docutils import nodes
from docutils.nodes import Element


class PatchedHTMLTranslator(HTMLTranslator):

    def visit_reference(self, node: Element) -> None:
        atts = {"class": "reference"}
        if node.get("internal") or "refuri" not in node:
            atts["class"] += " internal"
        else:
            atts["class"] += " external"
            # ---------------------------------------------------------
            # Customize behavior (open in new tab, secure linking site)
            atts["target"] = "_blank"
            atts["rel"] = "noopener noreferrer"
            # ---------------------------------------------------------
        if "refuri" in node:
            atts["href"] = node["refuri"] or "#"
            if self.settings.cloak_email_addresses and atts["href"].startswith(
                "mailto:"
            ):
                atts["href"] = self.cloak_mailto(atts["href"])
                self.in_mailto = True
        else:
            assert (
                "refid" in node
            ), 'References must have "refuri" or "refid" attribute.'
            atts["href"] = "#" + node["refid"]
        if not isinstance(node.parent, nodes.TextElement):
            assert len(node) == 1 and isinstance(node[0], nodes.image)
            atts["class"] += " image-reference"
        if "reftitle" in node:
            atts["title"] = node["reftitle"]
        if "target" in node:
            atts["target"] = node["target"]
        self.body.append(self.starttag(node, "a", "", **atts))

        if node.get("secnumber"):
            self.body.append(
                ("%s" + self.secnumber_suffix) % ".".join(map(str, node["secnumber"]))
            )


def setup(app):
    app.set_translator("html", PatchedHTMLTranslator)
