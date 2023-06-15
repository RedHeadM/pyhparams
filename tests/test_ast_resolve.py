import ast
from pyhparams.ast import ast_to_dict
from pyhparams.ast_data_fields_resolve import RESOLVE, ast_resolve_dataclass_filed

from dataclasses import dataclass

@dataclass
class A:
    a: int = 0
    b: float = 0

@dataclass
class B:
    c: int = 0
    d: float = 0

assigned = A(a=10, b= 1/139.)  
resolved = RESOLVE(A.a)


def test_resolve_top_level():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
@dataclass
class A:
    a: int = 0
    b: float = 0
assigned = A(a=10, b= 1/139.)  
resolved = RESOLVE(A.a) # resolve last assignment a=10 instead of default 0
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("resolved") == 10


def test_resolve_nested_data_class_defined_at_top_level():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE

@dataclass
class B:
    c: int = 3
    d: float = 4
@dataclass
class A:
    a: int = 1
    b: float = 2
    to_resolve: float = 1 # in assigned updated vale is used
assigned = A(a=10, to_resolve = RESOLVE(A.a) )  
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("assigned").to_resolve == 10

def test_resolve_nested_data_class_defined_nested():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
                   
@dataclass
class A:
    a: int = 1
    b: float = 2
    to_resolve: float = 1 # in assigned updated vale is used
    @dataclass
    class B:
        b: int = 3
    nesed_class: B = None
assigned = A(a=100, nesed_class = A.B(b=RESOLVE(A.a)) )  
''')

    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("assigned").nesed_class.b == 100

def test_resolve_data_class_import():
    a = ast.parse(r'''
from pyhparams.utils import UtilsTestParams, UtilsTestParams2
from pyhparams.ast_data_fields_resolve import RESOLVE
a = UtilsTestParams(x=10,y=100)
b = UtilsTestParams2(z= RESOLVE(UtilsTestParams.x))
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("b").z == 10


#TODO: test dataclass default values is no assign
