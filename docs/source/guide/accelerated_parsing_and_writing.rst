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
means, an attempt is made to compile the C++ source code to a
Python extension module, which contains the functions of all format
flavors, if pre-compiled binary wheels for your platform are not
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
To read and write your own recipes with C++ code, you can add them to
the package as a new format flavor (see :ref:`adding_recipe_flavor_sec`)
or generate a standalone C++ module from them (see
:ref:`generating_cpp_code_sec`).

The next section describes how the C++ parser reads numeric data and
how to check it; the last two sections describe how to use your own
recipes with C++ code.


.. _cpp_bulk_bodies_sec:

Fast reading of numeric data
----------------------------

Most of the data of an ENDF-6 file are the numbers in the bodies of
TAB1 and LIST records. :class:`~endf_parserpy.EndfParserCpp` converts
them a whole line at a time instead of field by field (*bulk reading*)
and, where the processor supports it, with its vector instructions
(AVX2 or AVX-512 on x86-64, NEON on 64-bit ARM). This happens
automatically, and nothing needs to be configured.

The results are exactly the same as with reading field by field: every
value, every check of the data and every error, including its message
and the line it names. Only the speed differs. Bulk reading is not used
with ``preserve_value_strings=True`` and ``load_file_into_memory=False``,
which affects only the speed; writing is not affected.

The implementation of bulk reading for a processor is called a *tier*.
The tier is chosen once, when the C++ module is loaded:

.. list-table::
   :header-rows: 1
   :class: wrap-cells
   :widths: 15 55 30

   * - Tier
     - Processors
     - Chosen automatically
   * - ``avx512``
     - x86-64 with AVX-512 (the subsets F, BW, VL, DQ and VBMI), e.g.
       Intel processors since Ice Lake and Tiger Lake, AMD processors
       since Zen 4
     - yes
   * - ``avx2``
     - x86-64 with AVX2 and FMA (most x86-64 processors since about 2013)
     - yes, if ``avx512`` is not available
   * - ``neon``
     - 64-bit ARM (AArch64), e.g. Apple silicon and the ARM servers of
       cloud providers
     - yes, unless the module is compiled with GCC, as the Linux wheels are
   * - ``scalar``
     - every processor, without vector instructions
     - if no vector tier is available

Checking and changing the selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The selected tier can be printed with:

.. code:: Python

   import importlib
   from endf_parserpy import EndfParserCpp
   parser = EndfParserCpp()
   module = importlib.import_module(parser._parse_endf.__module__)
   print(module._bulk_body_info()["selected"])

The environment variable ``ENDF_PARSERPY_CPP_BULK_BODIES`` selects
the tier, or switches bulk reading off. It is read when the C++ module
is loaded, i.e. when the first :class:`~endf_parserpy.EndfParserCpp`
object is created in a Python process, whatever its format flavor:

.. list-table::
   :header-rows: 1
   :class: wrap-cells
   :widths: 25 75

   * - Value
     - Effect
   * - ``auto``
     - The default, also if the variable is unset or empty: the fastest
       tier available, as in the table above.
   * - ``off``
     - Reading field by field, as in versions without bulk reading; for
       diagnosis and comparisons.
   * - ``scalar``
     - Bulk reading without vector instructions, for all LIST bodies with
       a loop; the reference for testing the vector tiers.
   * - ``avx2``, ``avx512``, ``neon``
     - Bulk reading with this tier, if it is built and supported by the
       processor.

If the requested tier is not available, or the value is not one of
these, the automatic choice is used and a ``RuntimeWarning`` is issued
when the module is loaded. For example, to read field by field under
Linux or macOS:

.. code:: bash

   ENDF_PARSERPY_CPP_BULK_BODIES=off python my_script.py

The following technical details are for those who want to know how
bulk reading works; they are not needed to use it.

.. dropdown:: How bulk reading works

   The float values of the bodies of TAB1 and LIST records can be read in
   two forms by the C++ module:

   - the *per-field form*: each field is converted when its value is
     needed, and the lines of a body are read one after the other;
   - the *bulk form* (the default): the float fields of a line are
     converted with one call of a *row kernel*, of which each tier is an
     implementation.

   A TAB1 body is read in the bulk form line by line. A LIST body is
   read in three steps:

   1. The body is read and converted as a whole into a buffer. A body of
      several lines that all have 75 to 80 columns, the same line ending,
      only printable characters and the MAT, MF and MT numbers of the
      section is checked and converted as one block of memory; any other
      body line by line, with the same checks and errors as in the
      per-field form.
   2. If the code generator has proven the layout of the body regular,
      its values are delivered to the variables by strided copies: e.g.
      one copy per array for the bodies of MF6 LAW=1 records, the bulk of
      most neutron files, and one copy per row for the triangular
      matrices of covariance data, whose rows have lengths that depend on
      the row.
   3. Otherwise, the values are delivered by the same code as in the
      per-field form, which takes each value from the buffer.

   With the scalar row kernel, bodies without a regular layout (e.g. the
   scattering laws of thermal scattering data) are read in the per-field
   form, which is as fast for them, unless the tier is requested with
   ``ENDF_PARSERPY_CPP_BULK_BODIES=scalar``; with a vector tier they are
   read in the bulk form, which is faster then.

   The parse results do not depend on the form or the tier: a row
   kernel converts a field only if the conversion field by field would
   give the same value, every other field is converted field by field,
   and the checks of the values and all errors (type, message and the
   line named in it) are those of the per-field form, in the same order.
   The bulk form is not used for ``preserve_value_strings=True`` (which
   needs the strings of the fields), for ``load_file_into_memory=False``
   and in the lookahead of recipes.

.. dropdown:: Platforms and compilers

   The ``avx2`` and ``avx512`` tiers are built on x86-64 with GCC and
   Clang (Linux, macOS on Intel processors, MinGW, and clang-cl if its
   headers declare the intrinsics without global compiler flags) and with
   the Microsoft compiler (MSVC, Windows x64). The module itself is
   compiled for the baseline instruction set, and only the functions of a
   tier use its instructions, which are executed only if the processor
   and the operating system support them.

   The ``neon`` tier is built on 64-bit ARM (AArch64) with GCC, Clang and
   MSVC (Linux, macOS, Windows); NEON is part of the baseline instruction
   set there, so this tier is always supported. If the module is compiled
   with GCC (e.g. the Linux wheels and most installations from source
   under Linux), the ``neon`` tier is built but not chosen automatically,
   only if it is requested: on a Neoverse N2 processor, parsing with it
   compiled by GCC 13 was a few percent slower than with the ``scalar``
   tier, while the same code compiled by Clang was 10–13% faster than the
   scalar tier (``array_type="numpy"``). A module compiled with Clang
   (also Apple Clang) or MSVC chooses ``neon``.

   On other architectures (e.g. 32-bit ARM, 32-bit x86), only the scalar
   tier is built. The vector tiers need GCC 8 or later, Clang 8 or later
   (Apple Clang 11 or later) or MSVC 19.30 (Visual Studio 2022) or later;
   with an older compiler the module is built with the scalar tier only.

.. dropdown:: What ``_bulk_body_info`` returns

   The function ``_bulk_body_info`` of the C++ module (see the example
   above) is meant for diagnostics and tests; its name and content may
   change between versions. It returns a dictionary with:

   - ``selected``: the selected tier (``avx512``, ``avx2``, ``neon``,
     ``scalar`` or ``off``);
   - ``variable``, ``requested``: the name and the value of the
     environment variable;
   - ``warning``: the reason why a requested tier is not used;
   - ``tiers``: for each tier, whether it is built, supported by the
     processor, a vector tier and chosen by ``auto`` if available;
   - ``cpu``: the detected processor features;
   - ``compiler``: the compiler of the module (``gcc``, ``clang``,
     ``apple-clang``, ``clang-cl``, ``msvc`` or ``other``);
   - ``scalar_kernel_lines``: the number of lines converted by the scalar
     tier;
   - ``bulk_all_list_bodies``: whether all LIST bodies with a loop are
     read in the bulk form;
   - ``bulk_list_bodies``: the numbers of LIST bodies read in the bulk
     form: delivered by strided copies, delivered by the code of the
     per-field form, those whose conversion stopped at a field the row
     kernel does not convert, the bodies of several lines read as one
     block of memory and line by line, and, of the bodies delivered by
     strided copies, those with one copy per row, their values and their
     rows.

   The C++ code of all format flavors is in one module, so that the
   selection and the counters are the same for all flavors: the counters
   count the bodies read by the parsers of all flavors in the Python
   process (until version 0.18, every flavor had a module and counters of
   its own).


.. _cpp_module_names_sec:

C++ module names before version 0.19
-------------------------------------

The modules of the flavors until version 0.18, e.g.
``endf_parserpy.cpp_parsers.endf6``, are deprecated: they can still be
imported and give the functions of the flavor, with a
``DeprecationWarning``, and will be removed in a later version. Use
:class:`~endf_parserpy.EndfParserCpp` with the ``endf_format`` argument
instead, and ``importlib.import_module(parser._parse_endf.__module__)``
as in :ref:`cpp_bulk_bodies_sec` for the diagnostic functions.


.. _adding_recipe_flavor_sec:

Adding a recipe flavor to the package
-------------------------------------

:class:`~endf_parserpy.EndfParserCpp` reads and writes the format
flavors whose C++ code was compiled into the C++ module of the package
when the package was installed (see the ``endf_format`` argument). The simplest way to use your own
recipes with it is to add them to the package as a new flavor and to
install the package from its source code: the installation then
generates the C++ code of the new flavor and compiles it into the
module in the same way as that of the flavors shipped with the package. This needs a C++
compiler, but no knowledge of it.

As an example, we add a flavor ``myflavor`` that differs from the
``endf6`` flavor in one field. Suppose that the files of your library
store a revision number of the evaluation in the fourth field of the
third record of MF1/MT451, which the ENDF-6 format leaves at zero. The
``endf6`` flavor tolerates a value other than zero in this field, but
does not keep it: parsing issues an
:class:`~endf_parserpy.EndfToleratedMismatchWarning`, and writing the
data gives a zero (see :ref:`tolerated_mismatches_sec`). The flavor
``myflavor`` reads this field into a variable ``NREV`` instead.

1. Clone the repository, preferably at a release tag (``git tag`` lists
   them), and work on a branch of your own:

   .. code:: console

      git clone https://github.com/IAEA-NDS/endf-parserpy.git
      cd endf-parserpy
      git checkout -b myflavor <tag>

   The following commands are run in the root directory of the clone.

2. Create the folder of the flavor in ``endf_parserpy/endf_recipes``,
   with the recipe that changes. Here we start from a copy of the
   ``endf6`` recipe of MF1/MT451:

   .. code:: console

      mkdir endf_parserpy/endf_recipes/myflavor
      cp endf_parserpy/endf_recipes/endf6/endf_recipe_mf1_mt451.py endf_parserpy/endf_recipes/myflavor/

   In the copy, ``endf_parserpy/endf_recipes/myflavor/endf_recipe_mf1_mt451.py``,
   replace the zero in the third record by the variable:

   .. code:: text

      [MAT, 1,451/ AWI, EMAX, LREL, NREV, NSUB, NVER]CONT

   The flavor itself is the file
   ``endf_parserpy/endf_recipes/myflavor/__init__.py``, which defines the
   recipe dictionary ``endf_recipe_dictionary``. It derives from the
   ``endf6`` flavor, as the ``jendl`` flavor of the package does:

   .. code:: Python

      from copy import deepcopy
      from ..utils import defdic
      from ..endf6 import endf_recipe_dictionary as base_recipe_dictionary

      from .endf_recipe_mf1_mt451 import ENDF_RECIPE_MF1_MT451

      endf_recipe_dictionary = deepcopy(base_recipe_dictionary)
      defdic(endf_recipe_dictionary, (1, 451), ENDF_RECIPE_MF1_MT451)

      # the tape structure of the flavor: that of ENDF-6, the defaults
      TAPE_STRUCTURE = {}

   The copy of the ``endf6`` dictionary contains all its recipes,
   including the recipe of the tape identification (TPID) record under
   MF=0 and MT=0, which every recipe dictionary needs. ``defdic``
   replaces the recipe of MF1/MT451; the index ``(MF,)`` instead of
   ``(MF, MT)`` sets a recipe for all MT sections of an MF section. The
   file ``__init__.py`` is also needed for the folder to be installed
   with the package. ``TAPE_STRUCTURE`` is the
   :ref:`tape structure <tape_structure_sec>` of the flavor; the empty
   dictionary is that of ENDF-6.

3. Register the flavor in ``endf_parserpy/endf_recipes/catalogue.py``,
   with an entry in the dictionary ``_FLAVOR_PACKAGES``, which maps the
   names of the flavors to the names of their folders:

   .. code:: Python

      _FLAVOR_PACKAGES = {
          # ... the entries of the other flavors
          "myflavor": "myflavor",
      }

   The folder of a flavor is imported when its recipes or its tape
   structure are first needed, not with the package, so that an error
   in one of its files appears only then.

4. Try the flavor with :class:`~endf_parserpy.EndfParserPy` first, in an
   interactive Python session started in the root directory of the clone,
   which then imports the package from the clone. Nothing needs to be compiled or
   installed, and a change of a recipe takes effect in the next Python
   session, which makes this the fastest way to work on the recipe:

   .. code:: Python

      from endf_parserpy import EndfParserPy
      parser = EndfParserPy(endf_format="myflavor")
      endf_dict = parser.parsefile("input.endf")
      print(endf_dict[1][451]["NREV"])

5. Build and install the package from the clone, preferably in a
   virtual environment:

   .. code:: console

      INSTALL_ENDF_PARSERPY_CPP=yes python -m pip install .

   (under Windows, ``set INSTALL_ENDF_PARSERPY_CPP=yes`` first, then
   ``python -m pip install .``). This needs a C++ compiler; ``pip``
   installs the other build requirements, such as pybind11, itself.
   ``INSTALL_ENDF_PARSERPY_CPP=yes`` makes the installation fail with an
   error if the C++ module cannot be compiled (if no compiler is found,
   the error is ``Unsupported compiler -- at least C++11 support is
   needed!``). Without it, the installation then succeeds without any C++
   module, with no message unless ``pip`` is run with ``-v``, and
   :class:`~endf_parserpy.EndfParserCpp` raises an ``ImportError``
   (``Unable to import the cpp module ...``).
   The build generates the C++ code of all flavors in ``_FLAVOR_PACKAGES``,
   not only of the new one, and compiles it into one module, which takes
   about a minute on a laptop processor with eight threads (about three
   minutes with one compile job). The variables
   ``INSTALL_ENDF_PARSERPY_NUM_BUILD_JOBS`` (the number of parallel
   compile jobs) and ``INSTALL_ENDF_PARSERPY_CPP_OPTIM`` (the
   optimization flag, by default ``-O1`` on Linux and macOS and ``/O2``
   on Windows) are explained in the :doc:`installation notes </index>`.

6. Use the flavor with :class:`~endf_parserpy.EndfParserCpp`, in a Python
   session started outside the root directory of the clone, so that the
   installed package is imported, not the one in the clone, which does
   not contain the compiled module:

   .. code:: Python

      from endf_parserpy import EndfParserCpp
      parser = EndfParserCpp(endf_format="myflavor")
      endf_dict = parser.parsefile("input.endf")
      print(endf_dict[1][451]["NREV"])
      parser.writefile("output.endf", endf_dict)

Some points to keep in mind:

- After a change of a recipe, install the package again (step 5) before
  :class:`~endf_parserpy.EndfParserCpp` sees the change; the compiled
  code of the flavor is otherwise the one of the previous
  installation.
- An editable installation, ``INSTALL_ENDF_PARSERPY_CPP=yes python -m
  pip install -e .``, also works: the compiled module, one file such as
  ``_flavors.cpython-312-x86_64-linux-gnu.so`` (``_flavors.cp312-win_amd64.pyd``
  under Windows), is then placed
  into ``endf_parserpy/cpp_parsers/`` of the clone, and a change of a
  recipe is seen by :class:`~endf_parserpy.EndfParserPy` in the next
  Python session without installing again, from any directory. For
  :class:`~endf_parserpy.EndfParserCpp`, the editable installation must
  still be run again after a change of a recipe. An editable
  installation of a version until 0.18 placed one module per flavor
  there instead (e.g. ``endf6.cpython-312-x86_64-linux-gnu.so``). Python
  would import such a file instead of the current code of the same
  name, so the build removes these files, and importing the package
  issues a ``RuntimeWarning`` that names any such file that is left.
- Installing or upgrading ``endf-parserpy`` from PyPI replaces the
  package including the flavor. Keep the flavor on its branch of the
  clone, and install from the clone again after an upgrade, e.g. after
  rebasing the branch on a newer release tag.
- The build writes the generated C++ code into
  ``endf_parserpy/cpp_parsers/`` (one file per flavor,
  ``_flavor_<name>.cpp``, the module init ``_flavors.cpp`` and the code
  shared by the flavors, ``_shared_part_<NN>.cpp``), so that
  ``git status`` shows the C++ files there as modified, deleted or new
  (and, after an editable installation, the compiled module as new). Don't commit them with the flavor; the
  flavor consists of its folder and its entry in ``catalogue.py``.
- If your flavor is of general interest, consider contributing it
  through a pull request on
  `GitHub <https://github.com/IAEA-NDS/endf-parserpy>`_.


.. _generating_cpp_code_sec:

Generating C++ code from ENDF recipes
----------------------------------------

To follow this section properly, basic knowledge of using
a C++ compiler, such as ``clang`` or the ``GNU C++`` compiler,
is likely required. The aim of this section is to provide a
starting point for expert users to compile their own ENDF format parsers
but a detailed explanation of all possible pitfalls in the process
is beyond the scope of this document. The result is a standalone Python
module outside the package; to use your recipes with
:class:`~endf_parserpy.EndfParserCpp`, add them to the package as a
flavor instead (see :ref:`adding_recipe_flavor_sec`).

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

While it generates the code, the function prints a line for each recipe,
e.g. ``MF: 0 MT: 0``, once for the parsing and once for the writing
functions.

The argument ``tape_structure`` (a dictionary or a
:class:`~endf_parserpy.TapeStructure`, ENDF-6 by default) gives the
rules for the framing and the arrangement of the sections that the
functions of the module use, e.g. no SEND record after a section whose
recipe ends without ``SEND``; the recipes and the tape structure must
agree on the SEND records.

This code will create a directory ``endf_parser_project`` with a
simple example ``CMakeLists.txt`` file, a C++ source file named
``cpp_endf.cpp`` and an empty directory ``build``. The file
``cpp_endf.cpp`` is the complete source code of the module, generated
from the recipes; have a look at it for an impression of how the
generated C++ code looks like.
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

The generated project builds the module optimized by default (build
type ``Release``), with GCC and Clang at ``-O1``, the level that the
installation of the package uses (see the optimization flag in step 5
of the previous section). Other choices are passed to ``cmake``:

- ``-DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG"`` for the highest
  optimization level. In a measurement with GCC 13, the build took about
  twice as long (47 instead of 23 seconds, with two and a half times the
  CPU time), and the module parsed a test file at most 5% faster. Keep
  ``-DNDEBUG`` in this value, as in the default and in the installation
  of the package: it switches off the debug checks of pybind11 and the
  standard ``assert``.
- ``-DCMAKE_BUILD_TYPE=Debug`` for a build without optimization and with
  debugging information.

With MSVC, CMake's own defaults for ``Release`` (``/O2``) are used.


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

   from endf_parserpy import to_dict_form

   sections = parse_endf_file("input.endf")
   endf_dict = to_dict_form(sections)
   sections = parse_endf_file("input.endf", exclude=(3,), parse_opts={"accept_spaces": False})
   endf_string = write_endf(endf_dict, write_opts={"abuse_signpos": True})
   sections2 = parse_endf(endf_string)
   write_endf_file("output.endf", sections2, write_opts={"prefer_noexp": True})

``parse_endf`` and ``parse_endf_file`` return a material as the **list of
its sections** in the order of the file (the tape head first), for every
flavor; :func:`~endf_parserpy.to_dict_form` turns it into the nested
dictionary ``{MF: {MT: section}}``, which
:class:`~endf_parserpy.EndfParserCpp` returns. ``write_endf`` and
``write_endf_file`` accept both forms. The SEND, FEND, MEND and TEND
records are read and generated by the *tape structure* (see
:class:`~endf_parserpy.TapeStructure`), which the functions take at run
time from their options. Options without it get the structure compiled
into the module as their default: that of ENDF-6, or the one given to
``create_project_files(..., tape_structure=...)``. Another one can be
given in the options, ``parse_opts={"tape_structure":
TapeStructure.from_spec(spec).cpp_options()}``, and likewise in
``write_opts``; it must agree with the recipes of the module on the SEND
records. :class:`~endf_parserpy.EndfParserCpp` does not pass this option
and has no ``tape_structure`` argument: its flavor's structure is the
one compiled into the entry of the flavor, as the compiled recipes fix
the SEND records.


The keys of the ``parse_opts`` and ``write_opts`` dictionaries are the
options of the :class:`~endf_parserpy.EndfParserCpp` class marked as
*(parsing)* and *(writing)* in its documentation, respectively; an option
marked as both, such as ``array_type``, must be given in both
dictionaries, e.g. ``write_opts={"array_type": "numpy"}`` to write a
dictionary parsed with ``parse_opts={"array_type": "numpy"}``. A missing key
takes the default value of the option, and an unknown key raises an
error. Furthermore, all functions are endowed with an ``include`` and
``exclude`` argument that behaves exactly the same way as for the member
methods of the :class:`~endf_parserpy.EndfParserCpp` class.

The :class:`~endf_parserpy.EndfParserCpp` class calls these functions,
but also does some work of its own. It collects the options given to its
constructor into the two dictionaries, also accepts a list of lines in
``parse`` (``parse_endf`` takes a string), returns a list of lines from
``write`` (``write_endf`` returns a string), and writes a file only if it
does not exist yet or ``overwrite=True`` is given, via a temporary file
(``write_endf_file`` overwrites an existing file). It also reports the
:ref:`tolerated mismatches <tolerated_mismatches_sec>`: the direct
functions do not report them, i.e. with the default options a value
other than zero in a field given as ``0`` in a recipe is accepted and
dropped without any message. Use :class:`~endf_parserpy.EndfParserCpp`,
which issues an :class:`~endf_parserpy.EndfToleratedMismatchWarning` with
the lines of the mismatches, or turn them into errors with
``parse_opts={"ignore_zero_mismatch": False}`` (and likewise for
``ignore_varspec_mismatch``).
