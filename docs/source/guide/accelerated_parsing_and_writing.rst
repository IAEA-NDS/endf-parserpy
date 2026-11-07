.. _accelerated_parsing_and_writing_sec:

Accelerated Parsing and Writing
===============================

The parsing and writing functionality of the
:class:`~endf_parserpy.EndfParserPy` class is implemented
in pure Python, which guarantees smooth functioning
on a wide variety of platforms as long as a Python interpreter
is available. However, the disadvantage is slow execution
speed compared to parsers implemented in compiled
languages, such as C++. The speed disadvantage is
exacerbated by the fact that ``endf-parserpy`` implements
at its core an interpreter for :ref:`ENDF recipe files <endf6_recipe_sec>`
which contain the necessary information to properly parse and write
ENDF-6 formatted files. Understandably, the implementation of
an interpreter in an interpreted language (Python) is even
slower than a direct implementation of the specific instructions
required for parsing and writing ENDF-6 files in Python.

For this reason, parsing and writing functionality is also
provided by C++ functions shipped with the ``endf-parserpy``
package. During the installation via ``pip install`` or equivalent
means, an attempt is made to compile the C++ source code to
Python modules if pre-compiled binary wheels for your platform are not
available. Provided that a binary exists for your platform or the
compilation from source is successful, you can benefit
from accelerated parsing and writing of ENDF-6 files by using
the :class:`~endf_parserpy.EndfParserCpp` class.

The interface of the :class:`~endf_parserpy.EndfParserCpp` class
closely mirrors the one of the :class:`~endf_parserpy.EndfParserPy` class,
providing most of the same initialization options. The following
code snippet demonstrates the reading and writing of an ENDF-6 file:

.. code:: Python

   from endf_parserpy import EndfParserCpp
   parser = EndfParserCpp()
   endf_dict = parser.parsefile('input.endf')
   # here you can modify endf_dict in some way
   parser.writefile('output.endf', endf_dict)

As can be seen, the same functions as for the
:class:`~endf_parserpy.EndfParserPy` class are available
and hence the :class:`~endf_parserpy.EndfParserCpp` class can
be used as a drop-in replacement. The fastest parsing and writing
is obtained with the ``array_type="numpy"`` option, i.e.
``EndfParserCpp(array_type="numpy")``, which returns arrays of
numbers as numpy arrays (see the ``array_type`` parameter in the
documentation of the :class:`~endf_parserpy.EndfParserCpp` class).
Be aware of a few differences: in case of an error,
:class:`~endf_parserpy.EndfParserCpp` reports the template of the
record being read, the line number and the failing field, whereas
:class:`~endf_parserpy.EndfParserPy` in addition provides a
record-by-record log of the parsing process. Furthermore, some
initialization options are not available.
One of these options is ``recipes`` that allows users
to provide their custom :ref:`format extensions <guide_format_extension>`.
In the following, we will explain how a user can generate their
own C++ module with parsing and writing functions based on their
own recipe files.


.. _cpp_bulk_bodies_sec:

Bulk reading of TAB1 and LIST bodies
------------------------------------

The float values of the bodies of TAB1 and LIST records can be read in
two forms by the C++ modules:

- the *per-field form*: each field is converted when its value is
  needed, and the lines of a body are read one after the other;
- the *bulk form* (the default): the float fields of the lines are
  converted with one call of a *row kernel* per line. A TAB1 body is read
  this way line by line. A LIST body is first read and converted as a
  whole into a buffer (a body of several lines of 75 to 80 columns with
  the same line ending, only printable characters and the MAT, MF and MT
  numbers of the section is checked and converted as one block of
  memory, any other body line by line, with the same checks and errors
  as in the per-field form), from which its values are then delivered to the
  variables: by strided copies if the code generator has proven the
  layout of the body regular (e.g. one copy per array for the bodies of
  MF6 LAW=1 records, the bulk of most neutron files, and one copy per
  row for the triangular matrices of covariance data, whose rows have
  lengths that depend on the row), otherwise by the same code as in the
  per-field form, which takes each value from the buffer. With the
  scalar row kernel, bodies without a regular layout (e.g. the
  scattering laws of thermal scattering data) are read in the per-field
  form, which is as fast for them, unless the tier is forced (see below);
  with a vector tier they are read in the bulk form, which is faster
  then.

The row kernel has several implementations (tiers); which one is used is
decided once when a C++ module is loaded, from the features of the
processor:

- ``avx512``: AVX-512 (the subsets F, BW, VL, DQ and VBMI, e.g. Intel
  processors since Ice Lake and Tiger Lake, AMD processors since Zen 4);
- ``avx2``: AVX2 with FMA (most x86-64 processors since about 2013);
- ``neon``: NEON (Advanced SIMD) of 64-bit ARM processors (AArch64,
  e.g. Apple silicon and the ARM servers of cloud providers);
- ``scalar``: the conversion field by field applied to a whole line, on
  every platform.

The ``avx2`` and ``avx512`` tiers are built on x86-64 with GCC and Clang
(Linux, macOS on Intel processors, MinGW, and clang-cl if its headers
declare the intrinsics without global compiler flags) and with the
Microsoft compiler (MSVC, Windows x64); the modules themselves are
compiled for the baseline instruction set, and only the functions of a
tier use its instructions, which are executed only if the processor and
the operating system support them. The ``neon`` tier is
built on 64-bit ARM (AArch64) with GCC, Clang and MSVC (Linux, macOS,
Windows); NEON is part of the baseline instruction set there, so this
tier is always supported. If the modules are compiled with GCC (e.g. the
Linux wheels and most installations from source under Linux), the
``neon`` tier is built but not chosen automatically, only if it is
requested: on a Neoverse N2 processor, parsing with it compiled by GCC
13 was a few percent slower than with the ``scalar`` tier, while the
same code compiled by Clang was 10–13% faster than the scalar tier
(``array_type="numpy"``). Modules compiled with Clang (also Apple
Clang) or MSVC choose ``neon``. On other architectures (e.g. 32-bit
ARM, 32-bit x86), only the scalar tier is built.
The vector tiers need GCC 8 or later, Clang 8 or later (Apple Clang 11
or later) or MSVC 19.30 (Visual Studio 2022) or later; with an older
compiler the modules are built with the scalar tier only.
The parse results do not depend on the form or the tier: a row kernel
converts a field only if the conversion field by field would give the
same value, every other field is converted field by field, and the
checks of the values and all errors (type, message and the line named in
it) are those of the per-field form, in the same order. The bulk form is
not used for ``preserve_value_strings=True`` (which needs the strings of
the fields), for ``load_file_into_memory=False`` and in the lookahead of
recipes; writing is not affected.

The environment variable ``ENDF_PARSERPY_CPP_BULK_BODIES``, read when a
C++ module is loaded (i.e. before the first
:class:`~endf_parserpy.EndfParserCpp` object of an ENDF format flavor is
created in a Python process), selects the form and the tier of the row
kernel:

- ``auto`` (the default, also if the variable is unset or empty): the
  bulk form with the fastest vector tier supported by the processor (not
  ``neon`` in modules compiled with GCC, see above), or with the scalar
  row kernel if there is none (then only for the LIST bodies with a
  regular layout);
- ``off``: the per-field form, as in versions without the bulk form; for
  diagnosis and comparisons;
- ``scalar``: the bulk form with the scalar row kernel, the conversion
  field by field applied to a whole line, for all LIST bodies with a
  loop; it is also the reference for testing the vector tiers;
- ``avx2``, ``avx512``, ``neon``: the bulk form with this vector tier
  (``avx2`` and ``avx512`` on x86-64, ``neon`` on 64-bit ARM), if it is
  built and supported by the processor.

If the requested tier is not available, or the value is not one of
these, the automatic choice is used and a ``RuntimeWarning`` is issued
when the module is loaded. For example, to parse in the per-field form
under Linux or macOS:

.. code:: bash

   ENDF_PARSERPY_CPP_BULK_BODIES=off python my_script.py

The function ``_bulk_body_info`` of each C++ module returns the
selected tier (``selected``: ``avx512``, ``avx2``, ``neon``,
``scalar`` or ``off``), the name and the value of the variable (``variable``,
``requested``), the reason why a requested tier is not used
(``warning``), for each tier whether it is built, supported by the
processor, a vector tier and chosen by ``auto`` if available
(``tiers``), the detected processor features (``cpu``), the compiler of
the module (``compiler``: ``gcc``, ``clang``, ``apple-clang``,
``clang-cl``, ``msvc`` or ``other``), the number of lines converted by
the scalar tier
(``scalar_kernel_lines``), whether all LIST bodies
with a loop are read in the bulk form (``bulk_all_list_bodies``) and the
numbers of LIST bodies read in the bulk form (``bulk_list_bodies``:
delivered by strided copies, delivered by the code of the per-field
form, those whose conversion stopped at a field the row kernel does
not convert, the bodies of several lines read as one block of memory
and line by line, and, of the bodies delivered by strided copies, those
with one copy per row, their values and their rows). It is meant for diagnostics and tests; its name and content
may change between versions:

.. code:: Python

   import importlib
   from endf_parserpy import EndfParserCpp
   parser = EndfParserCpp()
   module = importlib.import_module(parser._parse_endf.__module__)
   print(module._bulk_body_info()["selected"])


Generating C++ code from ENDF recipes
----------------------------------------

To follow this section properly, basic knowledge of using
a C++ compiler, such as ``clang`` or the ``GNU C++`` compiler,
is likely required. The aim of this section is to provide a
starting point for expert users to compile their own ENDF format parsers
but a detailed explanation of all possible pitfalls in the process
is beyond the scope of this document.

We assume that your recipes are available in a nested dictionary
where the keys of the first level are the MF numbers (of type :class:`int`)
and the keys of the second level the MT numbers (of type :class:`int`).
The recipes themselves are stored in strings. Consult the
`available ENDF-6 recipes
<https://github.com/IAEA-NDS/endf-parserpy/tree/main/endf_parserpy/endf_recipes/endf6>`_
to remind yourself of their form. The section on
:ref:`mappings by ENDF recipes <endf6_recipe_sec>` is also helpful
in this regard. For the sake of illustration, we will just use the
ENDF recipes shipped with this package:

.. code:: Python

    from endf_parserpy.endf_recipes.endf6_ext import endf_recipe_dictionary

.. note::

   A recipe dictionary must contain the recipe for the tape
   identification (TPID) record under MF=0 and MT=0, as the recipe
   dictionaries of the package do, e.g.
   ``recipes = {0: {0: '[MAT, 0, 0/ TAPEDESCR]TEXT'}, 3: ...}``.
   Without it, the first line of a tape is not recognized as the
   TPID record and parsing fails with a confusing error.


Now, you can use the ``create_project_files`` function to generate the
module code for parsing and writing files that conform to the format
description stored in the ``endf_recipe_dictionary``:

.. code:: Python

    from endf_parserpy.compiler.compiler import create_project_files
    create_project_files(
        "endf_parser_project", "cpp_endf", recipes=endf_recipe_dictionary,
        path_exist_ok=False, overwrite_files=False
    )

This code will create a directory ``endf_parser_project`` with a
simple example ``CMakeLists.txt`` file and a C++ source file named
``cpp_endf.cpp``. For an impression how the generated C++ source code looks
like, have a look at this `example C++ source file
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/cpp_parsers/endf6.cpp>`_.
Provided that the `pybind11
<https://pybind11.readthedocs.io/en/stable/index.html>`_  header files
are available on your system, you can use your favorite C++ compiler
(supporting the C++11 standard) to generate a dynamic library that
can be imported in Python. The header files and the CMake
configuration of pybind11 can be conveniently installed with
``pip install pybind11``; the location of the CMake configuration is
then given by ``python -c "import pybind11; print(pybind11.get_cmake_dir())"``.
If everything is correctly configured, the following
instructions on the command line can be used to compile the source code:

.. code:: console

   cd endf_parser_project/build
   cmake -Dpybind11_DIR=$(python -c "import pybind11; print(pybind11.get_cmake_dir())") ..
   make


The result of the successful compilation is a file named similar to
``cpp_endf.cpython-39-x86_64-linux-gnu.so`` in the ``build`` directory.
Being still in this directory, you can start an interactive Python session
and test whether the module can be imported:

.. code:: Python

    from cpp_endf import (
        parse_endf,
        parse_endf_file,
        write_endf,
        write_endf_file
    )

Here are a couple of examples how these functions can be used:


.. code:: Python

   endf_dict = parse_endf_file("input.endf")
   endf_dict = parse_endf_file("input.endf", exclude=(3,), parse_opts={"accept_spaces": False})
   endf_string = write_endf(endf_dict, write_opts={"abuse_signpos": True})
   endf_dict2 = parse_endf(endf_string)
   write_endf_file("output.endf", endf_dict, write_opts={"prefer_noexp": True})


The available keys for the ``parse_opts`` and ``write_opts`` dictionary can be found
in the documentation of the :class:`~endf_parserpy.EndfParserCpp` class.
Furthermore, all functions are endowed with an ``include`` and ``exclude``
argument that behaves exactly the same way as for the member methods of the
:class:`~endf_parserpy.EndfParserCpp` class.
In fact, this class is only a thin wrapper around the C++ module functions.
