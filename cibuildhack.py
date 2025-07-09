import fileinput
import os

# Define the environment variables
install_endf_parserpy_cpp = os.getenv("INSTALL_ENDF_PARSERPY_CPP", "optional")
install_endf_parserpy_cpp_optim = os.getenv("INSTALL_ENDF_PARSERPY_CPP_OPTIM", None)

# Path to the setup.py file
setup_file = "setup.py"

# Replace the lines in the setup.py file
with fileinput.FileInput(setup_file, inplace=True) as file:
    for line in file:
        # Replace `cibuildwheel_hack` assignment
        line = line.replace("cibuildwheel_hack = False", "cibuildwheel_hack = True")

        # Replace the placeholders with environment variables
        line = line.replace("__INSTALL_ENDF_PARSERPY_CPP__", install_endf_parserpy_cpp)
        line = line.replace(
            "__INSTALL_ENDF_PARSERPY_CPP_OPTIM__", install_endf_parserpy_cpp_optim
        )

        # Write the modified line back to the file
        print(line, end="")
