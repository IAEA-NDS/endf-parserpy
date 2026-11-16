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
   parser = EndfParserCpp(endf_format='endf6-ext@0.19')
   parser = EndfParserPy(endf_format='endf6-ext@0.19')

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

A layout version is named ``<flavor>@<X.Y>`` after the release
``X.Y`` of ``endf-parserpy`` whose layout it keeps, e.g.
``endf6-ext@0.19`` or ``endf6@0.19``. Every release adds the layout
versions of its own number, so the version to pin is the release your
code was developed with. Layout versions exist from 0.19 on.
A layout version does not pin the release of ``endf-parserpy``: fixes
of the parsers reach all versions, and a change of the recipes that
keeps the layout, e.g. one that accepts more deviations from the
ENDF-6 format found in nuclear data libraries, reaches them as well.

The layout version that a flavor currently gives, i.e. the name to
pin, and the flavor whose recipes a name stands for can be queried:

.. code:: python

   from endf_parserpy.endf_recipes import get_layout_version, resolve_endf_flavor
   get_layout_version('endf6-ext')
   # 'endf6-ext@0.19'
   resolve_endf_flavor('endf6-ext@0.19')
   # 'endf6-ext'

As long as a layout version gives the same dictionaries as the latest
flavor, it uses the recipes and the compiled C++ module of the flavor;
it adds nothing to the installation. Several releases with the same
layout share it in this way. When a later release changes the layout
of the flavor, the versions of the earlier releases get one copy of the
previous recipes, and the flavor and the version of the new release
move on to the new layout.


Available layout versions
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Version
     - Introduced in
     - Change relative to the previous version
   * - ``endf6-ext@0.19``
     - 0.19.0
     - First layout version of ``endf6-ext``: the layout of the release 0.19.
   * - ``endf6@0.19``
     - 0.19.0
     - First layout version of ``endf6``: the layout of the release 0.19.

The other flavors (``jendl``, ``pendf``, ``errorr``, ``gendf``) have no layout
versions yet.
