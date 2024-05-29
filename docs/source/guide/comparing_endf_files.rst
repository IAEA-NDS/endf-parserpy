.. _guide_file_comparison:

Comparing ENDF-6 Files
======================

Producing a new nuclear data evaluation
typically involves many iterations with
various adjustments to an ENDF-6 file
before eventually converging to one version of the
file whose performance in relevant
benchmark experiments compares favorably
to other candidate files.

Version control
software, such as ``git``, enables the
systematic tracking of file modifications.
However, it is not enough to know that
a file changed but it is also very
important to be able to understand the
exact differences between different versions
of a file. Line-based comparison tools
are unfortunately of limited use for
comparing ENDF-6 files, as they can't
take into consideration the inherent logical
structure of these files.

In contrast, the dictionaries with ENDF-6 data
returned by the :func:`~endf_parserpy.EndfParser.parsefile` method
of the :class:`~endf_parserpy.EndfParser` class
are a perfect starting point for insightful
comparisons between two ENDF-6 files.
It it is straightforward to implement a
recursive function that walks through
the nested structure of two dictionaries
in sync and reports any differences found.
The function :func:`~endf_parserpy.compare_objects`
does exactly that. Following, we want to showcase
the use of this function and discuss the form
of its output.

Assume that we have two ENDF-6 files named
``input1.endf`` and ``input2.endf``. We can
compare their content with the following
code snippet:

.. code:: Python

   from endf_parserpy import EndfParser
   from endf_parserpy import compare_objects
   parser = EndfParser()
   endf_dict1 = parser.parsefile('input1.endf')
   endf_dict2 = parser.parsefile('input2.endf')
   compare_objects(endf_dict1, endf_dict2, atol=1e-6, rtol=1e-6, fail_on_diff=False)

After the content of the two ENDF-6 files has been read into two dictionaries
named ``endf_dict1`` and ``endf_dict2``, the
:func:`~endf_parserpy.compare_objects` function
is invoked for the comparison. The argument ``atol`` defines
the absolute difference and the argument ``rtol`` the relative
difference below which
two floating point numbers are considered equal.
The provision of the ``fail_on_diff=False`` argument is important
because this function would otherwise raise an exception
after the first encounter of a difference between the two
dictionaries.

Apart from returning ``True`` if no differences were encountered
and ``False`` otherwise, the
:func:`~endf_parserpy.compare_objects`
function prints the discrepancies found on standard output.
The output may look like this:

.. code:: shell

    at path /2/151/isotope/1/range: only obj2 contains {2}
    Value mismatch at /2/151/isotope/1/range/1/EH (36000.0 vs 34490.0)
    Value mismatch at /3/1/AWR (12.0 vs 134.737)

The example output indicates the path where the difference
occured and the type of difference.
The first line informs us that only the second object
passed to :func:`~endf_parserpy.compare_objects`
possesses a key ``2`` at the path ``2/151/isotope/1/range``.
The second line points out a different value
of the ``EH`` variable in the first ``range``
section of the first isotope.
Similarly, the third line signals a difference of a value
in a MF=3/MT=1 section.
While the aesthetical appearance of the output can certainly
be improved, the indication of differences on the basis
of the logical structure is much more meaningful than
the result of a line-based diff tool.
