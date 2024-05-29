ENDF-6 File Plumbing
====================

The creation of a comprehensive ENDF-6 file
often is a multi-year, multi-person effort.
Several persons work together to
leverage their combined expertise in
the design of nuclear experiments, nuclear physics,
integral benchmarks, the usage of transport codes,
statistical procedures, the ENDF-6 format, and the processing
of ENDF-6 files to application formats for creating a
well-performing ENDF-6 file.

Considering the huge effort that has gone into the production
of the existing ENDF-6 files in various nuclear data library
projects, files are usually not created from scratch
but rather existing files tweaked to improve their performance.
This tweaking may also involve the merging of specific
information from several files into a single one.

In this guide, we explain the following basic operations on
ENDF-6 files:

- Tweaking cross sections
- Removing MF/MT sections
- Including an MF/MT section from another file
- Modifying arrays

The explanations for these actions will also give
some intuition on how similar operations not listed here can be
accomplished.

Tweaking a cross section
------------------------

Let's assume the elastic cross section in an ENDF-6 file
stored in MT=2 (see :endf6manshort:`348`) is globally
underestimated by 5%. Therefore, we want to rescale this
cross section accordingly.

.. note::

   In principe, other cross sections must be updated
   as well to preserve the sum rules
   (see :endf6manshort:`40`). There are
   several ways how this can be done, e.g.
   by updating the total cross section. However,
   consistent updating will not be covered in
   this short guide.


The following code snippet achieves this:

.. code:: python

   from endf_parserpy import EndfParser
   from endf_parserpy.accessories import EndfDict
   import numpy as np

   parser = EndfParser()
   endf_dict = EndfDict(parser.parsefile('input.endf'))

   xs = np.array(endf_dict['3/2/xstable/xs'])
   xs *= 1.05
   endf_dict['3/2/xstable/xs'] = list(xs)

   parser.writefile('output.endf', endf_dict)


The :class:`~endf_parserpy.EndfParser` class is imported
for reading and writing ENDF-6 files.
The :class:`~endf_parserpy.EndfDict` class is an
enhanced :class:`dict` that enables convenient access to
data via :ref:`EndfPaths <endf_path_class>`.

After instantiating an
:class:`~endf_parserpy.EndfParser` object,
the ENDF-6 file ``input.endf`` is read and the resulting
:class:`dict` immediately converted to an
:class:`~endf_parserpy.EndfDict` object.

Next, we retrieve the :class:`list` with the elastic cross
sections stored in the MF3/MT2 section, or more precisely
at ``3/2/xstable/xs``. The list is converted to a
numpy :class:`~numpy.ndarray` to leverage the associated functionality.
The array in ``xs`` can then be rescaled by 1.05 using
a simple instruction.
The result cast to a :class:`list` is assigned to the
respective location in ``endf_dict``, replacing the previous list.
Finally, the updated data is written to the file
``output.endf``.

In order to see whether the procedure had the intended effect,
we can compare the original file with the adjusted one:

.. code:: python

   from endf_parserpy import compare_objects
   endf_dict1 = parser.parsefile('input.endf')
   endf_dict2 = parser.parsefile('output.endf')
   compare_objects(endf_dict1, endf_dict2, atol=1e-6, rtol=1e-6 fail_on_diff=False)

The reported differences should only involve the location ``3/2/xstable/xs``.
Please also take note of the information in the
:ref:`section about writing ENDF-6 files <writing_endf_file_subsec>`
regarding the control of output precision.

With the instructions provided above, potentially small numerical
differences are introduced in other MF/MT sections if the original
file uses an unconventional notation style for real values, e.g.
switching from floating point notation to decimal notation to
increase precision.
To avoid this issue from the start, we can use the ``include``
argument in the call of the :func:`~endf_parserpy.EndfParser.parsefile`
method to only parse MF3/MT2. The other sections will then be read
verbatim as string and consequently also written verbatim to the output file.
The adjusted instruction for reading the ENDF-6 file in the current
example would be:

.. code:: python

   endf_dict = EndfDict(parser.parsefile('input.endf', include=[(3,2)])


Removing an MF/MT section
-------------------------

For removing MF/MT sections from a file we
can use basic Python functionality for deleting keys from dictionaries.
For example, the following code snippet removes the MF3/MT2 section
from an ENDF-6 file:

.. code:: python

   endf_dict = EndfDict(parser.parsefile('input.endf', include=[])
   del endf_dict['3/2']
   parser.writefile('output.endf')

The ``include=[]`` argument causes the parser to not parse any
MF/MT section in the ENDF-6 files and to store the raw strings
in the dictionary instead. In this way, we ensure that all preserved
sections are copied verbatim to the new file.

To check if everything worked as expected, we can again compare
the input and output file:

.. code:: pycon

    >>> endf_dict1 = parser.parsefile('input.endf', include=[])
    >>> endf_dict2 = parser.parsefile('output.endf', include=[])
    >>> compare_objects(endf_dict1, endf_dict2, fail_on_diff=False)
    at path /3: only obj1 contains {2}
    False


Including an MF/MT section from another file
--------------------------------------------

To include an MF/MT section from another file, we read
both files verbatim into two dictionaries and use
basic Python functionality to manipulate the dictionaries
for the desired effect. The resulting dictionary is then
written to an ENDF-6 file. Assume that we want to merge the
elastic cross sections (stored in MF3/MT2) from a file ``input1.endf``
into another file ``input2.endf``.
Here's the code snippet that
implements the described actions for this case:

.. code:: python

   from copy import deepcopy
   endf_dict1 = parser.parsefile('input1.endf', include=[]))
   endf_dict2 = parser.parsefile('input2.endf', include=[])
   endf_dict1 = EndfDict(endf_dict1)
   endf_dict2 = EndfDict(endf_dict2)
   endf_dict2['3/2'] = deepcopy(endf_dict1['3/2'])
   parser.writefile('output.endf', endf_dict2)

The invocation of the :func:`~copy.deepcopy` function is not really necessary.
However, without this operation,
``endf_dict1`` and ``endf_dict2`` would share the same dictionary
for the MF3/MT2 data. In this case, assignments such as
``endf_dict2['3/2/AWR'] = 10`` would cause  the same change
in ``endf_dict1``. Using the :func:`~copy.deepcopy` function
prevents this coupling.

.. _modifying_arrays_sec:

Modifying arrays
----------------

Arrays are implemented as dictionaries with contiguous integer keys.
Consider the following part extracted from the
`ENDF-6 recipe for MF6 sections
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf6/endf_recipe_mf6.py>`_:

.. code:: text

    for j=1 to NE:
        [MAT, 6, MT/ 0.0, E[j] , ND[j], NA[j], NW[j], NEP[j]/
                 {Ep[j,k], {b[m,j,k]}{m=0 to NA[j]}}{k=1 to NEP[j]} ]LIST
    endfor


Suppose the dictionary containing all these variables is called ``d`` and
that the counter variable ``NE`` contains the value ``6``.
The array ``E[j]`` would appear as key ``E`` in ``d`` and ``d['E']``
would be a dictionary with integer keys from ``1`` to ``6``.

Suppose we want to insert a new element after the second element.
One approach to achieve this is to convert the dictionary first
to a :class:`list`, use the Python functionality for inserting
an element into a list, and finally convert the list back to a dictionary.
The following code snippet demonstrates this approach:

.. code:: python

   vals = list(d['E'].values())
   vals.insert(2, 5)  # inserted value is 5
   d['E'] = {k: v for k, v in enumerate(vals, start=1)}


Of course, we would then also need to increase the associated
counter variable ``NE`` by one. All other arrays whose
size is determined by the loop variable ``j`` need
to be extended by one element as well.

In contrast, changing a single value can be achieved with a single
instruction, e.g.

.. code:: python

   d['E'][5] = 10

