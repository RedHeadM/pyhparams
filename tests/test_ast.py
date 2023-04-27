import ast 
from pyhparams.ast import ast_to_dict, AstLoadClassCallArgsExtrator

def test_ast_to_dict_str():
    c = r'var1="foo"'
    d = ast_to_dict(ast.parse(c))
    assert  d.get('var1') == 'foo'

def test_ast_to_dict_dict():
    c = r'var1={"foo":12}'
    d = ast_to_dict(ast.parse(c))
    assert  d.get('var1').get('foo') == 12


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

def test_ast_merge_dict_replace():
    a = r"foo={'x': 1,'y':2}"
    b = r"foo={'x': 3,'y':4}"
    # assuming ast.Attribute
    # Assign(targets=[Name(id='FOO3', ctx=Store())], value=Call(func=Attribute(value=Name(id='pyhparams', ctx=Load()), attr='PARAM_SUBSTITUTE', ctx=Load()), args=[Constant(value='foo')], keywords=[]))
    extractor = AstLoadClassCallArgsExtrator("pyhparams","PARAM_SUBSTITUTE")
    c = extractor.visit(ast.parse(c))
    assert isinstance(extractor.collected_args[0], ast.Constant)
    assert extractor.collected_args[0].value =="foo"

