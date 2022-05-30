# endf-parserpy

This package can read the content of an 
ENDF file into a nested dictionary in Python.
It can also generate an ENDF file from
such a nested dictionary. By using additional
packages, such as the `json` package, ENDF files
can be converted from and to other container formats
as well.

Importantly, for the time being, it expects to find a single
material in an ENDF file. You can inspect the
files available in the `testdata` directory to
get a better idea of the ENDF format. The technical
specification of the format is provided in the
[ENDF formats manual](https://oecd-nea.org/dbdata/data/manual-endf/endf102.pdf).

Noteworthy, this package does not directly read
and write ENDF files, but implements an interpreter
to parse ENDF recipe files whose content closely
resembles the ENDF format specifications available
in the ENDF formats manual. The capability of this
package to read and write ENDF files can therefore  be extended by
adding ENDF recipe files.

The development of this package is at an early stage
and it has not been thoroughly tested yet. Documentation
and capabilities will be gradually extended.
Be aware that for some MF/MT sections the recipe
files are still missing or incomplete, in which
case the parser will fail. To see which MF/MT
sections have already been implemented, inspect the
[recipe files](https://github.com/iaea-nds/endf-parserpy/tree/main/endf_parserpy/endf_recipes).

## Installation

Assuming that `git` is installed, you can clone the
repository by executing the command:
```
git clone https://github.com/endf-parserpy.git
```
Afterwards, to use this package in a Python script
file, add the following lines to the beginning of your
script:
```
import sys
sys.path.append('<path-containing-endf-parserpy>')
```
The `<path-containing-endf-parserpy>` is the path
that contains the `endf-parserpy` directory.

## Basic usage

The `example/` folder contains example scripts to
demonstrate how this package can be used.
A simple example is also provided here to get you
started.
```
from endf_parserpy.end_parser import BasicEndfParser
from endf_parserpy.user_tools import locat, get_endf_values
parser = BasicEndfParser() 
endf_file = '../testdata/n_2925_29-Cu-63.endf'
endf_dic = parser.parsefile(endf_file)
# locate all variables with name AWR
locations = locate(endf_dic, 'AWR')
values = get_endf_values(endf_dic, locs)
# write back the ENDF file
parser.writefile(endf_file + '.writeback')
```

## Legal note

This code is distributed under the MIT license, see the
accompanying license file for more information.

Copyright (c) International Atomic Energy Agency (IAEA)

