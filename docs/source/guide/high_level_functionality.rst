High-level Functionality
========================

The paramount focus of endf-parserpy
is to provide a low-level interface to
ENDF-6 formatted data, which includes
reading and writing entire ENDF-6 formatted files
as well as convenient read and write access to any
piece of data stored in an ENDF-6 file.

Some nuclear quantities are stored in compact
but not very human-friendly representations,
such as the R-matrix formalism
employed for the storage of cross sections
(and associated angular disributions) in the
resonance region and the storage of
angular distributions as Legendre coefficients.
For the plotting of these quantities, however,
angular distributions as functions of angle
are easier to understand.
At present, endf-parserpy doesn't include any
functionality to transform the compact and
more abstract representations into human-friendly
ones.

In this section, we want to discuss one possible
approach to the implementatoin of high-level functionality.

A nice feature of endf-parserpy is that it keeps
the bidirectional link between data in the ENDF-6
format and the same data in a Python dictionary,
permitting the
reliable translation from one representation into
the other. It would be a pertinent design feature if any
high-level functionality also preserves the
link between the original data and the
derived/simplified representation.
While it won't be possible to maintain a
bidirectional link due to the loss of 
information in all cases, e.g. when calculating a group-wise
cross section from point-wise cross sections,
it will certainly be possible in some cases.
The advantage would be that a user could change the
nuclear quantities using the human-friendly representation,
and the modifications could be automatically propagated back
to the original low-level representation.

We want to demonstrate one possibility to accomplish
this bidirectional linking by implementing a prototype class for linear
interpolation of cross sections in MF3. 
The class should support the computation of interpolated values
at energies requested by the user and also enable the user to update the cross section
values at the mesh points.
We will make use of the :class:`~endf_parserpy.accessories.EndfVariable` class to
preserve the link to the original data in the ENDF-6 dictionary.
A simple prototype class implementation
could look something like this:


.. code:: python

    import numpy as np
    from copy import copy 
    from endf_parserpy.accessories import EndfVariable


    class LinearCrossSectionInterpolation:

        def __init__(self, xarr, yarr, nbt_arr, int_arr):
            if not (isinstance(xarr, EndfVariable)
                    and isinstance(yarr, EndfVariable)
                    and isinstance(nbt_arr, EndfVariable)
                    and isinstance(int_arr, EndfVariable)):
                raise TypeError('expecting EndfVariables')
            self._xarr = xarr
            self._yarr = yarr
            self._nbt_arr = nbt_arr
            self._int_arr = int_arr
            self.table = (xarr.value, yarr.value)

        @property
        def table(self):
            return copy(self._xarr.value), copy(self._yarr.value)

        @table.setter
        def table(self, value):
            x = list(value[0])
            y = list(value[1])
            if len(x) != len(y):
                raise IndexError('length of x and y differs')
            if not isinstance(x, list) or not isinstance(y, list):
                raise TypeError('both x and y must be a `list`')
            self._xarr.value = x
            self._yarr.value = y
            self._nbt_arr.value = [2]
            self._int_arr.value = [len(x)]

        def __call__(self, xout):
            return np.interp(xout, self._xarr.value, self._yarr.value)


To see what this class is accomplishing, let's set up an example
that uses it for the linear interpolation of a total
cross section (MF3/MT1):

.. code:: python

   from endf_parserpy import EndfParser
   from endf_parserpy.accessories import EndfVariable
   
   parser = EndfParser()
   endf_dict = parser.parsefile('input.endf')

   xvar = EndfVariable('3/1/xstable/E', endf_dict) 
   yvar = EndfVariable('3/1/xstable/xs', endf_dict)
   int_arr = EndfVariable('3/1/xstable/INT', endf_dict)
   nbt_arr = EndfVariable('3/1/xstable/INT', endf_dict)

   interpobj = LinearCrossSectionInterpolation(xvar, yvar, nbt_arr, int_arr) 


After loading the data of an ENDF-6 file into the dictionary ``endf_dict``,
:class:`~endf_parserpy.accessories.EndfVariable` objects are created and
linked to the locations of the variables associated with the total cross
section in MF3/MT1. The objects ``xvar``, ``yvar``, ``int_arr`` and ``nbt_arr``
serve the same purpose
as regular variables: They can flow through the program logic to support
a certain analysis or data processing.
We use these variables to set up a ``LinearCrossSectionInterpolation`` object
that we associate with the variable ``interpobj``.
This object allows us to compute cross section values at arbitrary
energies within the permissible energy range, e.g.

.. code:: python

   interp_ens = [10, 100, 1000]
   interp_xs = interpobj(interp_ens)


Importantly, also the energy mesh and cross sections at the mesh
points can be updated, e.g.:

.. code:: python

   new_ens = [1, 50, 100]
   new_xs = [20, 40, 60]
   interpobj.table = (new_ens, new_xs)

Because the variables used by the ``LinearCrossSectionInterpolationClass``
are :class:`~endf_parserpy.accessories.EndfVariable` objects, any adjustment performed using an
object of that class will also lead to a corresponding update
of the ``endf_dict``.

This approach represents one possible way how
higher-level functionality could be implemented, which is to some
extent decoupled from the detailed structure of the dictionary
with ENDF-6 data. Yet, modifications via the high-level object
will be propagated back to the original dictionary via the
:class:`~endf_parserpy.accessories.EndfVariable` mechanism.

