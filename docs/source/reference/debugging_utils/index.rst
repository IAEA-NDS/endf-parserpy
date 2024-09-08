.. currentmodule:: endf_parserpy.utils.debugging_utils

debugging_utils
===============

The ``endf_parserpy.utils.debugging_utils`` module implements
functionality pertinent for comparing nested dictionaries
as obtained by the :meth:`~endf_parserpy.EndfParser.parsefile()` method of the
:class:`~endf_parserpy.EndfParser` class.
It also provides a class :class:`~endf_parserpy.utils.debugging_utils.TrackingDict`
which helps ensure that a user-created dictionary with ENDF-6 data is properly
set up and written to a file via the :meth:`~endf_parserpy.EndfParser.writefile()` method.

The following facilities are provided by the debugging_utils module:

.. toctree::
   :maxdepth: 1

   compare_objects
   tracking_dict_class

