# endf-parserpy - an ENDF-6 toolkit for Python

[![PyPI version](https://img.shields.io/pypi/v/endf-parserpy)](https://pypi.org/project/endf-parserpy/)
[![Python versions](https://img.shields.io/pypi/pyversions/endf-parserpy)](https://pypi.org/project/endf-parserpy/)
[![Tests](https://github.com/IAEA-NDS/endf-parserpy/actions/workflows/test_package.yml/badge.svg)](https://github.com/IAEA-NDS/endf-parserpy/actions/workflows/test_package.yml)
[![Documentation](https://readthedocs.org/projects/endf-parserpy/badge/?version=latest)](https://endf-parserpy.readthedocs.io/en/latest/)

`endf-parserpy` is a Python package for reading
and writing [ENDF-6](https://doi.org/10.2172/1425114) files.
This functionality in combination with Python's
powerful facilities for data handling enables you to
perform various actions on ENDF-6 files, such as:

- Easily access any information
- Modify, delete and insert data
- Perform format validation
- Convert to and from other file formats, such as JSON
- Merge data from various ENDF-6 files into a single one
- Read and write files bundling several materials (tapes)
- Compare ENDF-6 files with meaningful reporting on differences
- Construct ENDF-6 files from scratch


Many of these actions can also be performed from the command line
through the `endf-cli` tool.

The support for the ENDF-6 format is comprehensive, and some special
NJOY2016 output formats are supported as well. The package has been
tested on the various sublibraries of the major nuclear data
libraries, such as
[ENDF/B](https://www.nndc.bnl.gov/endf/),
[JEFF](https://www.oecd-nea.org/dbdata/jeff/),
and [JENDL](https://wwwndc.jaea.go.jp/jendl/jendl.html).
Files that bundle several materials — including PENDF tapes
that repeat the same material at different temperatures — are
supported both as plain lists of materials and through a lazy,
memory-bounded `EndfFile` interface for large files.
Parsing and writing have been extensively optimized; the C++ backend
processes ENDF-6 data at rates of up to several hundred megabytes per
second.


## Install endf-parserpy

This package is available on the
[Python Package Index](https://pypi.org/project/endf-parserpy/)
and can be installed using `pip`:

```sh
python -m pip install endf-parserpy --upgrade
```


## Documentation

The documentation is available online
[@readthedocs](https://endf-parserpy.readthedocs.io).
See the `README.md` in the `docs/` subdirectory
for instructions on building the documentation locally.


## Simple example

The following code snippet demonstrates
how to read an ENDF-6 file, change the
`AWR` variable in the MF3/MT1 section
and write the modified data to a new
ENDF-6 file:

```python
from endf_parserpy import EndfParserFactory
parser = EndfParserFactory.create()
# fastest variant, returning arrays of numbers as numpy arrays:
# parser = EndfParserFactory.create(array_type="numpy")
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
