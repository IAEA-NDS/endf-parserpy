.. currentmodule:: endf_parserpy.utils.debugging_utils

debugging_utils
===============

The ``endf_parserpy.utils.debugging_utils`` module implements
functionality pertinent for comparing nested dictionaries
as obtained by the ``parsefile()`` method of the
:doc:`EndfParser <../endf_parser/endf_parser_class>` class.
It also provides a class :ref:`TrackingDict <tracking_dict_class_doc>`
which helps ensure that a user-created dictionary with ENDF-6 data is properly
set up and written to a file via the ``.writefile()`` method.

The following facilities are provided by the debugging_utils module:

.. toctree::
   :maxdepth: 1

   compare_objects
   tracking_dict_class

