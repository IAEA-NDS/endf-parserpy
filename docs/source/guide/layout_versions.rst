.. _layout_versions_sec:

Layout Versions of Format Flavors
=================================

The dictionaries produced by the parsers have the *layout* given
by the :ref:`ENDF recipes <endf6_recipe_sec>` of the
:ref:`format flavor <pendf_and_format_flavors>` selected by the
``endf_format`` argument: the names of the keys, their nesting,
the shape of the arrays and the meaning of the values.
A change of the recipes in a new release of ``endf-parserpy`` can
change this layout, e.g. rename a key, and then break code that
reads or creates these dictionaries.

To keep the layout that your code was developed against, pass a
*layout version* of the flavor instead of its name:

.. code:: python

   from endf_parserpy import EndfParserCpp, EndfParserPy
   parser = EndfParserCpp(endf_format='endf6-ext-v1')
   parser = EndfParserPy(endf_format='endf6-ext-v1')

The same names can be given to :class:`~endf_parserpy.EndfParserFactory`
and to the ``--endf_format`` option of the
:ref:`command-line interface <command_line_interface>`.
The bare name of a flavor, e.g. ``endf6-ext``, always gives the latest
layout. It is the right choice for interactive work and for code that
is updated together with ``endf-parserpy``. A layout version is
useful for code that is kept for a longer time, e.g. a processing
pipeline, that should continue to work after an upgrade.


Naming
------

A layout version is named ``<flavor>-v<N>`` with a positive integer
``N``, e.g. ``endf6-ext-v1`` or ``endf6-v1``. ``N`` is increased only
by a change of the layout. A change of the recipes that keeps the
layout, e.g. one that accepts more deviations from the ENDF-6 format
found in nuclear data libraries, does not increase it.
A layout version does not pin the release of ``endf-parserpy``: fixes
of the parsers reach all versions.

The layout version that a flavor currently gives, i.e. the name to
pin, and the flavor whose recipes a name stands for can be queried:

.. code:: python

   from endf_parserpy.endf_recipes import get_layout_version, resolve_endf_flavor
   get_layout_version('endf6-ext')
   # 'endf6-ext-v1'
   resolve_endf_flavor('endf6-ext-v1')
   # 'endf6-ext'

As long as a layout version gives the same dictionaries as the latest
flavor, it uses the recipes and the compiled C++ module of the flavor;
it adds nothing to the installation. When a later release changes the
layout of the flavor, the version gets a copy of the previous recipes,
and the flavor and a new version with the next number move on to the
new layout.


Available layout versions
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Version
     - Introduced in
     - Change relative to the previous version
   * - ``endf6-ext-v1``
     - 0.19.0
     - First layout version of ``endf6-ext``: the layout of this release.
   * - ``endf6-v1``
     - 0.19.0
     - First layout version of ``endf6``: the layout of this release.

The other flavors (``jendl``, ``pendf``, ``errorr``) have no layout
versions yet.
