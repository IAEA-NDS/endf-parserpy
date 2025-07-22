import sys


major = sys.version_info.major
minor = sys.version_info.minor


if (major, minor) >= (3, 9):
    from .import_resources_new import open_text, open_binary, is_resource
else:
    from importlib.resources import (
        open_text,
        open_binary,
        is_resource,
    )
