## Documentation

The documentation is available online
[@readthedocs](https://endf-parserpy.readthedocs.io).
If you want to generate the documentation locally
on your computer, follow these steps:

1) Change into the `endf-parserpy/docs` folder
2) Create a virtual environment via `python -m venv docenv`
3) Activate the environment: for Linux and MacOS, run `source docenv/bin/activate` and for Windows `docenv\Scripts\activate.bat`
4) Install the requirements to build the documentation: `pip install -r requirements.txt`
5) Install the `endf-parserpy` package: `pip install ../`
6) Build the documentation by running `make html`
7) Deactivate the virtual environment by running `deactivate`

After these steps, the `html` files are available in `build/html`.
The start page of the documentation is accessible via `build/html/index.html`.
There are also other output options (e.g. pdf), and you can see the available
options by running `make` without additional arguments.
