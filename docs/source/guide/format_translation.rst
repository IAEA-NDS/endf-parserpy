.. _guide_format_translation:

Translating ENDF-6 to JSON
==========================

The `ENDF-6 format <https://doi.org/10.2172/1425114>`_
is a very specific format that is exclusively employed in the
nuclear data domain. Only a few
software packages exist to comprehensively
access data stored in an ENDF-6 file.
The translation of ENDF-6 formatted data
into formats that are widely used in the IT domain,
such as `JSON <https://en.wikipedia.org/wiki/JSON>`_,
enables the usage of standard functionality of various
programming languages to access and manipulate the data.

Therefore, one approach to dealing with ENDF-6 files
consists of converting ENDF-6 files into the JSON
format, apply the desired operations on the JSON
files, and afterwards translate the JSON files back
into the ENDF-6 format. Another possible
use case could be the storage of JSON objects
with nuclear data in documented-oriented databases, such as
`CouchDB <https://couchdb.apache.org/>`_ or
`MongoDB <https://www.mongodb.com/>`_ to leverage
their flexible search and access capabilities.

The conversion of an ENDF-6 file to a JSON file
can be accomplished by a couple of lines of Python code:

.. code:: Python

   from endf_parserpy import EndfParserPy
   import json
   parser = EndfParserPy()
   endf_dict = parser.parsefile('input.endf')
   with open('output.json', 'w') as f:
       json.dump(endf_dict, f, indent=2)

In this code snippet, an ENDF-6 file is read
into a dictionary ``endf_dict`` and then
basic Python functionality utilized to
dump the content of ``endf_dict`` into
a JSON file.

.. note::

   Keys in dictionaries with ENDF-6 data are
   either of type :class:`int` or :class:`str`. However,
   the JSON format only supports keys of type :class:`str`.
   The :func:`json.dump` method converts :class:`int` keys
   automatically to :class:`str` before writing them
   to a JSON file.


The reverse process, converting a JSON file to an ENDF-6 formatted file,
is equally simple. The following code snippet accomplishes
this conversion:

.. code:: Python

    from endf_parserpy.utils.user_tools import sanitize_fieldname_types
    with open('input.json', 'r') as f:
        endf_dict = json.load(f)

    sanitize_fieldname_types(endf_dict)
    parser.writefile('output.endf', endf_dict)

Here, basic Python functionality is employed to
read the data from the JSON file into a dictionary
``endf_dict``.
Afterwards, the invocation of :func:`~endf_parserpy.sanitize_fieldname_types`
converts keys of type :class:`str` that contain integer values back to
type :class:`int`. Finally, the :func:`~endf_parserpy.EndfParserPy.writefile`
method of the :class:`~endf_parserpy.EndfParserPy` object is called to write
the data stored in the  dictionary ``endf_dict`` to an ENDF-6 file.
