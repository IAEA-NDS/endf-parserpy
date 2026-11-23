"""The tape structures of the flavors, one module per flavor.

The module of a flavor has the name of its folder in
``endf_parserpy/endf_recipes`` and defines ``TAPE_STRUCTURE`` (see
:mod:`endf_parserpy.utils.tape_structure`). It is a module of its own so
that the tape structure can be read without importing the recipes of
the flavor (see ``get_tape_structure`` in ``catalogue.py``).
"""
