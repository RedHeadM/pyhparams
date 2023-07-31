import ast
import pytest
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

def test_resolve_top_level_same_multiple_times():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
@dataclass
class A:
    a: int = 0
    b: float = 1
assigned = A(a=10, b= 1/139.)  
resolved = RESOLVE(A.a) 
resolved2 = RESOLVE(A.a) 
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("resolved") == 10
    assert resolved.get("resolved2") == 10

def test_resolve_top_level_with_list():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
@dataclass
class A:
    a: int = 0
    b: float = 0
assigned = A(a=10, b= 1/139.)  
resolved = [RESOLVE(A.a)] # resolve last assignment a=10 instead of default 0
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("resolved")[0] == 10

def test_resolve_top_level_with_dict():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
@dataclass
class A:
    a: int = 0
    b: float = 0
assigned = A(a=10, b= 1/139.)  
resolved = dict(value=RESOLVE(A.a)) 
resolved2 = {"value":RESOLVE(A.a)} 
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("resolved").get("value") == 10
    assert resolved.get("resolved2").get("value") == 10

def test_resolve_top_level_with_tuple():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
@dataclass
class A:
    a: int = 0
    b: float = 0
assigned = A(a=10, b= 1/139.)  
# resolved = tuple(RESOLVE(A.a),) 
resolved2 = (RESOLVE(A.a),)
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    # assert resolved.get("resolved")[0] == 10
    assert resolved.get("resolved2")[0] == 10

# TODO set

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
    @dataclass
    class B:
        b: int = 3
    nesed_class: B = None
assigned = A(a=100, nesed_class = A.B(b=RESOLVE(A.a)) )  
''')

    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("assigned").nesed_class.b == 100

def test_resolve_nested_data_class_defined_nested_with_List():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
from typing import List
                   
@dataclass
class A:
    a: int = 1
    @dataclass
    class B:
        b: int = 3
    nesed_class: List[B] = None
assigned = A(a=100, nesed_class = [A.B(b=RESOLVE(A.a))] )  
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("assigned").nesed_class[0].b == 100


def test_resolve_nested_data_class_defined_nested_with_Dict():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
from typing import Dict
                   
@dataclass
class A:
    a: int = 1
    @dataclass
    class B:
        b: int = 3
    nesed_class: Dict[str,B] = None
assigned = A(a=100, nesed_class = {"val":A.B(b=RESOLVE(A.a))} )  
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("assigned").nesed_class.get("val").b == 100

def test_resolve_nested_data_class_defined_nested_with_Tuple():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
from typing import Tuple
                   
@dataclass
class A:
    a: int = 1
    b: float = 2
    to_resolve: float = 1 # in assigned updated vale is used
    @dataclass
    class B:
        b: int = 3
    nesed_class: Tuple[str,B] = None
assigned = A(a=100, nesed_class = ("val", A.B(b=RESOLVE(A.a))) )  
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("assigned").nesed_class[1].b == 100

# def test_resolve_nested_data_class_defined_nested_with_dict():
#     a = ast.parse(r'''
# from dataclasses import dataclass
# from pyhparams.ast_data_fields_resolve import RESOLVE
# from typing import Dict
#                    
# @dataclass
# class A:
#     a: int = 1
#     b: float = 2
#     to_resolve: float = 1 # in assigned updated vale is used
#     @dataclass
#     class B:
#         b: int = 3
#     nesed_class: Dict[B] = None
# assigned = A(a=10, nesed_class = {"dict_key":A.B(b=RESOLVE(A.a))} )  
# ''')
#     resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
#     assert False
#     assert resolved.get("assigned").nesed_class["dict_key"].b == 100

def test_resolve_data_class_import():
    a = ast.parse(r'''
from pyhparams.utils import UtilsTestParams, UtilsTestParams2
from pyhparams.ast_data_fields_resolve import RESOLVE
a = UtilsTestParams(x=10,y=100)
b = UtilsTestParams2(z= RESOLVE(UtilsTestParams.x))
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("b").z == 10


def test_resolve_default():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
@dataclass
class A:
    a: int = 100
    b: float = 1/137.
resolved = RESOLVE(A.a) # resolve default
''')
    conf = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert conf.get("resolved") == 100

def test_resolve_nested_default_nested():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
                   
@dataclass
class A:
    a: int = 1
    b: float = 2
    @dataclass
    class B:
        b: int = 3
    nesed_class: B = None
assigned = A(nesed_class = A.B(b=RESOLVE(A.a)) )  
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("assigned").nesed_class.b == 1

def test_resolve_nested_level_assign():
    a = ast.parse(r'''
from dataclasses import dataclass
from pyhparams.ast_data_fields_resolve import RESOLVE
                   
@dataclass
class A:
    a: int = 1
    @dataclass
    class B:
        b: int = 2
        c: int = 3
    nesed_class: B = None
A.B.b
assigned = A(nesed_class = A.B(b=RESOLVE(A.B.c), c=100))  
''')
    with pytest.raises(NotImplementedError):   
        resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    # assert resolved.get("assigned").nesed_class.b == 100

def test_resolve_tuple_idx_default():
    a = ast.parse(r'''
from dataclasses import dataclass
from typing import Tuple
@dataclass
class A:
    a_tuple: Tuple[int,int]= (10,20)                   
idx0 = RESOLVE(A.a_tuple)[0]
idx1 = RESOLVE(A.a_tuple)[1]
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("idx0") == 10
    assert resolved.get("idx1") == 20

def test_resolve_tuple_idx_assigned():
    a = ast.parse(r'''
from dataclasses import dataclass
from typing import Tuple
@dataclass
class A:
    a_tuple: Tuple[int,int]= (10,20)                   
a = A(a_tuple=(1,2))
idx0 = RESOLVE(A.a_tuple)[0]
idx1 = RESOLVE(A.a_tuple)[1]
''')
    resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
    assert resolved.get("idx0") == 1
    assert resolved.get("idx1") == 2


# def test_resolve_multi_depended():
#     a = ast.parse(r'''
# from dataclasses import dataclass
# from pyhparams.ast_data_fields_resolve import RESOLVE
# @dataclass
# class A:
#     a: int = 100
# @dataclass
# class B:
#     b: int = 2
# @dataclass
# class C:
#     c: int = 3
# a = A(a=4) 
# b = B(b=RESOLVE(A.a)) 
# c = C(c=RESOLVE(B.b)) # resolve of b only can happen if resolved before
# ''')
#     resolved = ast_to_dict(ast_resolve_dataclass_filed(a))
#     assert resolved.get("c").c ==4
