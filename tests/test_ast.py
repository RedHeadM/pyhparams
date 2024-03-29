import ast

from pathlib import Path

from pyhparams.ast import (
    ast_to_dict,
    AstLoadClassCallArgsExtrator,
    merge,
    compare,
    get_imports,
    is_dataclass,
    is_dataclass_same,
    _unpack_keywords,
    remove_assigment,
)

from .helper import TestParams


def test_ast_to_dict_str():
    c = r'var1="foo"'
    d = ast_to_dict(ast.parse(c))
    assert d.get("var1") == "foo"

def test_ast_to_dict_dict():
    c = r'var1={"foo":12}'
    d = ast_to_dict(ast.parse(c))
    assert d.get("var1").get("foo") == 12

def test_ast_imports_none():
    c = r'var1="foo"'
    d = get_imports(ast.parse(c))
    assert len(d) == 0

def test_ast_remove():
    c = r'a="foo";b="bar"'
    p = ast.parse(c)
    remove_assigment("b", p)
    d = ast_to_dict(p)
    assert d.get("a") == "foo"
    assert d.get("b") is None

def test_ast_compare():
    assert compare(ast.Constant("a"), ast.Constant("a"))
    assert not compare(ast.Constant("a"), ast.Constant("b"))

def test_ast_imports():
    c = r"""
bar = 3
import sys
from pathlib import Path
foo = 3
"""
    d = get_imports(ast.parse(c))
    assert len(d) == 2


def test_ast_extract_class_values():
    c = r"""
class PARAM_SUBSTITUTE:
    def __init__(self, name):
        pass
val = PARAM_SUBSTITUTE("foo")
"""
    extractor = AstLoadClassCallArgsExtrator(None, "PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    print(
        f"DEBUG:  extractor.collected_args[0]: {ast.dump(extractor.collected_args[0])}"
    )  # __AUTO_GENERATED_PRINT_VAR__
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value == "foo"


def test_ast_extract_class_nested_dict():
    c = r"""
class PARAM_SUBSTITUTE:
    def __init__(self, name):
        pass
val = {"foo":PARAM_SUBSTITUTE("foo")} # <- nested here
"""
    extractor = AstLoadClassCallArgsExtrator(None, "PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value == "foo"


def test_ast_extract_class_no_match():
    c = r"""
class PARAM_SUBSTITUTE:
    def __init__(self, name):
        pass
val = PARAM_SUBSTITUTE("foo")
"""
    extractor = AstLoadClassCallArgsExtrator(None, "no_match")
    c = extractor.visit(ast.parse(c))
    assert len(extractor.collected_args) == 0


def test_ast_extract_class_import_form():
    c = r"""
from pyhparams import PARAM_SUBSTITUTE
val = PARAM_SUBSTITUTE("foo")
"""
    # assuming ast.Call
    #  Assign(targets=[Name(id='FOO1', ctx=Store())], value=Call(func=Name(id='PARAM_SUBSTITUTE', ctx=Load()), args=[Constant(value='foo')], keywords=[]))
    extractor = AstLoadClassCallArgsExtrator("pyhparams", "PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value == "foo"


def test_ast_extract_class_import():
    c = r"""
import pyhparams 
val = pyhparams.PARAM_SUBSTITUTE("foo")

"""
    # assuming ast.Attribute
    # Assign(targets=[Name(id='FOO3', ctx=Store())], value=Call(func=Attribute(value=Name(id='pyhparams', ctx=Load()), attr='PARAM_SUBSTITUTE', ctx=Load()), args=[Constant(value='foo')], keywords=[]))
    extractor = AstLoadClassCallArgsExtrator("pyhparams", "PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value == "foo"


def test_ast_merge_replace_int_int():
    a = ast.parse(r"foo=0")
    b = ast.parse(r"foo=1")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"] == 0


def test_ast_merge_replace_str():
    a = ast.parse(r"foo='strfoo'")
    b = ast.parse(r"foo=1")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"] == "strfoo"


def test_ast_merge_append():
    a = ast.parse(r"target_only=0")
    b = ast.parse(r"base_only=1")
    merged = ast_to_dict(merge(a, base=b))
    assert merged.get("base_only") == 1
    assert merged.get("target_only") == 0


def test_ast_merge_append_dict():
    a = ast.parse(r"target_only={'a':1}")
    b = ast.parse(r"base_only={'b':0}")
    merged = ast_to_dict(merge(a, base=b))
    assert merged.get("base_only") == {"b": 0}
    assert merged.get("target_only") == {"a": 1}


def test_ast_merge_append_dict_call():
    a = ast.parse(r"target_only=dict(a=1)")
    b = ast.parse(r"base_only=dict(b=0)")
    merged = ast_to_dict(merge(a, base=b))
    assert merged.get("base_only") == {"b": 0}
    assert merged.get("target_only") == {"a": 1}


def test_ast_merge_dict_replace_top_level():
    a = ast.parse(r"foo={'replaced': 1,'addedtarget':4}")
    b = ast.parse(r"foo={'replaced': 3,'addedbase':10}")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"].get("replaced") == 1
    assert merged["foo"].get("addedbase") == 10
    assert merged["foo"].get("addedtarget") == 4


def test_ast_merge_dict_nesed_1_replace():
    a = ast.parse(r"foo={'level0': {'level1':0}}")
    b = ast.parse(r"foo={'level0': {'level1':'to_be_gone'}}")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"].get("level0") == {"level1": 0}


def test_ast_merge_dict_nesed_1_replace_call():
    a = ast.parse(r"foo=dict(level0=dict(level1=0))")
    b = ast.parse(r"foo=dict(level0=dict(level1='to_be_gone'))")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"].get("level0") == {"level1": 0}


def test_ast_merge_dict_nesed_1_append():
    a = ast.parse(r"foo={'level0': {'a':0}}")
    b = ast.parse(r"foo={'level0': {'b':'must_be_there'}}")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"].get("level0") == {"a": 0, "b": "must_be_there"}


def test_ast_merge_dict_with_import_in_target():
    a = ast.parse(r"import pathlib; foo=pathlib.Path('a')")
    b = ast.parse(r"bar=pathlib.Path('a')")
    merged = ast_to_dict(merge(a, base=b))
    assert merged.get("foo") == Path("a")


def test_ast_merge_dict_with_import_in_base():
    a = ast.parse(r"bar=pathlib.Path('a')")
    b = ast.parse(r"import pathlib; foo=pathlib.Path('a')")
    merged = ast_to_dict(merge(a, base=b))
    assert merged.get("foo") == Path("a")


def test_ast_merge_dataclass_append():
    local_import_path = Path(__file__).parent.resolve()
    sys_path = f'import sys;sys.path.append("{local_import_path}")'
    a = ast.parse(f"{sys_path};import helper; a=helper.TestParams(x=10,y=20)")
    b = ast.parse(f"{sys_path};import helper; b=helper.TestParams(x=1,y=2)")
    merge_expr = ast_to_dict(merge(a, base=b))
    # assert merge_expr.get("a") == TestParams(x=10,y=20) # TODO
    assert merge_expr.get("a").x == 10
    assert merge_expr.get("a").y == 20

    assert merge_expr.get("b").x == 1
    assert merge_expr.get("b").y == 2


def test_ast_is_data_class_assing():
    local_import_path = Path(__file__).parent.resolve()
    sys_path = f'import sys;sys.path.append("{local_import_path}")'
    expr_helper_import = ast.parse(sys_path)
    a = ast.parse(f"{sys_path};import helper; to_be_merged=helper.TestParams(x=10,y=20)")

    # pass body to have imports with sys call correct
    assert is_dataclass(a.body[-1], imports=a.body[:-1])

def test_ast_is_same_dataclass_eq():
    local_import_path = Path(__file__).parent.resolve()
    sys_path = f'import sys;sys.path.append("{local_import_path}")'
    expr_helper_import = ast.parse(sys_path)
    a = ast.parse(f"{sys_path};import helper; to_be_merged=helper.TestParams(x=10,y=20)")
    b = ast.parse(f"{sys_path};import helper; to_be_merged=helper.TestParams(x=0)")

    assert is_dataclass_same(a.body[-1],b.body[-1], imports=a.body[:-1])


def test_ast_is_data_class_assing_from_import():
    local_import_path = Path(__file__).parent.resolve()
    sys_path = f'import sys;sys.path.append("{local_import_path}")'
    expr_helper_import = ast.parse(sys_path)
    a = ast.parse(f"{sys_path};from helper import TestParams; to_be_merged=TestParams(x=10,y=20)")

    # pass body to have imports with sys call correct
    assert is_dataclass(a.body[-1], imports=a.body[:-1])


def test_ast_is_data_class_assing_none():
    a = ast.parse(r"import pathlib; foo=pathlib.Path('a'); bar =2")

    assert not is_dataclass(a.body[-2], imports=[a.body[0]])
    assert not is_dataclass(a.body[-1], imports=[a.body[0]])

def test_ast_is_same_dataclass_eq():
    local_import_path = Path(__file__).parent.resolve()
    sys_path = f'import sys;sys.path.append("{local_import_path}")'
    expr_helper_import = ast.parse(sys_path)
    a = ast.parse(f"{sys_path};import helper; to_be_merged=helper.TestParams(x=10,y=20)")
    b = ast.parse(f"{sys_path};import helper; to_be_merged=helper.TestParams(x=0)")

    assert is_dataclass_same(a.body[-1],b.body[-1], imports=a.body[:-1])

def test_ast_is_same_dataclass_not_eq():
    local_import_path = Path(__file__).parent.resolve()
    sys_path = f'import sys;sys.path.append("{local_import_path}")'
    expr_helper_import = ast.parse(sys_path)
    a = ast.parse(f"{sys_path};import helper; to_be_merged=helper.TestParams(x=10,y=20)")
    b = ast.parse(f"{sys_path};import helper; to_be_merged=helper.TestParams2(x=0)")

    assert not is_dataclass_same(a.body[-1],b.body[-1], imports=a.body[:-1])


def test_unpack_dict_keywords():
    expr = ast.Dict(
        keys=[ast.Constant(value="a"), ast.Constant(value="b")], values=[ast.Constant(value=0), ast.Constant(value=1)]
    )
    kw = _unpack_keywords(expr)
    assert kw is not None and len(kw) == 2
    assert compare(kw[0], ast.keyword(arg="a", value=ast.Constant(value=0)))
    assert compare(kw[1], ast.keyword(arg="b", value=ast.Constant(value=1)))


def test_ast_merge_dataclass_merge_attribule_import():
    a = ast.parse(r"import pyhparams; to_be_merged=pyhparams.utils.UtilsTestParams(x=10)")
    b = ast.parse(r"import pyhparams; to_be_merged=pyhparams.utils.UtilsTestParams(x=10,y=20)")
    merge_expr = ast_to_dict(merge(a, base=b))
    # assert merge_expr.get("a") == TestParams(x=10,y=20) # TODO
    assert merge_expr.get("to_be_merged").x == 10
    assert merge_expr.get("to_be_merged").y == 20, "default is not taken form base"


def test_ast_merge_dataclass_merge():
    a = ast.parse(r"from pyhparams.utils import UtilsTestParams; to_be_merged=UtilsTestParams(x=10)")
    b = ast.parse(r"from pyhparams.utils import UtilsTestParams; to_be_merged=UtilsTestParams(x=10,y=20)")
    merge_expr = ast_to_dict(merge(a, base=b))
    # assert merge_expr.get("a") == TestParams(x=10,y=20) # TODO
    assert merge_expr.get("to_be_merged").x == 10
    assert merge_expr.get("to_be_merged").y == 20, "default is not taken form base"


def test_ast_merge_dataclass_merge_attribule_import_replace():
    a = ast.parse(r"import pyhparams; to_be_merged=pyhparams.utils.UtilsTestParams(x=30)")
    b = ast.parse(r"import pyhparams; to_be_merged=pyhparams.utils.UtilsTestParams(x=10)")
    merge_expr = ast_to_dict(merge(a, base=b))
    assert merge_expr.get("to_be_merged").x == 30


def test_ast_merge_dataclass_nested():
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import WithNested, TestParamsStr
a  = WithNested(nested=TestParamsStr(value1="to_be_merged", value2="still_there"))
"""
    )
    target = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import WithNested, TestParamsStr
a  = WithNested(nested=TestParamsStr(value1="target"))
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))
    assert merge_expr.get("a").nested.value1 == "target"
    assert merge_expr.get("a").nested.value2 == "still_there"

def test_ast_merge_dataclass_default_not_changed():
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import WithNested, TestParamsStr
a  = WithNested(nested=TestParamsStr(value1="to_be_merged"))
"""
    )
    target = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import WithNested, TestParamsStr
a  = WithNested(nested=TestParamsStr(value1="target"))
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))
    assert merge_expr.get("a").nested.value1 == "target"
    assert merge_expr.get("a").nested.value2 == "not_set2"

def test_ast_merge_dataclass_level_two():
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import WithNested, TestParamsStr, NesttedTwoLevel
a  = NesttedTwoLevel(nested2=WithNested(nested=TestParamsStr(value1="to_be_merged")))
"""
    )
    target = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import WithNested, TestParamsStr, NesttedTwoLevel
a  = NesttedTwoLevel(nested2=WithNested(nested=TestParamsStr(value1="target")))
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))
    assert merge_expr.get("a").nested2.nested.value1 == "target"
    assert merge_expr.get("a").nested2.nested.value2 == "not_set2"


def test_ast_merge_dataclass_attr_import():
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
import pyhparams.utils as pyhu
a  = pyhu.TestParamsStr(value1="must_be_changed")
"""
    )
    target = ast.parse(
        f"""
import pyhparams.utils as pyhu
a  = pyhu.TestParamsStr(value1="target")
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))
    assert merge_expr.get("a").value1 == "target"
    assert merge_expr.get("a").value2 == "not_set2"

def test_ast_merge_dataclass_attr2_import():
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
import pyhparams as pyh
a  = pyh.utils.TestParamsStr(value1="must_be_changed")
"""
    )
    target = ast.parse(
        f"""
import pyhparams as pyh
a  = pyh.utils.TestParamsStr(value1="target")
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))
    assert merge_expr.get("a").value1 == "target"
    assert merge_expr.get("a").value2 == "not_set2"

def test_ast_merge_nestested_dataclass_attr_import():
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
import pyhparams.utils as pyhu
a  = pyhu.WithNested(nested=pyhu.TestParamsStr(value1="must_be_changed"))
"""
    )
    target = ast.parse(
        f"""
import pyhparams.utils as pyhu
a  = pyhu.WithNested(nested=pyhu.TestParamsStr(value1="target"))
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))
    assert merge_expr.get("a").nested.value1 == "target"
    assert merge_expr.get("a").nested.value2 == "not_set2"


def test_ast_merge_differnt_dataclasses():
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import WithNested, TestParamsStr
# from pyhparams.utils import TestParamsDictStr
a  = WithNested(nested=TestParamsStr(value1="to_be_merged", value2="still_there"))
"""
    )
    target = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
# from pyhparams.utils import WithNested, TestParamsStr
from pyhparams.utils import TestParamsDictStr
a = TestParamsDictStr(value={{'val':'target'}})
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))

    from pyhparams.utils import TestParamsDictStr
    assert isinstance(merge_expr.get("a"),TestParamsDictStr)
    assert merge_expr.get("a").value.get('val') == "target"

def test_ast_merge_dataclasses_no_dict_nodict_value():
    kw_base = "kw_base"
    base = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import TestParamsDictStr
a  = TestParamsDictStr(value=dict({kw_base}="should_be_gone"))
"""
    )
    target = ast.parse(
        f"""
from pyhparams.ast_data_fields_resolve import RESOLVE
from pyhparams.utils import TestParamsDictStr
a  = TestParamsDictStr(value=dict(diffent_kw_to_base="target"))
"""
    )

    merge_expr = ast_to_dict(merge(target, base=base))

    from pyhparams.utils import TestParamsDictStr
    assert isinstance(merge_expr.get("a"),TestParamsDictStr)
    assert "kw_base" not in merge_expr.get("a").value
    # assert merge_expr.get("a").value.get('diffent_kw_to_base') == "target"


# TODO: to not allow syy path valls for usr
# TODO: merge empty dict

# def test_ast_multi_assign_toplevel_yes():
#     c = r'''
# a = 2
# a = a+3
# '''
#     assert ast.has_multi_name_assigment(ast.parse(c))
#
# def test_ast_multi_assign_toplevel_no():
#     c = r'''
# a = 2
# b = a + 2
# '''
#     assert not ast.has_multi_name_assigment(ast.parse(c))
