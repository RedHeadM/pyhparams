import ast
import pprint
import dataclasses
from os import walk
from typing import Any, Optional, Sequence, Tuple, Union, Dict, List
import sys


from dataclasses import is_dataclass

c = r"""
from dataclasses import dataclass,fields
from typing import NamedTuple
class TestNamedTuple(NamedTuple):
    x:int=0
    y:int=1

@dataclass
class A:
    a_tuple: TestNamedTuple= TestNamedTuple(10,20)                   
idx0 = RESOLVE(A.a_tuple)[0]
idx1 = RESOLVE(A.a_tuple)[1]
"""

from typing import TypeVar

from dataclasses import dataclass, is_dataclass

T = TypeVar("T")


def RESOLVE(val: T) -> T:
    return val


foo1: int = RESOLVE(1.0)
foo1: int = RESOLVE(1.0)


@dataclass
class A:
    a: int = 0
    b: float = 0


assigned = A(a=10, b=1 / 139.0)
resolved = RESOLVE(A.a)


@dataclass
class DataClassSimple:
    name: int = 1
    foo: int = 2


a = DataClassSimple(name=1, foo=dataclasses.MISSING)

assert is_dataclass(DataClassSimple)

kslajfl = DataClassSimple(name=1)

codes = ast.parse(c)
print(codes.__class__.__name__)


def ast_to_dict(codes) -> Dict[str, Any]:
    codeobj = compile(codes, "", mode="exec")
    # Support load global variable in nested function of the
    # config.
    global_locals_var = {}
    eval(codeobj, global_locals_var, global_locals_var)
    cfg_dict = {key: value for key, value in global_locals_var.items() if (not key.startswith("__"))}
    return cfg_dict


class AstClassSubstitutor(ast.NodeTransformer):
    """Wraps all strings in 'START ' + string + ' END'."""

    # def visit_Str(self, node):
    name: str = "PARAM_SUBSTITUTE____"
    value = ast.Constant(value="HHHAALLO")

    def visit_Call(self, node):
        # if isinstance(node.func, ast.Call):
        assert isinstance(node, ast.Call)
        if isinstance(node.func, ast.Name):
            if node.func.id == self.name:
                return self.value
        return node

    def visit_Assign(self, node):
        # print(f"DEBUG: ParamSubstitutor#visit_Assign targets: {node.targets}") # __AUTO_GENERATED_PRINT_VAR__
        # for t in node.targets:
        #     print(f"DEBUG: ParamSubstitutor#visit_Assign t: {t}") # __AUTO_GENERATED_PRINT_VAR__
        #     if isinstance(t, ast.Call):
        #         print("CALL")
        #     if isinstance(t, ast.Name):
        #         print("Name")kkjj

        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                if node.value.func.id == self.name:
                    # print("FOUND")
                    pass
                    # node.value = self.value
        return self.generic_visit(node)
        # return node

        # if (isinstance(node.targets[0], ast.Name)
        #         and node.targets[0].id == "base"):
        #     return None
        # else:
        #     print(f"DEBUG: AstDo#visit_Assign ast.Name: {ast.Name}") # __AUTO_GENERATED_PRINT_VAR__
        #     return node


print(ast.dump(codes))


# for node in ast.walk(codes):
#     print(ast.dump(node))

print()
print()
# codesUnpaded = AstClassSubstitutor().visit(codes)
# Add lineno & col_offset to the nodes we created
# ast.fix_missing_locations(codesUnpaded)
# print(ast_to_dict(codesUnpaded))
# BASE_KEY = "_base_"
dataclass_test = ast.Module

# class AstMergeerge(ast.NodeTransformer):
#     ''' extracts args for class a call'''
#     def __init__(self,  import_a, import_b)
#         self.import_a = import_a
#         self.import_b = import_b
#
#     def visit_Call(self, node_a):
#         # class is used to create a class
#         assert isinstance(node, ast.Call) #k
#         if isinstance(node.func, ast.Name) and isinstance(node.func.ctx, ast.Load):
#             #class definition is local or imorted with "form xyz import TheClass"
#             if node.func.id == self.class_name:
#                 self.collected_args.extend(node.args)
#         elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
#             if node.func.value.id == self.class_module and node.func.attr == self.class_name:
#                 self.collected_args.extend(node.args)
#         return node
#
#     def visit_Assign(self, node):
#         # visit all Call create for assignment with visit_Call
#         return self.generic_visit(node)
#
#         if isinstance(node, (ast.Import,ast.ImportFrom)):
#             return node
#         else:
#             return None

#
for i, stm in enumerate(codes.body):
    # pprint.pprint(f"{i}:\n{ast.dump(stm)}")
    pprint.pprint(f"{i}:\n{ast.dump(stm)}")
    # pprint.pprint(ast.dump(stm))
#     if isinstance(stm, ast.Assign):
#         print(f"{i}:\n{ast.dump(stm)}")
#     # if isinstance(stm, ast.Import):
#     #     dataclass_test += stm
# if isinstance(stm, ast.Assign):
#     if isinstance(stm, ast.Assign):


# for i, stm in enumerate(codes.body):
#     print(f"{i}:\n{ast.dump(stm)}")


# class AstLoadClassCallArgsExtrator(ast.NodeTransformer):
#     ''' extracts args for class a call'''
#     def __init__(self,):

#
# def merge(a, b):
#     codes_a = ast.parse(a)
#     #
#     # import_a = get_imports(a)
#     # codes_b = ast.parse(b)kk
#     # import_b = get_imports(b)
#     for i, stm in enumerate(codes.body):
#         print(f"{i}:\n{ast.dump(stm)}")
#         # if isinstance(stm, ast.Assign):


# ast_imports = AstImportExtractor().vt(codes)
def get_imports(codes) -> List[Union[ast.Import, ast.ImportFrom]]:
    stm_imports = []
    for i, stm in enumerate(codes.body):
        if isinstance(stm, (ast.Call)):
            stm_imports.append(stm)
    return stm_imports


def is_dataclass(importsstm, class_names: List[Union[ast.Name, ast.Attribute]]):
    ast_m = ast.parse("from dataclasses import is_dataclass")
    # redo same imports
    for stm in importsstm:
        ast_m.body.append(stm)
    # append call to check if is dataclass
    for class_name in class_names:
        # call function to check if is data class
        check_call = ast.Assign(
            targets=[ast.Name(id=class_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id="is_dataclass", tx=ast.Load()),
                args=[ast.Name(id=class_name, ctx=ast.Load())],
                keywords=[],
            ),
        )
        ast_m.body.append(check_call)
    return ast_to_dict(codes)

    # print(ast_to_dict(codes))


# if sys.version_info[0] == 3 and sys.version_info[1] > 9 :
#     print(f"unparse code:\n {ast.unparse(codes)}")

codes = ast.parse("{'foo':1}")


def match_keyword(assign_value: ast.expr) -> Optional[List[ast.keyword]]:
    match assign_value:
        case ast.Call(
            func=ast.Call(
                func=ast.Name(id="dict", ctx=ast.Load()),
            ),
        ):
            assert False
            return assign_value.keywords
        case ast.Dict():
            return [ast.keyword(args=k.value, value=v) for k, v in zip(assign_value.keys, assign_value.values)]
        case _:
            assert False
            return None


a = match_keyword(codes.body[-1].value)
