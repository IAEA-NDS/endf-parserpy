.. _python_and_cpp_parser_sec:


Python and C++ Parser
=====================

The ``endf-parserpy`` package contains two independent ENDF parsers,
one written in pure Python and another one written
(or more appropriate, :ref:`generated <accelerated_parsing_and_writing_sec>`)
in C++. Most examples in the tutorials make use of the Python parser by
instantiating the :class:`~endf_parserpy.EndfParserPy` class. However,
the C++ parser implemented in the :class:`~endf_parserpy.EndfParserCpp`
class is **much faster** and functionally equivalent,
apart from the fact that it does not support some very specific initialization arguments.
In other words, the C++ parser returns exactly the same nested Python dictionary
as the Python parser. Also, when you serialize a Python dictionary to the
ENDF format, the output of both parsers is exactly the same, character by character.

Therefore, it is recommended to use the C++ parser and only fall back on the
Python parser if the C++ parser is not available or some very specific
behavior has been requested that is only supported by the Python parser.
To help with the selection of the appropriate parser,
the :class:`~endf_parserpy.EndfParserFactory` class can automatically
select the right parser according to the user-supplied
initialization arguments. A parser object can be obtained by

.. code:: Python

   from endf_parserpy import EndfParserFactory
   parser = EndfParserFactory.create()

Without any initialization arguments, the faster C++ parser will be selected
if available, otherwise the Python parser. If the method needs to fall back
on the Python parser, it will issue a :exc:`UserWarning` informing
the user that parsing and writing will be slow. This warning message
can be suppressed by using an additional argument:

.. code:: Python

   parser = EndfParserFactory.create(warn_slow=False)


In addition, this function can take any arguments that are supported
by the :class:`~endf_parserpy.EndfParserPy` or
the :class:`~endf_parserpy.EndfParserCpp` class.
It will then select the appropriate parser according to argument compatibility.
For instance, using the ``loglevel`` argument, not supported by
the C++ parser, will force the selection of the Python parser:

.. code:: Python

   from endf_parserpy import EndfParserPy
   parser = EndfParserFactory.create(loglevel=30)
   assert type(parser) = EndfParserPy

From the viewpoint of a developer, it may be pertinent to have some
guarantee that initialization arguments are compatible with both
the Python and the C++ parser to avoid depending on a specific
parser. Argument compatibility can be enforced by the
``require_compat`` argument:

.. code:: Python

   parser = EndfParserFactory.create(require_compat=True)

With this option being true, parser instantiation will fail for
arguments not compatible with both parser types,
raising a :exc:`ValueError` exception. For instance,

.. code:: Python

   parser = EndfParserFactory.create(require_compat=True, loglevel=20)

will fail as ``loglevel`` is only supported by the Python parser.
Without the ``require_compat=True`` argument, the method would return
a Python parser object (instance of :class:`~endf_parserpy.EndfParserPy`).

Finally, it is also possible to manually select the parser type by
supplying the ``select`` argument. Instead of the default,
``select="fastest"``, one can also use ``"python"`` for the Python and
``"cpp"`` for the C++ parser, for instance:

.. code:: Python

   parser = EndfParserFactory.create(select="cpp")

This invocation is equivalent to ``parser = EndfParserCpp()``.

In summary, the :meth:`endf_parserpy.EndfParserFactory.create` method
helps the user to pick the best available parser type and provides
informative error messages if something goes wrong. Disregarding the
implemented selection logic for a moment, this function is equivalent to

.. code:: Python

   from endf_parserpy import EndfParserPy
   parser = EndfParserPy(...)

if the Python parser (:class:`~endf_paserpy.EndfParserPy`) is selected or

.. code:: Python

   from endf_parserpy import EndfParserCpp
   parser = EndfParserCpp(...)

if the C++ parser (:class:`~endf_parserpy.EndfParserCpp`) is selected
As described above, the selection of the parser
depends on the availability of the C++ parser and whether the arguments
provided to :class:`~endf_parserpy.EndfParserFactory` are supported by the
C++ parser.
