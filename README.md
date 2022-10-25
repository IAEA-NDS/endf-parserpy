**Important disclaimer**:
The development of this package is at an early stage
and lacks documentation. It has been successfully tested
on neutron-induced reaction data and thermal scattering data
of several world libraries. If this package fails
on one of your files, open an issue here or send an email
to [g.schnabel@iaea.org](mailto:g.schnabel@iaea.org).

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
[ENDF-6 formats manual].

Noteworthy, this package does not directly read
and write ENDF files, but implements an interpreter
to parse ENDF recipe files whose content closely
resembles the ENDF format specifications available
in the ENDF formats manual. The capability of this
package to read and write ENDF files can therefore  be extended by
adding ENDF recipe files. The already implemented recipe files
can be inspected [here](https://github.com/iaea-nds/endf-parserpy/tree/main/endf_parserpy/endf_recipes).

## Installation

We recommend to create a virtual environment for
this package. For instance, with conda this can be done by
```
conda create -y -n endf-parserpy pip
conda activate endf-parserpy
```
To install this package using pip, run
```
pip install git+https://github.com/iaea-nds/endf-parserpy.git
```

## Basic usage

The `example/` folder contains example scripts to
demonstrate how this package can be used.
A simple example is also provided here to get you
started.
```
from endf_parserpy.endf_parser import BasicEndfParser
parser = BasicEndfParser()
endf_file = 'testdata/n_2925_29-Cu-63.endf'
endf_dic = parser.parsefile(endf_file)
```
The variable `endf_dic` contains a nested dictionary that
exposes all the fields and arrays described in
the [ENDF-6 formats manual].
You can explore it by using the `.key()` method, e.g.,
```
endf_dic.key()
# show the fields of MF2
endf_dic[2].keys()
# show the fields of MF2/MT151
endf_dic[2][151].keys()
# show the fields of MF2/MT151/isotope
endf_dic[2][151]['isotope'].keys()
# show fields of first isotope
endf_dic[2][151]['isotope'][1].keys()
```
You can make modifications to these fields and then
produce a new ENDF file:
```
parser.writefile(endf_file + '.writeback', endf_dic)
```

There are a few user convenience functions available, e.g.,
```
# locate all variables with name AWR
locations = locate(endf_dic, 'AWR')
values = get_endf_values(endf_dic, locations)
```

## Legal note

This code is distributed under the MIT license, see the
accompanying license file for more information.

Copyright (c) International Atomic Energy Agency (IAEA)

[ENDF-6 formats manual]: https://oecd-nea.org/dbdata/data/manual-endf/endf102.pdf
