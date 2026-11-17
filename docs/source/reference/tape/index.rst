.. currentmodule:: endf_parserpy.tape

tape
====

The ``endf_parserpy.tape`` module provides support for ENDF-6
files that contain several materials, traditionally called
*tapes*. This includes the PENDF tapes produced by
:ref:`processing codes <related_software>`, which repeat the
same material at several temperatures.

The :func:`~endf_parserpy.parse_tape`,
:func:`~endf_parserpy.iter_parse_tape` and
:func:`~endf_parserpy.write_tape` functions (and their
``_file`` variants) read and write such files in terms of
ordinary material dictionaries. The
:class:`~endf_parserpy.EndfFile` class instead provides lazy,
memory-bounded access: the file is indexed on construction
and individual sections are parsed only when accessed.

The :doc:`guide on multi-material files <../../guide/multimaterial_files>`
explains these tools from a practical perspective. The
following sections give a detailed description of the
functions and classes involved:

.. toctree::
   :maxdepth: 1

   tape_functions
   endf_file_class
   material_view_class
   endf_material_path_class
   tape_index_class

Exceptions
----------

All exceptions raised by ``endf-parserpy`` derive from
:class:`~endf_parserpy.EndfParserpyError`. The tape interface
raises the :class:`TapeError` subclasses listed below.

.. autoexception:: endf_parserpy.EndfParserpyError

.. autoexception:: TapeError

.. autoexception:: TapeStructureError

.. autoexception:: AmbiguousMaterialError

.. autoexception:: AmbiguousSectionError

.. autoexception:: SectionParseError

.. autoexception:: SectionRenderError

.. autoexception:: StaleSourceError
