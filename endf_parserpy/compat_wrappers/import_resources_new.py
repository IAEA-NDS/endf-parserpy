# The functions in this file are taken from [1] and [2]
# as suggested in [3] to expose the revised importlib.resources
# API introduced in Python 3.9 under the legacy names.
# [1]: https://github.com/python/importlib_resources/blob/66ea2dc7eb12b1be2322b7ad002cefb12d364dff/importlib_resources/_legacy.py
# [2]: https://github.com/python/importlib_resources/blob/66ea2dc7eb12b1be2322b7ad002cefb12d364dff/importlib_resources/_common.py
# [3]: https://importlib-resources.readthedocs.io/en/latest/using.html#migrating-from-legacy
import os
import importlib.resources as r


def _normalize_path(path):
    """Normalize a path by ensuring it is a string

    If the resulting string contains path separators, an exception is raised.
    """
    str_path = str(path)
    parent, file_name = os.path.split(str_path)
    if parent:
        raise ValueError(f"{path!r} must be only a file name")
    return file_name


def is_resource(package, name):
    """True if `name` is a resource inside `package`."""
    resource = _normalize_path(name)
    return any(
        traversable.name == resource and traversable.is_file()
        for traversable in r.files(package).iterdir()
    )


def open_text(package, resource, encoding="utf-8", errors="strict"):
    """Return a file-like object opened for text reading of the resource."""
    return (r.files(package) / _normalize_path(resource)).open(
        "r", encoding=encoding, errors=errors
    )


def open_binary(package, resource):
    """Return a file-like object opened for binary reading of the resource."""
    return (r.files(package) / _normalize_path(resource)).open("rb")
