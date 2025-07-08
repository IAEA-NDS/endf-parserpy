# endf-parserpy - an ENDF-6 toolkit for Python

`endf-parserpy` is a Python package for reading
and writing [ENDF-6](https://doi.org/10.2172/1425114) files.
This functionality in combination with Python's
powerful facilities for data handling enables you to
perform various actions on ENDF-6 files, such as:

- Easily access any information
- Modify, delete and insert data
- Perform format validation
- Convert from and to other file formats, such as JSON
- Merge data from various ENDF-6 files into a single one
- Compare ENDF-6 files with meaningful reporting on differences
- Construct ENDF-6 files from scratch


Many of these actions can be performed via the command line.
The support for the [ENDF-6 format]((https://doi.org/10.2172/1425114))
is comprehensive and some special NJOY2016 output formats
are also supported.
The package has been tested on the various sublibraries
of the major nuclear data libraries, such as
[ENDF/B](https://www.nndc.bnl.gov/endf/),
[JEFF](https://www.oecd-nea.org/dbdata/jeff/),
and [JENDL](https://wwwndc.jaea.go.jp/jendl/jendl.html).
Note that the package does not support several materials
in a single ENDF-6 file.


## Install endf-parserpy

This package is available on the
[Python Package Index](https://pypi.org/project/endf-parserpy/)
and can be installed using ``pip``:

```sh
python -m pip install endf-parserpy --upgrade
```


## Documentation

The documentation is available online
[@readthedocs](https://endf-parserpy.readthedocs.io).
Consider the ``README.md`` in the ``docs/`` subdirectory
for instructions on how to generate the help files locally.


## Simple example

The following code snippet demonstrates
how to read an ENDF-6 file, change the
``AWR`` variable in the MF3/MT1 section
and write the modified data to a new
ENDF-6 file:

```
from endf_parserpy import EndfParserFactory
parser = EndfParserFactory.create()
endf_dict = parser.parsefile('input.endf')
endf_dict[3][1]['AWR'] = 99.99
parser.writefile('output.endf', endf_dict)
```


## Citation

If you want to cite this package,
please use the following reference:

```
G. Schnabel, D. L. Aldama, R. Capote, "How to explain ENDF-6 to computers: A formal ENDF format description language", arXiv:2312.08249, DOI:10.48550/arXiv.2312.08249
```


## License

This code is distributed under the MIT license augmented
by an IAEA clause, see the accompanying license file for more information.

Copyright (c) International Atomic Energy Agency (IAEA)


## Acknowledgments

Daniel Lopez Aldama made significant contributions
to the development of this package. He debugged the
ENDF-6 recipe files and helped in numerous discussions
to convey a good understanding of the technical details of
the ENDF-6 format that enabled the creation of this package.
