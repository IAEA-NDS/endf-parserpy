import os
import subprocess
import sys


def get_version_from_init():
    version_file = "endf_parserpy/__init__.py"
    version = None
    if os.path.exists(version_file):
        with open(version_file, "r") as file:
            for line in file:
                if line.strip().startswith("__version__"):
                    version = line.split("=")[1].strip().strip("\"'")
                    break
    return version


def create_git_tag(version):
    tag_name = f"v{version}"
    # Check if the tag already exists
    existing_tags = subprocess.check_output(["git", "tag"], text=True).split()
    if tag_name in existing_tags:
        print(f"Tag {tag_name} already exists.")
        sys.exit(1)

    # Create the tag
    try:
        subprocess.check_call(
            ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"]
        )
        print(f"Tag {tag_name} created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create tag {tag_name}: {e}")
        sys.exit(1)


def main():
    version = get_version_from_init()
    if not version:
        print("Could not find __version__ in __init__.py")
        sys.exit(1)

    create_git_tag(version)
    sys.exit(0)


if __name__ == "__main__":
    main()
