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
from endf_parserpy import BasicEndfParser
parser = BasicEndfParser()
endf_file = 'testdata/n_2925_29-Cu-63.endf'
endf_dic = parser.parsefile(endf_file)
```
The variable `endf_dic` contains a nested dictionary that
exposes all the fields and arrays described in
the [ENDF-6 formats manual].
You can explore it by using the `.keys()` method, e.g.,
```
endf_dic.keys()
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

### Precision control for ENDF file output

Some options can be provided to increase the
precision of outputted ENDF files:
```
from endf_parserpy import BasicEndfParser
parser = BasicEndfParser(prefer_noexp=True,
    abuse_signpos=True, skip_intzero=True)
parser.writefile(endfout_filepath)
```

### Convenience functions

There are a few user convenience functions available, e.g.,
```
from endf_parserpy import (
    locate, get_endf_values, list_parsed_sections,
    list_unparsed_sections, show_content)
# locate all variables with name AWR
locations = locate(endf_dic, 'AWR')
values = get_endf_values(endf_dic, locations)
# show the content of some part of the file
show_content(endf_dic[1][451])
# obtain all parsed and unparsed sections
list_parsed_sections(endf_dic)
list_unparsed_sections(endf_dic)
```

### Deleting, substituting, modifying ENDF files

Basic functionality to deal with Python dictionaries
can be used to achieve these tasks.
The following example code demonstrates how to
delete a section:
```
from endf_parserpy import BasicEndfParser
parser = BasicEndfParser()
endf_dic = parser.parsefile(endf_file)
# delete MF1/MT451
del endf_dic[1][451]
# delete MF3
del endf_dic[3]
```
Substituting a section by one from another
ENDF file can be done like this:
```
from copy import deepcopy
endf_dic1 = parser.parsefile(endf_filepath1)
endf_dic2 = parser.parsefile(endf_filepath2)
endf_dic1[3][1] = deepcopy(endf_dic2[3][1])
```
Modifying a number is very easy and can be
achieved by, e.g.,
```
endf_dic[1][451]['AWR'] = 63
```

### ENDF file comparison

If two files are believed to be equivalent or have only
minor differences, they can be compared in the following way:
```
from endf_parserpy import BasicEndfParser
from endf_parserpy.debugging_utils import compare_objects
parser = BasicEndfParser()
endf_dic1 = parser.parsefile(endf_filepath1)
endf_dic2 = parser.parsefile(endf_filepath2)
compare_objects(endf_dic1, endf_dic2, fail_on_diff=False)
```

### Converting between ENDF and JSON files

Equivalent JSON files can be produced from ENDF files.
```
from endf_parserpy import BasicEndfParser
import json
parser = BasicEndfParser()
endf_dic = parser.parsefile(endf_filepath)
with open('endf_file.json', 'w') as f:
    json.dump(endf_dic, f, indent=2)
```

To convert a JSON file back to an ENDF file, you can
use this code:
```
from endf_parserpy.user_tools import sanitize_fieldname_types
with open('endf_file.json', 'r') as f:
    endf_dic = json.load(f)
sanitize_fieldname_types(endf_dic)
parser.writefile('endf_out.endf', endf_dic)
```

## Testing

The development of this package relies on `pytest` to ensure
the proper implementation of the ENDF-6 recipes. As most of
the recipes have already been implemented, the testing
functionality can be also used to validate ENDF-6 formatted
files. For a convenient workflow, install the Python package
`poetry`, clone this repository, and create a virtual environment
with all dependencies:
```
pip install poetry
git clone https://github.com/iaea-nds/endf-parserpy
cd endf-parserpy
poetry install
```
To start a testing session, change into the directory
`tests` within the repository directory and run
```
poetry shell
```
Now you can check if endf-parserpy is able to parse
ENDF files in a directory `<endfdir>` by executing
```
pytest --endfdir=<endfdir> -k test_endf_parserpy_never_fails
```
This command will read and check all ENDF files
with the file ending `.endf` in the specified directory.
Additional available arguments are:

- `--endffile=<endffile>` to only test a single ENDF file within `<endfdir>`.
- `--mf=<mfnum>` will restrict parsing to the MF section `<mfnum>`
- `--ignore_zero_mismatch=false` to let the conversion fail for non-zero fields in the ENDF file if the ENDF-6 format specifies them to be zero.
- `--ignore_number_mismatch=true` will lead to less strict checking that tolerates any non-zero number in the ENDF file contradicting the expected number
                                  in the ENDF recipe if the latter number is suffixed by a question mark.
- `--ignore_varspec_mismatch=true` will lead to less strict checking that tolerates any inconsistent variable specification if the variable name in the
                              ENDF recipe is suffixed by a question mark.

## Acknowledgments

The IAEA consultant Daniel Lopez Aldama helped with his great knowledge
on the ENDF-6 format to guide through the complexities of the format
in numerous discussions and also greatly contributed to the
debugging of the recipe files.

## Legal note

This code is distributed under the MIT license, see the
accompanying license file for more information.

Copyright (c) International Atomic Energy Agency (IAEA)

[ENDF-6 formats manual]: https://oecd-nea.org/dbdata/data/manual-endf/endf102.pdf
