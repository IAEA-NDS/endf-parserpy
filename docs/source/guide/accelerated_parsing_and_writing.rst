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
be used as a drop-in replacement. Be aware that the
logging output is less verbose in case of an error and
that some initialization options are not available.
One of these options is ``recipes`` that allows users
to provide their custom :ref:`format extensions <guide_format_extension>`.
In the following, we will explain how a user can generate their
own C++ module with parsing and writing functions based on their
own recipe files.


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
can be imported in Python. If everything is correctly configured, the following
instructions on the command line can be used to compile the source code:

.. code:: console

   cd endf_parserpy_project/build
   cmake ..
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
