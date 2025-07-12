.. toctree::
   :maxdepth: 1
   :caption: Overview
   :hidden:

   overview/philosophy
   overview/mapping_endf_recipes
   overview/endf_navigation

.. toctree::
   :maxdepth: 1
   :caption: Tutorials & Guides
   :hidden:

   guide/getting_started
   guide/python_and_cpp_parser
   guide/command_line_interface
   guide/reading_writing_endf
   guide/endf_format_validation
   guide/comparing_endf_files
   guide/format_translation
   guide/endf_plumbing
   guide/creation_endf_scratch
   guide/pendf_and_format_flavors
   guide/format_extensions
   guide/working_with_legacy_formats
   guide/high_level_functionality
   guide/perfect_precision
   guide/arrays_as_list
   guide/accelerated_parsing_and_writing

.. toctree::
   :maxdepth: 1
   :caption: Reference
   :hidden:

   reference/modules
   reference/classes
   reference/endf6_recipes
   reference/related_software


.. _ENDF-6 format: https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf

Welcome to endf-parserpy's documentation!
=========================================

endf-parserpy is a Python package for reading
and writing `ENDF <https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf>`_ files.
This functionality in combination with Python's
powerful facilities for data handling enables you to
perform various actions on ENDF files, such as:

- Easily access any information
- Modify, delete and insert data
- Perform format validation
- Convert from and to other file formats, such as JSON
- Merge data from various ENDF-6 files into a single one
- Compare ENDF-6 files with meaningful reporting on differences
- Construct ENDF-6 files from scratch


Many of these actions can be performed via the command line.
The support for the `ENDF-6 format`_ is comprehensive and
some special NJOY output formats are also supported.
The package has been tested on the various sublibraries
of the major nuclear data libraries, such as
`ENDF/B <https://www.nndc.bnl.gov/endf/>`_,
`JEFF <https://www.oecd-nea.org/dbdata/jeff/>`_,
and `JENDL <https://wwwndc.jaea.go.jp/jendl/jendl.html>`_.
Note that the package does not support several materials
in a single ENDF-6 file.


Install endf-parserpy
---------------------

.. code:: bash

   python -m pip install endf-parserpy --upgrade


.. note::

   :ref:`Accelerated parsing <accelerated_parsing_and_writing_sec>`
   relies on compiled C++ code.
   If a suitable binary wheel isn't available for your platform,
   an attempt will be made to compile the C++ source files during
   installation, which may take up to ten minutes. You may reduce
   the optimization level to significantly reduce the compilation
   time at the expense of slower parsing by setting the
   ``INSTALL_ENDF_PARSERPY_CPP_OPTIM`` environment variable with
   a value between 0 (no optimization) to 3 (maximal optimization).
   The value 1 seems to be a good trade-off between compilation time
   and achievable parsing and writing speed.
   Under Linux and MacOS, the command would be

   .. code:: bash

      export INSTALL_ENDF_PARSERPY_CPP_OPTIM=1


   and under Windows

   .. code:: bash

      set INSTALL_ENDF_PARSERPY_CPP_OPTIM=1

   If you want to disable the compilation of the C++ modules,
   you can set the environment variable ``INSTALL_ENDF_PARSERPY_CPP``
   to ``no`` before executing the ``pip install`` command.

.. note::

   The package is still evolving and will be
   extended with convenience functions to enhance
   the user experience. You can always check for updated versions
   `on PyPI <https://pypi.org/project/endf-parserpy/>`_.


Resources
---------

- :doc:`overview/philosophy`
- :doc:`overview/mapping_endf_recipes`
- :doc:`overview/endf_navigation`
- Guides

  - :doc:`guide/getting_started`
  - :doc:`guide/python_and_cpp_parser`
  - :doc:`guide/command_line_interface`
  - :doc:`guide/reading_writing_endf`
  - :doc:`guide/endf_format_validation`
  - :doc:`guide/comparing_endf_files`
  - :doc:`guide/format_translation`
  - :doc:`guide/endf_plumbing`
  - :doc:`guide/creation_endf_scratch`
  - :doc:`guide/pendf_and_format_flavors`
  - :doc:`guide/format_extensions`
  - :doc:`guide/working_with_legacy_formats`
  - :doc:`guide/high_level_functionality`
  - :doc:`guide/perfect_precision`
  - :doc:`guide/arrays_as_list`
  - :doc:`guide/accelerated_parsing_and_writing`

- Reference

  - :doc:`reference/modules`
  - :doc:`reference/classes`
  - :doc:`reference/endf6_recipes`
  - :doc:`reference/related_software`

