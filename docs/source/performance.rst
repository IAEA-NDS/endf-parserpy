Performance
===========

This page gives the time and the peak memory of parsing and writing
the sublibraries of ENDF/B-VIII.1 with ``EndfParserCpp`` and
``EndfParserPy``, each with ``array_type`` ``"dict"``, ``"list"`` and
``"numpy"``. Here ``array_type="list"`` is the representation of arrays
(see :doc:`guide/arrays_as_list`), not the list form of a material.
Every number on this page comes from one results file, produced by one
command (see `Reproducing the numbers`_), and is refreshed for each
release.


Summary
-------

.. include:: performance/summary.rst


What is measured
----------------

Parsing is ``parser.parsefile(path)`` and writing is
``parser.write(obj)`` of the object parsed in the same mode, which gives
the ENDF-6 text in memory; no disk access is included. Each parser and
mode runs in a fresh process of its own on a single core, with the
default options of the parser (``endf_format``, ``material_form`` and no
``preserve_value_strings``), the garbage collector enabled, as for a
user, and a warm file cache, so that disk speed is not measured. Every
value is fully interpreted during parsing, and written output is
formatted field by field. The rounds are interleaved over the parsers
and modes, so that slow drifts of the machine affect them alike.

.. include:: performance/method.rst


Machine and software
--------------------

.. include:: performance/machine.rst


Results by sublibrary
---------------------

The time is the total over all files of the sublibrary for
``EndfParserCpp``, and over the files of the sample for
``EndfParserPy``.

.. include:: performance/by_sublibrary.rst


By file size
------------

The files are grouped by their size. Small files show the fixed cost
per file: opening the file, setting up the dictionary of a material and
reading the tape head. Large files show the throughput of the bulk of
the data, mostly the arrays of numbers.

.. include:: performance/by_size.rst


Memory
------

The peak memory is measured in a separate pass, after the times. With
``array_type="numpy"``, the arrays of numbers are numpy arrays, which
store a float in 8 bytes; ``"dict"`` stores every value as a Python
object in a dictionary, keyed by its index, which takes several times
as much. For small files, the increase of the peak is within the memory
that the process has already reserved, and the factor is not
meaningful.

.. include:: performance/memory.rst


Choosing a parser and a mode
----------------------------

- ``EndfParserCpp`` unless the recipes are given at run time, which
  only ``EndfParserPy`` supports (see :doc:`guide/python_and_cpp_parser`
  and :doc:`guide/accelerated_parsing_and_writing`).
- ``array_type="numpy"`` for large arrays and less memory.
- ``array_type="dict"`` when index arithmetic is not wanted; ``"list"``
  gives the arrays as Python lists (see :doc:`guide/arrays_as_list`).


Reproducing the numbers
-----------------------

1. Download the sublibraries of ENDF/B-VIII.1 from the
   `NNDC <https://www.nndc.bnl.gov/endf-releases/>`_ and unpack them
   into one directory, which then contains ``neutrons-version.VIII.1``,
   ``decay-version.VIII.1`` and so on.
2. Install endf-parserpy and numpy, e.g.
   ``python -m pip install endf-parserpy numpy``.
   The results record the version of a release; for a package
   installed from a git checkout, also the commit and ``git describe``
   of the checkout, with ``+modified`` if the installed ``.py`` files
   differ from those of the checkout, and for a git URL the commit.
3. Run the measurement with the tool of the repository,
   ``tools/benchmark_report.py``, from a directory that does not
   contain an ``endf_parserpy`` source tree, which would be imported
   instead of the installed package::

       python benchmark_report.py measure <directory> --out my_results.json \
           --check-manifest results.json --sample results.json --pin-cpu 2

   where ``results.json`` is the published results file of this page.
   ``--check-manifest`` reports the files that are missing or differ
   from those measured here, and ``--sample`` uses the same files for
   ``EndfParserPy``. ``--sublibraries neutrons`` limits the measurement
   to one sublibrary.
4. Compare: ``python benchmark_report.py render my_results.json
   --out-dir <dir>`` writes the tables of this page for your results,
   and ``readme-sentence`` the sentence of the README.

For comparable numbers, run on an idle machine on AC power, with the
power profile for performance, and with the C++ module of a wheel or a
release build.
