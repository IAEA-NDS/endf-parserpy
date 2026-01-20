import fileinput
import os

# Define the environment variables
install_endf_parserpy_cpp = os.getenv("INSTALL_ENDF_PARSERPY_CPP", None)
install_endf_parserpy_cpp_optim = os.getenv("INSTALL_ENDF_PARSERPY_CPP_OPTIM", None)

# Path to the setup.py file
setup_file = "setup.py"

# Replace the lines in the setup.py file
with fileinput.FileInput(setup_file, inplace=True) as file:
    for line in file:
        # Replace `cibuildwheel_hack` assignment
        line = line.replace("cibuildwheel_hack = False", "cibuildwheel_hack = True")

        # Replace the placeholders with environment variables.
        # If variables not set, omit the entire line
        # (See setup.py#147 for reason)
        if "__INSTALL_ENDF_PARSERPY_CPP__" in line:
            if install_endf_parserpy_cpp is None:
                line = None
            else:
                line = line.replace(
                    "__INSTALL_ENDF_PARSERPY_CPP__", install_endf_parserpy_cpp
                )

        elif "__INSTALL_ENDF_PARSERPY_CPP_OPTIM__" in line:
            if install_endf_parserpy_cpp_optim is None:
                line = None
            else:
                line = line.replace(
                    "__INSTALL_ENDF_PARSERPY_CPP_OPTIM__",
                    install_endf_parserpy_cpp_optim,
                )

        # Write the modified line back to the file
        if line is not None:
            print(line, end="")
