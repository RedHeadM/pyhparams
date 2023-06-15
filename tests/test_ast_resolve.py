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


# def test_resolve_nested_data_class():
#     a = ast.parse(r'''
# from dataclasses import dataclass
# from pyhparams.ast_data_fields_resolve import RESOLVE
# @dataclass
# class A:
#     a: int = 1
#     b: float = 2
#     @dataclass
#     class B:
#         c: int = 3
#         d: float = 4
#     nested_with_resolved: B = B(c=RESOLVE(A.a)) # in assigned updated vale is used
# assigned = A(a=10)  
# ''')
#     resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
#     assert resolved.get("assigned").nested_with_resolved.c == 10

#TODO: test dataclass default values is no assign
