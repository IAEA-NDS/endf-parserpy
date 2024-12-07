.. currentmodule:: endf_parserpy.utils.math_utils

math_utils
==========

The ``endf_parserpy.utils.math_utils`` module implements
functions for basic mathematical operations on scalars
and iterable objects (e.g. :class:`list`). Operations
applied to two iterable objects are performed element-wise.
Operations between a scalar and an iterable object are also
performed element-wise.
The :class:`~endf_parserpy.EndfFloat` class
stores a :class:`float` along with its string representation.

The following facilities are provided by the ``math_utils`` module:

.. autoclass:: EndfFloat
   :members:

.. autofunction:: math_isclose

.. autofunction:: math_op

.. autofunction:: math_mul

.. autofunction:: math_div

.. autofunction:: math_mod

.. autofunction:: math_add

.. autofunction:: math_sub

.. autofunction:: math_allclose
