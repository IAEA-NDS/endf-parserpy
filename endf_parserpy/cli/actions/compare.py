############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from collections import defaultdict
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    open_endf_file,
    parsed_material_dict,
)
import sys
from endf_parserpy import compare_objects
from endf_parserpy.utils.debugging_utils import _compare_objects


COMMAND_NAME = "compare"


def add_subparser(subparsers):
    parser_compare = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_compare)
    parser_compare.add_argument(
        "--atol", type=float, default=1e-8, help="absolute tolerance"
    )
    parser_compare.add_argument(
        "--rtol", type=float, default=1e-6, help="relative tolerance"
    )
    parser_compare.add_argument("files", nargs=2, help="files for comparison")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    files = args["files"]
    atol = args["atol"]
    rtol = args["rtol"]
    retcode = _compare_endf_files(parser, files, atol=atol, rtol=rtol)
    sys.exit(retcode)


def _pair_materials(endf_file1, endf_file2):
    """Pair the materials of two tapes by MAT number.

    Materials are paired by MAT number; when a MAT number repeats, the
    k-th occurrence in one tape is paired with the k-th occurrence in the
    other (pairing by order of appearance). Returns ``(pairs, unpaired1,
    unpaired2)`` where ``pairs`` is a list of ``(MaterialView,
    MaterialView)`` and the ``unpaired`` lists hold the materials of each
    tape that found no partner.
    """
    by_mat1 = defaultdict(list)
    by_mat2 = defaultdict(list)
    for material in endf_file1:
        by_mat1[material.mat].append(material)
    for material in endf_file2:
        by_mat2[material.mat].append(material)
    pairs = []
    unpaired1 = []
    unpaired2 = []
    for mat, materials1 in by_mat1.items():
        materials2 = by_mat2.get(mat, [])
        npairs = min(len(materials1), len(materials2))
        for k in range(npairs):
            pairs.append((materials1[k], materials2[k]))
        unpaired1.extend(materials1[npairs:])
        unpaired2.extend(materials2[npairs:])
    for mat, materials2 in by_mat2.items():
        if mat not in by_mat1:
            unpaired2.extend(materials2)
    return pairs, unpaired1, unpaired2


def _section_keys(material):
    """The keys ``(MF, MT, k)`` of the sections of a material in its
    order, ``k`` the occurrence of the label."""
    seen = defaultdict(int)
    keys = []
    for mf, mt in material.sections():
        keys.append((mf, mt, seen[(mf, mt)]))
        seen[(mf, mt)] += 1
    return keys


def _compare_materials(material1, material2, files, atol, rtol):
    """Compare two paired materials section by section.

    The sections are paired by label and occurrence: the k-th section
    MF/MT of one material with the k-th of the other. A material without
    repeated labels is compared as the ``{MF: {MT: section}}`` dict, as
    before; the paths of a label that repeats in either material carry
    ``#k``. A section without a partner, and a different order of the
    paired sections, are differences.
    """
    keys1 = _section_keys(material1)
    keys2 = _section_keys(material2)
    repeated = {(mf, mt) for mf, mt, k in keys1 + keys2 if k > 0}
    set1, set2 = set(keys1), set(keys2)

    def name(key):
        mf, mt, k = key
        return f"{mf}/{mt}#{k}" if (mf, mt) in repeated else f"{mf}/{mt}"

    is_equal = True
    if not repeated:
        is_equal = compare_objects(
            parsed_material_dict(material1),
            parsed_material_dict(material2),
            atol=atol,
            rtol=rtol,
            fail_on_diff=False,
        )
    else:
        for key in keys1:
            if key not in set2:
                print(f"unpaired: section {name(key)} only in {files[0]}")
                is_equal = False
                continue
            mf, mt, k = key
            same = _compare_objects(
                material1[mf, mt, k].detach(),
                material2[mf, mt, k].detach(),
                curpath=f"/{name(key)}",
                atol=atol,
                rtol=rtol,
                fail_on_diff=False,
            )
            is_equal = is_equal and same
        for key in keys2:
            if key not in set1:
                print(f"unpaired: section {name(key)} only in {files[1]}")
                is_equal = False
    order1 = [key for key in keys1 if key in set2]
    order2 = [key for key in keys2 if key in set1]
    if order1 != order2:
        print(
            f"section order differs: {files[0]} has "
            + ", ".join(name(key) for key in order1)
            + f"; {files[1]} has "
            + ", ".join(name(key) for key in order2)
        )
        is_equal = False
    return is_equal


def _open(file, parser):
    """Open ``file`` as an :class:`EndfFile`, or exit cleanly with status 2."""
    try:
        return open_endf_file(file, parser, on_error="raise")
    except Exception as exc:  # noqa: BLE001
        print(f"compare: cannot read {file}: {exc}", file=sys.stderr)
        sys.exit(2)


def _compare_endf_files(parser, files, atol, rtol):
    endf_file1 = _open(files[0], parser)
    endf_file2 = _open(files[1], parser)
    pairs, unpaired1, unpaired2 = _pair_materials(endf_file1, endf_file2)
    # A plain single-vs-single comparison prints just the field diff, as
    # the pre-multi-material CLI did; a header is only added once more
    # than one material is in play.
    annotate = len(endf_file1) > 1 or len(endf_file2) > 1
    all_equal = True
    for material1, material2 in pairs:
        if annotate:
            print(
                f"=== comparing #{material1.position} (MAT {material1.mat}) "
                f"<-> #{material2.position} (MAT {material2.mat}) ==="
            )
        if not _compare_materials(material1, material2, files, atol, rtol):
            all_equal = False
    for material in unpaired1:
        print(
            f"unpaired: #{material.position} (MAT {material.mat}) "
            f"only in {files[0]}"
        )
    for material in unpaired2:
        print(
            f"unpaired: #{material.position} (MAT {material.mat}) "
            f"only in {files[1]}"
        )
    is_equal = all_equal and not unpaired1 and not unpaired2
    return 0 if is_equal else 1
