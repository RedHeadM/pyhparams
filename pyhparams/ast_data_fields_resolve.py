# import ast
from argparse import OPTIONAL
import collections
import dataclasses
from dataclasses import dataclass, field
from typing import Tuple, TypeVar, List, overload, Optional, Dict, DefaultDict
import ast
import typing
from collections import defaultdict

from pyhparams import data_class

T = TypeVar("T")
# F = TypeVar("F")

# PARAM_MISSING = dataclasses.MISSING
# PARAM_MISSING = Optional[F, dataclasses.MISSING]

def RESOLVE(val: T) -> T:
    ''' function to indicate which dataclass fileds will should be resolved in final config'''
    # NOTE:  better then calls with __new__ since simpler typing
    return val

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
            print(f"\nDEBUG: CollectResolveCallsNodeVisitor#visit_Call node.func.id: {ast.dump(node)}\n") # __AUTO_GENERATED_PRINT_VAR__
            if node.func.id == self.func_call_name_id:
                assert len(node.args) == 1
                data_class_instance_attr = node.args[0]
                assert isinstance(data_class_instance_attr, ast.Attribute), f"type error for {ast.dump(data_class_instance_attr)}"
                data_class_name, keyword_field = ResolveAttributeToDataClassCall().visit_and_resolves(node)
                self.collected_resolve_calls[data_class_name].add(keyword_field)
                assert not node in self.node_to_dataclass_kw
                self.node_to_dataclass_kw[node] = DataClassKw(dataclass_name = data_class_name, 
                                                             dataclass_field = keyword_field)
            elif len(node.keywords):
                # TODO: better way toget to call all ast.Call
                for kw in node.keywords:
                    if isinstance(kw.value,ast.Call):
                        self.visit_Call(kw.value)

        elif isinstance(node.func, ast.Attribute): 
            # TODO: better way toget to call all ast.Call
            for kw in node.keywords:
                if isinstance(kw.value,ast.Call):
                    self.visit_Call(kw.value)
        return node

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
        self.transform_cnt = 0
        self.resolved_dataclass_field: List[str] = []

    def visit_Call(self, node: ast.Call):
        self.visit_cnt+=1
        if (data_class_kw := self.node_to_dataclass_kw.get(node)) is not None: 
            value_call = self.resolved_dataclass_kw[data_class_kw.dataclass_name].get(data_class_kw.dataclass_field)
            id_dataclass_field =f'{data_class_kw.dataclass_name}.{data_class_kw.dataclass_field}'
            assert value_call is not None, f" dataclass field cound not be resolved: {id_dataclass_field}" 
            print(f"INFO resolve transform: {id_dataclass_field}={ast.dump(value_call)}")
            self.transform_cnt+=1
            self.resolved_dataclass_field.append(id_dataclass_field)
            return value_call
        elif len(node.keywords):
            # TODO: better way toget to call all ast.Call
            for kw in node.keywords:
                if isinstance(kw.value,ast.Call):
                    kw.value = self.visit_Call(kw.value)
        elif isinstance(node.func, ast.Attribute): 
            # TODO: better way toget to call all ast.Call
            for kw in node.keywords:
                if isinstance(kw.value,ast.Call):
                    self.visit_Call(kw.value)
                # check for kw calls
        return node

    def visit_and_check(self, node: ast.Module) -> List[str]: 
        self.visit(node)
        assert self.visit_cnt, "check requestet but nothing was visited"
        assert self.transform_cnt, "expected transform but none happend"
        return self.resolved_dataclass_field

def ast_resolve_dataclass_filed(node : ast.Module) -> ast.Module:
    func_call_name_id = RESOLVE.__name__
    assert isinstance(func_call_name_id, str)
    resolve_visit, node_to_dataclass_kw = CollectResolveCallsNodeVisitor(func_call_name_id).visit_collect_resolves(node)
    assert len(resolve_visit)
    if len(resolve_visit):
        # TODO look up defaults
        resolved = ResolveDataClassCallsToValue(resolve_visit).visit_and_resolve(node)
        resolved_ids = TransformResolves(node_to_dataclass_kw, resolved).visit_and_check(node)
        while(HasOpenResolveCalls(func_call_name_id).visit_and_check_open_resolves(node)):
            print("INFO: Start resolve nested level")
            resolved_ids.extend(TransformResolves(node_to_dataclass_kw, resolved).visit_and_check(node))
        for dataclass_name, dataclass_fields in resolved.items():
            for dataclass_field_name in dataclass_fields.keys():
                id_dataclass_field = f"{dataclass_name}.{dataclass_field_name}"
                assert id_dataclass_field in resolved_ids, f'failed to resolve {id_dataclass_field}'

        # check no resol
    return node

    # print(resole_visit.collected_resolve_calls)
    # TODO: cout assign call thow if multiple data classes are used
