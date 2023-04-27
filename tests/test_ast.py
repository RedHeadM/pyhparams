import ast 

from pathlib import Path
from pyhparams.ast import ast_to_dict, AstLoadClassCallArgsExtrator, merge,compare, get_imports

def test_ast_to_dict_str():
    c = r'var1="foo"'
    d = ast_to_dict(ast.parse(c))
    assert  d.get('var1') == 'foo'

def test_ast_to_dict_dict():
    c = r'var1={"foo":12}'
    d = ast_to_dict(ast.parse(c))
    assert  d.get('var1').get('foo') == 12


def test_ast_imports_none():
    c = r'var1="foo"'
    d = get_imports(ast.parse(c))
    assert  len(d) ==0

def test_ast_imports():
    c = r'''
bar = 3
import sys
from pathlib import Path
foo = 3
'''
    d = get_imports(ast.parse(c))
    assert  len(d) ==2

def test_ast_extract_class_values():
    c = r'''
class PARAM_SUBSTITUTE:
    def __init__(self, name):
        pass
val = PARAM_SUBSTITUTE("foo")
'''
    extractor = AstLoadClassCallArgsExtrator(None,"PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    print(f"DEBUG:  extractor.collected_args[0]: {ast.dump(extractor.collected_args[0])}") # __AUTO_GENERATED_PRINT_VAR__
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value =="foo"

def test_ast_extract_class_nested_dict():
    c = r'''
class PARAM_SUBSTITUTE:
    def __init__(self, name):
        pass
val = {"foo":PARAM_SUBSTITUTE("foo")} # <- nested here
'''
    extractor = AstLoadClassCallArgsExtrator(None,"PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value =="foo"

def test_ast_extract_class_no_match():
    c = r'''
class PARAM_SUBSTITUTE:
    def __init__(self, name):
        pass
val = PARAM_SUBSTITUTE("foo")
'''
    extractor = AstLoadClassCallArgsExtrator(None,"no_match")
    c = extractor.visit(ast.parse(c))
    assert len(extractor.collected_args) == 0


def test_ast_extract_class_import_form():
    c = r'''
from pyhparams import PARAM_SUBSTITUTE
val = PARAM_SUBSTITUTE("foo")
'''
    # assuming ast.Call
    #  Assign(targets=[Name(id='FOO1', ctx=Store())], value=Call(func=Name(id='PARAM_SUBSTITUTE', ctx=Load()), args=[Constant(value='foo')], keywords=[]))
    extractor = AstLoadClassCallArgsExtrator("pyhparams","PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value =="foo"

def test_ast_extract_class_import():
    c = r'''
import pyhparams 
val = pyhparams.PARAM_SUBSTITUTE("foo")

'''
    # assuming ast.Attribute
    # Assign(targets=[Name(id='FOO3', ctx=Store())], value=Call(func=Attribute(value=Name(id='pyhparams', ctx=Load()), attr='PARAM_SUBSTITUTE', ctx=Load()), args=[Constant(value='foo')], keywords=[]))
    extractor = AstLoadClassCallArgsExtrator("pyhparams","PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value =="foo"

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
    assert merged["foo"] == 'strfoo'

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
    assert merged.get("base_only") == {'b':0}
    assert merged.get("target_only") == {'a':1}

def test_ast_merge_dict_replace_top_level():
    a = ast.parse(r"foo={'replaced': 1,'addedtarget':4}")
    b = ast.parse(r"foo={'replaced': 3,'addedbase':10}")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"].get('replaced') == 1
    assert merged["foo"].get('addedbase') == 10
    assert merged["foo"].get('addedtarget') == 4

def test_ast_merge_dict_nesed_1_replace():
    a = ast.parse(r"foo={'level0': {'level1':0}}")
    b = ast.parse(r"foo={'level0': {'level1':'to_be_gone'}}")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"].get('level0') == {'level1':0}

def test_ast_merge_dict_nesed_1_append():
    a = ast.parse(r"foo={'level0': {'a':0}}")
    b = ast.parse(r"foo={'level0': {'b':'must_be_there'}}")
    merged = ast_to_dict(merge(a, base=b))
    assert "foo" in merged
    assert merged["foo"].get('level0') == {'a':0,'b':'must_be_there'}

def test_ast_merge_dict_with_import_in_target():
    a = ast.parse(r"import pathlib; foo=pathlib.Path('a')")
    b = ast.parse(r"bar=pathlib.Path('a')")
    merged = ast_to_dict(merge(a, base=b))
    assert merged.get("foo") == Path('a')

def test_ast_merge_dict_with_import_in_base():
    a = ast.parse(r"bar=pathlib.Path('a')")
    b = ast.parse(r"import pathlib; foo=pathlib.Path('a')")
    merged = ast_to_dict(merge(a, base=b))
    assert merged.get("foo") == Path('a')

def test_ast_compare():
    assert compare(ast.Constant("a"), ast.Constant("a"))
    assert not compare(ast.Constant("a"), ast.Constant("b"))


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
