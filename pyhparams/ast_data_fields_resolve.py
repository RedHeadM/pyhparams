# import ast
from argparse import OPTIONAL
import collections
import dataclasses
from dataclasses import dataclass, field
from typing import Tuple, TypeVar, Generic, overload, Optional, Dict, DefaultDict
import ast
import typing
from collections import defaultdict

from pyhparams import data_class

T = TypeVar("T")
F = TypeVar("F")

# PARAM_MISSING = dataclasses.MISSING
# PARAM_MISSING = Optional[F, dataclasses.MISSING]

def RESOLVE(val: T) -> T:
    ''' function to indicate which dataclass fileds will should be resolved in final config'''
    # NOTE:  better then calls with __new__ since simpler typing
    # foo: int = RESOLVE(1)
    # foo1: int = RESOLVE(1.) # FAILS typing
    return val

# def RESOLVE(val: T, type_t: F) -> F:
#     ''' function to indicate which dataclass fileds will should be resolved in final config'''
#     # NOTE:  better then calls with __new__ since simpler typing
#     # foo: int = RESOLVE(1)
#     # foo1: int = RESOLVE(1.) # FAILS typing
#     return val

@dataclasses.dataclass
class Foo:
    a: int = None
    b: int = 1

a:int = RESOLVE(Foo.a)
# a:int = RESOLVE(1., float)

@dataclass #(solts= True,kw_only=False,frozen=True)
class DataClassKw:
    dataclass_name: str
    dataclass_field: str


class ResolveAttributeToDataClassCall(ast.NodeVisitor):
    def __init__(self)  -> None:
        self.keyword_field : Optional[str] = None
        self.data_class_name : Optional[str] = None
        self.visit_cnt = 0

    def visit_Attribute(self, att: ast.Attribute):

        print(f"DEBUG: ResolveAttributeToDataClassCall#visit_and_resolves node: {ast.dump(att)}") # __AUTO_GENERATED_PRINT_VAR__
        self.visit_cnt += 1
        # assign filed to first visit
        if self.keyword_field is None:
            self.keyword_field = att.attr

        if isinstance(att.value, ast.Name):
            # no nested case
            self.data_class_name = att.value.id
        elif isinstance(att.value, ast.Attribute):
            # nested case: get last attr
            self.data_class_name = att.value.attr
        else:
            raise RuntimeError(f"not supported resolve for: {ast.dump(att)}")

    def visit_and_resolves(self, node: ast.Module) -> Tuple[str, str]:
        self.visit(node)
        assert self.visit_cnt, "attr resolve requestet but nothing was visited"

        assert self.keyword_field is not None, f"resolve look up failed {ast.dump(node)}"
        assert self.data_class_name is not None, f"resolve look up failed {ast.dump(node)}"
        return self.data_class_name, self.keyword_field


class CollectResolveCallsNodeVisitor(ast.NodeVisitor):
    ''' collect all recolve instances and extracts dataclas structure'''
    def __init__(self, func_call_name_id: str)  -> None:
        super().__init__()
        self.func_call_name_id = func_call_name_id
        self.collected_resolve_calls: DefaultDict[str, set] = defaultdict(set)
        # self.resolve_node = resolve_node
        self.node_to_dataclass_kw: Dict[ast.Call, DataClassKw] = {}

    def visit_Call(self, node: ast.Call):
        if  isinstance(node.func, ast.Name): 

            print(f"DEBUG: CollectResolveCallsNodeVisitor#visit_Call node.func.id: {node.func.id}") # __AUTO_GENERATED_PRINT_VAR__
            print(f"DEBUG: CollectResolveCallsNodeVisitor#visit_Call self.func_call_name_id: {self.func_call_name_id}") # __AUTO_GENERATED_PRINT_VAR__
            if node.func.id == self.func_call_name_id:
                assert len(node.args) == 1
                data_class_instance_attr = node.args[0]
                assert isinstance(data_class_instance_attr, ast.Attribute), f"type error for {ast.dump(data_class_instance_attr)}"
                data_class_name, keyword_field = ResolveAttributeToDataClassCall().visit_and_resolves(node)
                self.collected_resolve_calls[data_class_name].add(keyword_field)
                assert not node in self.node_to_dataclass_kw
                self.node_to_dataclass_kw[node] = DataClassKw(dataclass_name = data_class_name, 
                                                             dataclass_field = keyword_field)
        return node
    
    # @staticmethod
    # def attr_to_id(k : DataClassCallInfo) -> str:
    #     # only the last call is enough to get calls calll
    #     return f"{k.class_id}.{k.keyword_val}"

    def visit_collect_resolves(self, node: ast.Module) -> Tuple[DefaultDict[str, set], Dict[ast.Call, DataClassKw]]:
        self.visit(node)
        return self.collected_resolve_calls, self.node_to_dataclass_kw

class ResolveDataClassCallsToValue(ast.NodeVisitor):
    ''' collect all recolve instances and extracts dataclas structure'''
    def __init__(self, resolve_calls: DefaultDict[str, set])  -> None:
        super().__init__()
        self.resolve_calls = resolve_calls
        self.data_class_kw_value: DefaultDict[str, Dict[str, ast.expr]] = defaultdict(dict)
        self.visit_cnt = 0

    def visit_Call(self, node: ast.Call):
        self.visit_cnt+=1
        if  isinstance(node.func, ast.Name): 
            if node.func.id in self.resolve_calls:
                dataclass_name =  node.func.id 
                assert len(node.args) == 0, f"only keyword support dataclass={dataclass_name}: {ast.dump(node)}"
                keys_to_resolve = self.resolve_calls[dataclass_name]
                assert len(keys_to_resolve) > 0, f"no kw to resolve for: {ast.dump(node)}"
                assert len(self.data_class_kw_value[dataclass_name]) ==0, f"Not supported multi assigment for dataclass={dataclass_name}: {ast.dump(node)}"
                for kw in node.keywords:
                    assert kw.arg is not None, f"kw arg is None: {ast.dump(node)}"
                    dataclass_field_name = kw.arg
                    if dataclass_field_name in keys_to_resolve:
                        print(f"INFO: Resolve dataclass: {dataclass_name}.{dataclass_field_name}={ast.dump(kw.value)}") 
                        self.data_class_kw_value[dataclass_name][dataclass_field_name] = kw.value

        return node

    def visit_and_resolve(self, node: ast.Module) -> DefaultDict[str, Dict[str, ast.expr]]:
        self.visit(node)
        assert self.visit_cnt, "check requestet but nothing was visited"
        return self.data_class_kw_value 
    
class HasOpenResolveCalls(ast.NodeVisitor):
    ''' collect all recolve instances and extracts dataclas structure'''
    def __init__(self, func_call_name_id: str)  -> None:
        super().__init__()
        self.func_call_name_id = func_call_name_id
        self._open_resolve_found = False
        self.visit_cnt=0

    def visit_Call(self, node: ast.Call):
        self.visit_cnt+=1
        if isinstance(node.func, ast.Name): 
            if node.func.id == self.func_call_name_id:
                self._open_resolve_found = True

        return node

    def visit_and_check_open_resolves(self, node: ast.Module) -> bool: 
        self.visit(node)
        assert self.visit_cnt, "check requestet but nothing was visited"
        return self._open_resolve_found 


class TransformResolves(ast.NodeTransformer):
    ''' collect all recolve instances and extracts dataclas structure'''
    def __init__(self, node_to_dataclass_kw: Dict[ast.Call, DataClassKw], resolved_dataclass_kw: DefaultDict[str, Dict[str, ast.expr]])  -> None:
        super().__init__()
        self.node_to_dataclass_kw = node_to_dataclass_kw
        self.resolved_dataclass_kw = resolved_dataclass_kw 
        self.visit_cnt = 0

    def visit_Call(self, node: ast.Call):
        self.visit_cnt+=1
        if (data_class_kw := self.node_to_dataclass_kw.get(node)) is not None: 
            value_call = self.resolved_dataclass_kw[data_class_kw.dataclass_name].get(data_class_kw.dataclass_field)
            assert value_call is not None, f" dataclass field cound not be resolved: {data_class_kw.dataclass_name}.{data_class_kw.dataclass_field}" 
            print(f"INFO resolve transform: {data_class_kw.dataclass_name}.{data_class_kw.dataclass_field}={ast.dump(value_call)}")
            return value_call
        return node

    def visit_and_check(self, node: ast.Module) -> None: 
        self.visit(node)
        assert self.visit_cnt, "check requestet but nothing was visited"



# def get_updated_val_for_resolve(node: ast.Module, resolve_calls: Dict[str,DataClassCallInfo]) -> Dict[str, ast.Constant]:
#     ''' colletct all udpated value '''
#     id_to_const_value = {}
#     if len(resolve_calls) ==0:
#         return id_to_const_value
#
#     for stmt in node.body:
#         # if isinstance(stmt, ast.Assign) \
#         #     and isinstance(stmt.value, ast.Call)
#         #         call: ast.Cal = stmt.value.func
#         #         if isinstance(stmt.value, ast.Call)
#         #            if  stmt.value.func.id
#
#         match stmt:
#             case ast.Assign(
#                 value = ast.Call(func=ast.Name(), args =[]),
#             ):
#                 assert isinstance(stmt.value, ast.Assign) and isinstance(stmt.value, ast.Call) and  isinstance(stmt.value.func,ast.Name)
#                 for id_class, data_class_info in resolve_calls:
#                     if stmt.value.func.id == data_class_info:
#                         
#             case _:
#                 continue
#
#     return

def ast_resolve_dataclass_filed(node : ast.Module) -> ast.Module:
    func_call_name_id = RESOLVE.__name__
    assert isinstance(func_call_name_id, str)
    resole_visit, node_to_dataclass_kw = CollectResolveCallsNodeVisitor(func_call_name_id).visit_collect_resolves(node)
    assert len(resole_visit)
    if len(resole_visit):
        # TODO look up defaults
        resolved = ResolveDataClassCallsToValue(resole_visit).visit_and_resolve(node)
        TransformResolves(node_to_dataclass_kw, resolved).visit_and_check(node)
        while(HasOpenResolveCalls(func_call_name_id).visit_and_check_open_resolves(node)):
            print("INFO: Start resolve nested level")
            TransformResolves(node_to_dataclass_kw, resolved).visit_and_check(node)
    return node

    # print(resole_visit.collected_resolve_calls)
    # TODO: cout assign call thow if multiple data classes are used
