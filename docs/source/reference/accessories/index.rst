.. currentmodule:: endf_parserpy.utils.accessories

accessories
===========

The ``endf_parserpy.utils.accessories`` module implements
five classes that facilitate the access to
objects in nested dictionaries by introducing
enhanced indexing functionality. The enhanced indexing
functionality, established by the
:class:`~endf_parserpy.EndfPath` class is leveraged
by the :class:`~endf_parserpy.EndfDict` and
:class:`~endf_parserpy.utils.accessories.EndfList` classes, both
derived from :class:`~endf_parserpy.utils.accessories.EndfObject`,
to enable advanced indexing into nested dictionaries and lists.
Finally, an instance of the :class:`~endf_parserpy.EndfVariable`
class serves the same purpose as a regular variable but
is kept in sync with a specific location in a nested dictionary
and the data stored there.

Read the following sections for a more detailed
description of these classes:

.. toctree::
   :maxdepth: 1

   endf_object_class
   endf_dict_class
   endf_list_class
   endf_path_class
   endf_variable_class
