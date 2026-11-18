############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/11/18
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from glob import glob
import sys
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    open_endf_file,
    parse_error_message,
    is_material_qualified,
    resolve_material_path,
    section_label_of,
    selector_of,
    export_endf_file,
)
from endf_parserpy import EndfMaterialPath


COMMAND_NAME = "replace"


def add_subparser(subparsers):
    parser_replace = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_replace)
    parser_replace.add_argument(
        "-n",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_replace.add_argument(
        "--source-path",
        dest="source_path",
        type=str,
        default=None,
        help="path to the object in the source file, when it differs from "
        "the target path (e.g. a different material selector); defaults "
        "to the target path",
    )
    parser_replace.add_argument(
        "endfpath",
        type=str,
        help="path to the object in the target file; also used for the "
        "source file unless --source-path is given",
    )
    parser_replace.add_argument(
        "sourcefile", type=str, help="file from which object should be retrieved"
    )
    parser_replace.add_argument(
        "destfile",
        nargs="+",
        type=str,
        help="file(s) in which information should be inserted/replaced",
    )


def _fail(message):
    """Print a clean one-line error and exit with status 1."""
    print(f"replace: {message}", file=sys.stderr)
    sys.exit(1)


def _is_field_path(raw_path):
    """Whether ``raw_path`` reaches into a section (i.e. is field-depth).

    A malformed path is treated as not field-depth; the genuine error is
    reported later, when the path is resolved against a file.
    """
    raw_path = str(raw_path).strip().strip("/")
    try:
        if not is_material_qualified(raw_path):
            raw_path = f"#0/{raw_path}"
        return EndfMaterialPath(raw_path).depth == "field"
    except Exception:  # noqa: BLE001
        return False


def _path_kind(material_path):
    """Classify a resolved material-qualified path by its depth.

    Returns ``"material"`` (selector only), ``"mf"`` (selector and MF),
    ``"section"`` (selector, MF and MT) or ``"field"`` (a path reaching
    into a section).
    """
    return EndfMaterialPath(material_path).depth


def _location(mf, mt):
    """Render the MF[/MT] a path addresses."""
    if mt is None:
        return f"MF={mf}"
    return f"MF={mf}/MT={mt}"


def _label(endf_file, resolved, kind):
    """The ``(MF, MT)`` a path addresses (``MT`` is ``None`` for an MF),
    also for a section selected by its position."""
    if kind in ("section", "field"):
        return section_label_of(endf_file, resolved)
    mp = EndfMaterialPath(resolved)
    return mp.mf, mp.mt


def _open(file, parser, role):
    """Open ``file`` as an :class:`EndfFile`, or exit with a clean error."""
    try:
        return open_endf_file(file, parser)
    except Exception as exc:  # noqa: BLE001
        _fail(f"cannot read {role} file {file}: {parse_error_message(exc)}")


def _extract(endf_file, resolved, kind):
    """Return the object addressed by ``resolved`` in ``endf_file``.

    A ``"material"`` or ``"mf"`` path yields the list of ``(MF, MT,
    section)`` of every section it covers, in the order of the material;
    a ``"section"`` or ``"field"`` path yields the detached section dict
    or the plain field value.
    """
    if kind in ("material", "mf"):
        material = endf_file[selector_of(resolved)]
        mf_scope = EndfMaterialPath(resolved).mf  # None for a whole material
        sections = [
            (mf, mt, material[f"#{position}"].detach())
            for position, (mf, mt) in enumerate(material.sections())
            if mf_scope is None or mf == mf_scope
        ]
        if kind == "mf" and not sections:
            _fail(f"the source has no MF={mf_scope} section to copy")
        return sections
    # a section or a field within a section
    obj = endf_file[resolved]
    if hasattr(obj, "detach"):
        obj = obj.detach()
    return obj


def _has_repeats(labels):
    return len(labels) != len(set(labels))


def _install(endf_file, resolved, kind, obj):
    """Write ``obj`` (as produced by :func:`_extract`) into ``endf_file``."""
    if kind in ("section", "field"):
        endf_file[resolved] = obj
        return
    # "material" or "mf": the destination's covered sections become
    # exactly the source's
    material = endf_file[selector_of(resolved)]
    mf_scope = EndfMaterialPath(resolved).mf  # None for a whole material
    covered = [
        position
        for position, (mf, mt) in enumerate(material.sections())
        if mf_scope is None or mf == mf_scope
    ]
    source_labels = [(mf, mt) for mf, mt, _ in obj]
    target_labels = [material.sections()[position] for position in covered]
    if not (_has_repeats(source_labels) or _has_repeats(target_labels)):
        # every label names one section: replace by label, so that the
        # other sections keep their places
        for mf, mt, section in obj:
            material[mf, mt] = section
        for mf, mt in target_labels:
            if (mf, mt) not in source_labels:
                del material[mf, mt]
        return
    # a label names several sections: copy the sequence of the source in
    # its order, in place of the covered sections of the destination
    first = covered[0] if covered else None
    for position in reversed(covered):
        del material[f"#{position}"]
    for i, (_, _, section) in enumerate(obj):
        material.insert_section(section, None if first is None else first + i)


def _check_same_mat(source, src_resolved, dest, dst_resolved, outfile):
    """Exit with a clean error if the sections copied from the source
    material would get into a target material with another MAT number.

    The sections keep the MAT number of their records, and all sections
    of a material must have the same MAT number, so the file could not be
    written; the MAT number is not rewritten.
    """
    try:
        src_mat = source[selector_of(src_resolved)].mat
        dst_mat = dest[selector_of(dst_resolved)].mat
    except Exception:  # noqa: BLE001
        # reported by the replacement itself
        return
    if src_mat != dst_mat:
        _fail(
            f"the source material has MAT={src_mat} but the target material "
            f"in {outfile} has MAT={dst_mat}; the copied sections keep their "
            "MAT number and all sections of a material must have the same "
            "MAT number, so sections can only be replaced between materials "
            "with the same MAT number"
        )


def _replace_element(
    parser, source_path, target_path, sourcefile, destfiles, create_backup
):
    source = _open(sourcefile, parser, "source")
    src_resolved = resolve_material_path(source, source_path)
    try:
        source_kind = _path_kind(src_resolved)
        obj = _extract(source, src_resolved, source_kind)
    except Exception as exc:  # noqa: BLE001
        _fail(
            f"cannot read {src_resolved} from {sourcefile}: " + parse_error_message(exc)
        )
    for outfile in destfiles:
        dest = _open(outfile, parser, "target")
        dst_resolved = resolve_material_path(dest, target_path)
        try:
            target_kind = _path_kind(dst_resolved)
        except Exception as exc:  # noqa: BLE001
            _fail(f"invalid target path {dst_resolved}: {exc}")
        if target_kind != source_kind:
            _fail(
                f"the source path addresses a {source_kind} but the target "
                f"path addresses a {target_kind}; both must address the "
                "same kind of object"
            )
        try:
            src_label = _label(source, src_resolved, source_kind)
            dst_label = _label(dest, dst_resolved, target_kind)
        except Exception as exc:  # noqa: BLE001
            _fail(f"cannot resolve the sections the paths address: {exc}")
        if src_label != dst_label:
            # a section keeps its own MF/MT in its records, so copying it
            # to a different MF/MT would silently land it back at its own
            _fail(
                f"the source addresses {_location(*src_label)} but the target "
                f"addresses {_location(*dst_label)}; a section or MF file must "
                "be copied to the same MF/MT, since it carries its own "
                "MF/MT in its records"
            )
        if source_kind != "field":
            _check_same_mat(source, src_resolved, dest, dst_resolved, outfile)
        try:
            _install(dest, dst_resolved, target_kind, obj)
        except Exception as exc:  # noqa: BLE001
            _fail(
                f"cannot write {dst_resolved} in {outfile}: " + parse_error_message(exc)
            )
        try:
            export_endf_file(dest, outfile, create_backup)
        except ValueError as exc:
            # e.g. a rule of the tape structure that the edited material
            # breaks; the file is left unchanged
            _fail(f"cannot write {outfile}: {exc}")
    return 0


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    create_backup = not args["no_backup"]
    target_path = args["endfpath"]
    source_path = args["source_path"]
    if source_path is None:
        source_path = target_path
    sourcefile = args["sourcefile"]
    izm = args["ignore_zero_mismatch"]
    izm = False if izm is None else izm
    override_args = {
        "ignore_zero_mismatch": izm,
        "ignore_send_records": True,
        "ignore_missing_tpid": True,
    }
    if _is_field_path(target_path) or _is_field_path(source_path):
        # a replacement inside an MF/MT section and not just swapping out
        # the entire section: keep the verbatim string representation of
        # the section's other, untouched fields
        override_args["preserve_value_strings"] = True
    parser = get_endf_parser(args, override_args)

    destfiles = []
    for fp in args["destfile"]:
        matches = glob(fp)
        if not matches:
            _fail(f"file {fp} does not exist")
        destfiles.extend(matches)
    retcode = _replace_element(
        parser, source_path, target_path, sourcefile, destfiles, create_backup
    )
    sys.exit(retcode)
