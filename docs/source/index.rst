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

   guide/reading_writing_endf
   guide/endf_format_validation
   guide/comparing_endf_files
   guide/format_translation
   guide/endf_plumbing
   guide/creation_endf_scratch
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
and writing `ENDF-6 <https://doi.org/10.2172/1425114>`_ files.
This functionality in combination with Python's
powerful facilities for data handling enables you to
perform various actions on ENDF-6 files, such as:

- Easily access any information
- Modify, delete and insert data
- Perform format validation
- Convert from and to other file formats, such as JSON
- Merge data from various ENDF-6 files into a single one
- Compare ENDF-6 files with meaningful reporting on differences
- Construct ENDF-6 files from scratch


The support for the `ENDF-6 format`_ is comprehensive.
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

   pip install endf-parserpy --upgrade

.. note::

   The package contains C++ source files for
   :ref:`accelerated parsing <accelerated_parsing_and_writing_sec>`.
   If a suitable binary wheel isn't available for your platform,
   an attempt will be made to compile the source files during
   installation, which may take up to ten minutes. If you don't
   need this acceleration, you can disable the compilation attempt by
   setting the environment variable ``INSTALL_ENDF_PARSERPY_CPP``
   to ``no`` before executing the ``pip install`` command.
   Under Linux and MacOS, the command would be

   .. code:: bash

      export INSTALL_ENDF_PARSERPY_CPP=no


   and under Windows

   .. code:: bash

      set INSTALL_ENDF_PARSERPY_CPP=no

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

  - :doc:`guide/reading_writing_endf`
  - :doc:`guide/endf_format_validation`
  - :doc:`guide/comparing_endf_files`
  - :doc:`guide/format_translation`
  - :doc:`guide/endf_plumbing`
  - :doc:`guide/creation_endf_scratch`
  - :doc:`guide/format_extensions`
  - :doc:`guide/working_with_legacy_formats`
  - :doc:`guide/high_level_functionality`
  - :doc:`guide/accelerated_parsing_and_writing`

- Reference

  - :doc:`reference/modules`
  - :doc:`reference/classes`
  - :doc:`reference/endf6_recipes`
  - :doc:`reference/related_software`

