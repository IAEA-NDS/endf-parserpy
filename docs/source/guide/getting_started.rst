.. _getting_started_sec:

Getting Started
===============

This brief section gives you the essential information
to work with the ``endf-parserpy`` package.

To parse an ENDF file, first instantiate an ENDF parser:

.. code:: Python

   from endf_parserpy import EndfParserFactory
   parser = EndfParserFactory.create()


Now you can parse a file like so:

.. code:: Python

    endf_dict = parser.parsefile('input.endf')

The ``endf_dict`` variable contains a Python dictionary
that can be accessed, traversed and modified like any other
Python dictionary. For example:

.. code:: Python

   endf_dict.keys()  # return all MF numbers in a file
   endf_dict[3].keys()  # return all MT numbers in MF3
   endf_dict[3][1].keys()  # return all field names in MF3/MT1
   endf_dict[3][1]['AWR'] = 99.99  # change value of AWR variable

If your modifications respect the structure expected for an
ENDF file, you can write out the dictionary as a new ENDF file:


.. code:: Python

   parser.writefile('output.endf', endf_dict)


That's all you need to know to get started. To learn more
of available options and ways to interact with ENDF files,
feel free to dive into the other tutorials in this documentation.
