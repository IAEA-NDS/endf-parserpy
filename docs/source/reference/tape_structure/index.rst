.. currentmodule:: endf_parserpy

tape_structure
--------------

.. automodule:: endf_parserpy.utils.tape_structure
   :no-members:

.. currentmodule:: endf_parserpy

.. autoclass:: TapeStructure
   :members: from_spec, send, fend, repeat, mt_ascending, is_endf6, to_spec, cpp_options

.. autodata:: endf_parserpy.utils.tape_structure.ENDF6
   :no-value:

.. autofunction:: section_label

.. autofunction:: to_list_form

.. autofunction:: to_dict_form

The tape structure of a flavor is returned by:

.. autofunction:: endf_parserpy.endf_recipes.get_tape_structure
