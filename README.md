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

Noteworthy, this package leverages a formal ENDF format
description, closely following the notation of the
ENDF-6 formats manual, to read, write and verify ENDF-6 formatted files.
The capabilities of this package can therefore be extended by
adding or modifying ENDF recipe files. The already implemented recipe files
can be inspected [here](https://github.com/iaea-nds/endf-parserpy/tree/main/endf_parserpy/endf_recipes).

A detailed explanation of the formal ENDF description language used
in the ENDF recipe files is given in the following [arxiv preprint](https://arxiv.org/abs/2312.08249):
```
G. Schnabel, D. L. Aldama, R. Capote, "How to explain ENDF-6 to computers: A formal ENDF format description language", arXiv:2312.08249, DOI:10.48550/arXiv.2312.08249
```
Please use this reference for citation if you find this package useful.


[ENDF-6 formats manual]: https://doi.org/10.2172/1425114

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

Alternatively, you can download this repository and
update the `PYTHONPATH` environment variable on the
command line:
```
export PYTHONPATH="<path-of-repository-directory>"
```
Make sure that the only two depdendencies of this
package, the package `lark` and `appdirs` are installed, e.g., by
```
pip install lark
pip install appdirs
```

## Basic usage

The `example/` folder contains example scripts to
demonstrate how this package can be used.
Two ENDF files are provided in the `tests/testdata`
directory. Change into this directory if you want
to run all the following code snippets verbatim.
```
from endf_parserpy import BasicEndfParser
parser = BasicEndfParser()
endf_file = 'n_2925_29-Cu-63.endf'
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

The following subsections provide short code snippets
for common operations or interactions with ENDF files.

### Updating description and MT451 dictionary

In case the description in MF1/MT451 or
any other section were modified in ways that may
result in a different number of lines in the ENDF file,
it is better to use the `ExtEndfParser` class.
In addition to the methods of the `BasicEndfParser`,
it offers a few convenience methods, e.g.,
```
from endf_parserpy import ExtEndfParser
parser = ExtEndfParser()
endf_dic = parser.parsefile(endf_file)
descr = parser.get_description(endf_dic)
print(descr)
newinfo = 'We tweaked the data in MF3...\nJust joking!'
parser.insert_description(endf_dic, newinfo, after_line=5)
parser.writefile('modified_file.endf', endf_dic)
```

### Selective parsing

If one is only interested in specific MF/MT numbers,
it is possible to include or exclude the desired sections
to accelerate the parsing process.
For instance, only including MF1/MT451 and MF3 can be
done by:
```
endf_dic = parser.parsefile('n_2925_29-Cu-63.endf', include=(3, (1,451)))
```
All other sections will then only be available as strings. To include a
single section, use `include=(MF,)` or `include=((MF,MT),)`.

Excluding sections can be done analogously. To parse every section
except the specified sections use:
```
endf_dic = parser.parsefile('n_2925_29-Cu-63.endf', exclude=(3, (1,451)))
```
You can always retrieve a list of the parsed and unparsed sections by:
```
from endf_parserpy.user_tools import list_parsed_sections, list_unparsed_sections
list_parsed_sections(endf_dic)
list_unparsed_sections(endf_dic)
```

### Convenience functions

There are a few user convenience functions available.
This code snippet finds all locations where a variable
of a specific name appears and shows their values:
```
from endf_parserpy.user_tools import locate, get_endf_values
locations = locate(endf_dic, 'AWR')
values = get_endf_values(endf_dic, locations)
```
The following function aims to provide a nicer
visual representation of the content of a section
(or any subsection within):
```
from endf_parserpy.user_tools import show_content
show_content(endf_dic[1][451])
```

### Deleting, substituting, modifying MF/MT sections

Basic functionality to deal with Python dictionaries
can be used to delete, substitute or modify sections
in ENDF files.
To delete a section, e.g., MF3, you can use
```
del endf_dic[3]
```
To delete a subsection, e.g., MF1/MT451, execute
```
del endf_dic[1][451]
```

Substituting a section by one from another
ENDF file can be done like this:
```
from copy import deepcopy
endf_dic1 = parser.parsefile('n_2925_29-Cu-63.endf')
endf_dic2 = parser.parsefile('n_3025_30-Zn-64.endf')
endf_dic1[3][1] = deepcopy(endf_dic2[3][1])
parser.writefile('replaced.endf', endf_dic1)
```

Modifying a number is very easy and can be
achieved by, e.g.,
```
endf_dic[1][451]['AWR'] = 63
```

### Converting between ENDF and JSON files

Equivalent JSON files can be produced from ENDF files
with this code snippet:
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
parser.writefile('endf_out.endf', endf_dic, overwrite=True)
```
Keys of type integer in Python are converted to type string
by `json.dump`. The function `sanitize_fieldname_types` restores the
integer type of the keys after reading from a JSON file and
before passing them to `parser.writefile`.

### Precision control for ENDF file output

Some options can be provided to increase the
precision of outputted ENDF files by passing
specific options to the constructor:
```
from endf_parserpy import BasicEndfParser
parser = BasicEndfParser(prefer_noexp=True,
    abuse_signpos=True, skip_intzero=True)
parser.writefile('endf_output.endf', endf_dic)
```
If you prefer better compatibility for languages
different from Fortran at the cost of losing
one digit precision, you can also add
`keep_E=True` to the argument list.

### Comparing ENDF files

If two files are believed to be equivalent or to have only
minor differences, they can be compared in the following way:
```
from endf_parserpy import BasicEndfParser
from endf_parserpy.debugging_utils import compare_objects
parser = BasicEndfParser()
endf_dic1 = parser.parsefile('n_2925_29-Cu-63.endf')
endf_dic2 = parser.parsefile('n_3025_30-Zn-64.endf')
compare_objects(endf_dic1, endf_dic2, fail_on_diff=False)
```

You can also add the `atol` and `rtol` arguments to the
`compare_objects` call to control the absolute and relative
tolerance, respectively, in the comparison of floating point
numbers. These arguments have the same meaning as for the
`numpy.isclose` function. The default values are
`atol=1e-8` and `rtol=1e-6`. You may want to use this function
to check that you don't lose too much precision in a reading,
adjustment, writing sequence:
```
endf_dic1 = parser.parsefile('n_2925_29-Cu-63.endf')
# ...
# introduce some modifications in endf_dic1,
# e.g., changing numbers, substituting sections
endf_out = 'modified_n_2925_29-Cu-63.endf'
parser.writefile(endf_out, endf_dic1)
endf_dic2 = parser.parsefile(endf_out)
compare_objects(endf_dic1, endf_di2, fail_on_diff=False)
```
If inacceptable differences are detected, you may want
use the available arguments discussed
[above](#precision-control-for-endf-file-output) to
increase the output precision.

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
