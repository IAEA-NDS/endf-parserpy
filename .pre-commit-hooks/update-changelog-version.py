import re
import os
import subprocess
import sys


VERSION_FILE = os.path.join("endf_parserpy", "__init__.py")
CHANGELOG_FILE = "CHANGELOG.md"


def get_version(file):
    rex = re.compile('^ *__version__ *= *"([^"]*)" *$')
    with open(file, "r") as f:
        for line in f:
            m = rex.match(line)
            if m:
                return m.group(1)
    raise IndexError("__version__ string not found")


def get_changelog_versions(file):
    rex = re.compile(r"^## \[([^]]*)\]")
    versions = []
    with open(file, "r") as f:
        for line in f:
            m = rex.match(line)
            if m:
                versions.append(m.group(1))
    return versions


def update_changelog_version(file, version):
    lines_out = []
    found = False
    with open(file, "r") as f:
        for line in f:
            lines_out.append(line)
            if line.rstrip() == "## [Unreleased]":
                found = True
                lines_out.append("\nNo changes yet.\n")
                lines_out.append(f"\n## [{version}]\n")
    if not found:
        raise IndexError(f"Unreleased section not found in `{file}`")
    with open(file, "w") as f:
        f.writelines(lines_out)


def stage_changelog_file():
    subprocess.run(["git", "add", CHANGELOG_FILE])


def main():
    current_version = get_version(VERSION_FILE)
    changelog_versions = get_changelog_versions(CHANGELOG_FILE)
    if current_version not in changelog_versions:
        print(
            f"{CHANGELOG_FILE} does not contain version {current_version}, updating..."
        )
        update_changelog_version(CHANGELOG_FILE, current_version)
        stage_changelog_file()
        sys.exit(1)


if __name__ == "__main__":
    main()
