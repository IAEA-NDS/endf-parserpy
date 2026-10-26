"""The package works without the optional dependency lark.

lark is only needed for the logical expressions of ``endf-cli match``
(module ``endf_parserpy.utils.matching``). The tests run Python in a
subprocess in which ``import lark`` fails.
"""

import subprocess
import sys
import textwrap
from pathlib import Path
import pytest


TESTFILE = Path(__file__).parent / "testdata" / "dec-094_Pu_244.endf"

BLOCK_LARK = """
import sys
sys.modules["lark"] = None  # any import of lark raises ImportError
"""


def _run(code):
    script = BLOCK_LARK + textwrap.dedent(code)
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def test_python_parser_without_lark():
    out = _run(
        f"""
        from endf_parserpy import EndfParserPy, EndfParserFactory
        parser = EndfParserPy(cache_dir="/nonexistent", print_cache_info=True)
        data = parser.parsefile({str(TESTFILE)!r})
        assert parser.write(data) == EndfParserPy().write(data)
        parser = EndfParserFactory.create(select="python", cache_dir=False)
        assert parser.parsefile({str(TESTFILE)!r}).keys() == data.keys()
        assert "lark" not in sys.modules or sys.modules["lark"] is None
        print("ok")
        """
    )
    # the deprecated options are accepted but have no effect
    assert out.strip() == "ok"


def test_cpp_parser_without_lark():
    pytest.importorskip("endf_parserpy.cpp_parsers.endf6_ext")
    _run(
        f"""
        from endf_parserpy import EndfParserCpp, EndfParserPy, EndfParserFactory
        data = EndfParserCpp().parsefile({str(TESTFILE)!r})
        ref = EndfParserPy().parsefile({str(TESTFILE)!r})
        assert EndfParserCpp().write(data) == EndfParserPy().write(ref)
        parser = EndfParserFactory.create(select="cpp")
        assert parser.parsefile({str(TESTFILE)!r}).keys() == data.keys()
        """
    )


def test_endf_file_without_lark():
    _run(
        f"""
        from endf_parserpy import EndfFile, EndfParserPy
        endf_file = EndfFile({str(TESTFILE)!r}, parser=EndfParserPy())
        assert len(endf_file.materials()) == 1
        """
    )


def test_code_generation_without_lark():
    _run(
        """
        from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
        from endf_parserpy.endf_recipes import get_recipe_dict
        recipe = get_recipe_dict("endf6-ext")[3]
        code = generate_cpp_parsefun("parse_mf3", recipe)
        assert "parse_mf3" in code
        """
    )


def test_logical_expressions_need_lark():
    _run(
        """
        from endf_parserpy.utils.matching import eval_expr
        try:
            eval_expr("/1/451/ZA > 0", {})
        except ImportError as exc:
            msg = str(exc)
            assert "lark" in msg and "endf-parserpy[cli]" in msg, msg
        else:
            raise AssertionError("ImportError expected")
        """
    )
