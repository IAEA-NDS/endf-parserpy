.. _getting_started_sec:

Getting Started
===============

This brief section gives you the essential information
for working with the ``endf-parserpy`` package.

To parse an ENDF file, first instantiate an ENDF parser:

.. code:: Python

   from endf_parserpy import EndfParserFactory
   parser = EndfParserFactory.create()


Now you can parse a file like so:

.. code:: Python

    endf_dict = parser.parsefile('input.endf')

The ``endf_dict`` variable contains a Python dictionary,
which can be accessed, traversed and modified like any other
Python dictionary. For example:

.. code:: Python

   endf_dict.keys()  # return all MF numbers in a file
   endf_dict[3].keys()  # return all MT numbers in MF3
   endf_dict[3][1].keys()  # return all field names in MF3/MT1
   endf_dict[3][1]['AWR'] = 99.99  # change value of AWR variable

For the file ``tests/testdata/n_2925_29-Cu-63.endf`` of the source
repository, the first three lines return:

.. code:: text

   dict_keys([0, 1, 2, 3, 4, 6, 12, 14, 15])
   dict_keys([1, 2, 3, 4, 5, 16, 22, 28, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 91, 102, 103, 104, 106, 107])
   dict_keys(['MAT', 'MF', 'MT', 'xstable', 'ZA', 'AWR', 'QM', 'QI', 'LR'])

The key ``0`` (MF0) holds the tape head (TPID), the first line of
the file.

If your modifications respect the structure expected for an
ENDF file, you can write the dictionary as a new ENDF file to disk:

.. code:: Python

   parser.writefile('output.endf', endf_dict)

If ``output.endf`` already exists, a :exc:`FileExistsError` is raised;
pass ``overwrite=True`` to replace the file.

Alternatively, you can produce a list of strings with ENDF-6
formatted data using the :meth:`~endf_parserpy.EndfParserPy.write` method:

.. code:: Python

   endf6_data = parser.write(endf_dict)

Given ENDF-6 data as a string or list of strings, you can use the
:meth:`~endf_parserpy.EndfParserPy.parse` method to obtain a Python
dictionary:

.. code:: Python

   endf_dict = parser.parse(endf6_data)


That's all you need to know to get started.
To learn more about available options and ways to interact with ENDF files,
feel free to dive into the other tutorials in this documentation.

.. tip::

   A runnable script covering these basics is provided as
   ``examples/example-001-basic-parsing.py`` in the source repository.
