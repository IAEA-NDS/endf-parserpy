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
   guide/multimaterial_files
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


.. _ENDF-6 format: https://doi.org/10.2172/2007538

Welcome to endf-parserpy's documentation!
=========================================

endf-parserpy is a Python package for reading
and writing `ENDF-6 <https://doi.org/10.2172/2007538>`_ files.
This functionality in combination with Python's
powerful facilities for data handling enables you to
perform various actions on ENDF-6 files, such as:

- Access any information easily
- Modify, delete, and insert data
- Perform format validation
- Convert to and from other file formats, such as JSON
- Merge data from multiple ENDF-6 files into a single file
- Read and write files containing multiple materials (tapes)
- Compare ENDF-6 files and generate meaningful reports of their differences
- Construct ENDF-6 files from scratch


Many of these actions can also be performed from the command line
through the ``endf-cli`` tool (see :doc:`guide/command_line_interface`).
The support for the `ENDF-6 format`_ is comprehensive and
some special NJOY2016 output formats are also supported.
The package has been tested on the various sublibraries
of the major nuclear data libraries, such as
`ENDF/B <https://www.nndc.bnl.gov/endf/>`_,
`JEFF <https://www.oecd-nea.org/dbdata/jeff/>`_,
and `JENDL <https://wwwndc.jaea.go.jp/jendl/jendl.html>`_.
Files that bundle several materials, including PENDF
tapes, are supported as well; see the guide on
:doc:`multi-material files <guide/multimaterial_files>`.
Parsing and writing have been extensively optimized; the C++
backend processes ENDF-6 data at rates of up to several hundred
megabytes per second (see
:ref:`accelerated parsing and writing <accelerated_parsing_and_writing_sec>`).


Install endf-parserpy
---------------------

.. code:: bash

   python -m pip install endf-parserpy --upgrade


.. note::

   :ref:`Accelerated parsing <accelerated_parsing_and_writing_sec>`
   relies on compiled C++ code.
   If a suitable binary wheel isn't available for your platform,
   an attempt will be made to compile the C++ source files during
   installation, which can take up to ten minutes.
   The default optimization level aims to strike a balance between
   compile time and parsing speed. Power users can alter the
   optimization flag by setting the ``INSTALL_ENDF_PARSERPY_CPP_OPTIM``
   environment variable before installation. For instance, under Linux and macOS,
   where the compiler is usually GCC or Clang, you could disable all optimizations by:

   .. code:: bash

      export INSTALL_ENDF_PARSERPY_CPP_OPTIM="-O0"

   Under Windows (assuming Microsoft Visual C++), you can do:

   .. code:: bash

      set INSTALL_ENDF_PARSERPY_CPP_OPTIM=/Od

   If you want to disable the compilation of the C++ modules entirely,
   you can set the environment variable ``INSTALL_ENDF_PARSERPY_CPP``
   to ``no`` before executing the ``pip install`` command.

   Two further variables tune the compilation itself:
   ``INSTALL_ENDF_PARSERPY_NUM_BUILD_JOBS`` sets the number of parallel
   compile jobs (default: all CPU cores; ``1`` disables parallel
   compilation), and ``INSTALL_ENDF_PARSERPY_NUM_SHARED_CHUNKS`` sets
   how many translation units the C++ code shared between the format
   flavors is split into for faster parallel builds (default: up to 8;
   ``1`` emits the single ``_shared.cpp`` as found in the repository).
   At runtime, the environment variable ``ENDF_PARSERPY_CPP_BULK_BODIES``
   selects how the C++ modules read the float fields of the bodies of
   TAB1 and LIST records (see :ref:`cpp_bulk_bodies_sec`).


.. note::

   The :doc:`multi-material file interface <guide/multimaterial_files>`
   indexes tapes with a structural scan that is faster when
   `NumPy <https://numpy.org/>`_ is available, and NumPy also enables
   ``array_type="numpy"``, the fastest parsing mode. To install this
   optional dependency, add the ``fast`` extra:

   .. code:: bash

      python -m pip install "endf-parserpy[fast]"

   Without NumPy a pure-Python fallback is used, so the
   dependency is not required.


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
  - :doc:`guide/multimaterial_files`
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


Citation and acknowledgments
----------------------------

If you want to cite this package,
please use the following reference:

.. code:: text

   G. Schnabel, D. L. Aldama, R. Capote, "How to explain ENDF-6 to computers: A formal ENDF format description language", arXiv:2312.08249, DOI:10.48550/arXiv.2312.08249

This code is distributed under the MIT license augmented
by an IAEA clause, see the accompanying license file for more information.
Copyright (c) 2022-2026 International Atomic Energy Agency (IAEA).

Daniel Lopez Aldama made significant contributions
to the development of this package. He debugged the
ENDF-6 recipe files and helped in numerous discussions
to convey a good understanding of the technical details of
the ENDF-6 format that enabled the creation of this package.

endf-parserpy, including the formal recipe language, the parser
architecture and the compiler that translates recipes into C++ code,
was designed and developed without AI assistance from its beginning
in 2022 up to and including version 0.16 (May 2026). Starting with
version 0.17, AI coding assistance (Claude Fable 5 and Claude Opus 5.5
by Anthropic) has been used extensively, in particular, but not
exclusively, for the multi-material interface (``TapeIndex``, ``EndfFile``
and the multi-material support of ``endf-cli``, version 0.17), the
support for numpy arrays (``array_type="numpy"``, version 0.18), finding
and fixing bugs, and the performance optimization of the recipe
compiler and the generated C++ backend. All AI-assisted changes were
reviewed and tested before inclusion.
