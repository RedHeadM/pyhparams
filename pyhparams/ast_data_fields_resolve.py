from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, TypeVar, List, Union, Optional, Dict, DefaultDict
from collections.abc import Iterable
import ast
from collections import defaultdict

from pyhparams.ast import get_imports, get_dataclass_def, ast_to_dict, compare

T = TypeVar("T")


def RESOLVE(val: T) -> T:
    """function to indicate which dataclass fileds will should be resolved in final config"""
    # NOTE:  better then calls with __new__ since simpler typing
    return val


@dataclass  # (solts= True,kw_only=False,frozen=True)
class DataClassKw:
    class_name: str
    field_name: str
    nested_class_define: List[str]


class ResolveAttributeToDataClassCall(ast.NodeVisitor):
    def __init__(self) -> None:
        self.keyword_field: Optional[str] = None
        self.data_class_name: Optional[str] = None
        self.dataclass_nested_class_define: List[str] = []
        self.visit_cnt = 0

    def visit_Attribute(self, att: ast.Attribute):
        self.visit_cnt += 1
        # assign filed to first visit
        if self.keyword_field is None:
            self.keyword_field = att.attr

        if isinstance(att.value, ast.Name):
            # no nested case
            self.data_class_name = att.value.id
            self.dataclass_nested_class_define.append(att.value.id)
        elif isinstance(att.value, ast.Attribute):
            # nested case: get last attr
            self.data_class_name = att.value.attr
            self.dataclass_nested_class_define.append(att.value.attr)
        else:
            raise RuntimeError(f"not supported resolve for: {ast.dump(att)}")

        if isinstance(att.value, ast.Attribute):
            # nested attribute case
            self.visit_Attribute(att.value)

    def visit_and_resolves(self, node: ast.expr) -> DataClassKw:
        self.visit(node)
        assert self.visit_cnt, "attr resolve requestet but nothing was visited"

        assert self.keyword_field is not None, f"resolve look up failed {ast.dump(node)}"
        assert self.data_class_name is not None, f"resolve look up failed {ast.dump(node)}"
        assert len(self.dataclass_nested_class_define), f"resolve look up failed {ast.dump(node)}"
        # reverse order
        if len(self.dataclass_nested_class_define):
            self.dataclass_nested_class_define = self.dataclass_nested_class_define[::-1]
            self.data_class_name = self.dataclass_nested_class_define[-1]
        return DataClassKw(
            class_name=self.data_class_name,
            field_name=self.keyword_field,
            nested_class_define=self.dataclass_nested_class_define,
        )


class CollectResolveCallsNodeVisitor(ast.NodeVisitor):
    """collect all recolve instances and extracts dataclas structure"""

    def __init__(self, func_call_name_id: str) -> None:
        super().__init__()
        self.func_call_name_id = func_call_name_id
        self.collected_resolve_calls: DefaultDict[str, set] = defaultdict(set)
        # self.resolve_node = resolve_node
        self.node_to_dataclass_kw: Dict[ast.Call, DataClassKw] = {}

    def visit_Call(self, node: ast.Call):
        # print(f"\n\nDEBUG: CollectResolveCallsNodeVisitor#visit_Call node.func.id: {ast.dump(node)}\n") # __AUTO_GENERATED_PRINT_VAR__
        if isinstance(node.func, ast.Name) and node.func.id == self.func_call_name_id:
            assert len(node.args) == 1
            data_class_instance_attr = node.args[0]
            assert isinstance(
                data_class_instance_attr, ast.Attribute
            ), f"type error for {ast.dump(data_class_instance_attr)}"
            data_class_class_kw = ResolveAttributeToDataClassCall().visit_and_resolves(node)
            self.collected_resolve_calls[data_class_class_kw.class_name].add(data_class_class_kw.field_name)
            # print(f"DEBUG: resolve found: {data_class_class_kw.class_name}.{data_class_class_kw.field_name}")
            if len(data_class_class_kw.nested_class_define) > 1:
                raise NotImplementedError(f"not supporeded yet with nested imports {data_class_class_kw}")
            if node in self.node_to_dataclass_kw:
                pev_assign_kw = self.node_to_dataclass_kw[node]
                assert compare(
                    pev_assign_kw, data_class_class_kw
                ), f"Multiple assigments with differnt value: {data_class_class_kw.class_name}.{data_class_class_kw.field_name}"
            self.node_to_dataclass_kw[node] = data_class_class_kw

        if hasattr(node, "keywords"):
            for kw in node.keywords:
                self.visit(kw)
        if len(node.args):
            for kw in node.args:
                self.visit(kw)
        if isinstance(node.func, ast.Attribute):
            for kw in node.args:
                self.visit(kw)
        return node

    def visit_List(self, node: ast.List):
        for kw in node.elts:
            self.visit(kw)

    def visit_Dict(self, node: ast.Dict):
        for kw in node.values:
            self.visit(kw)

    def visit_collect_resolves(self, node: ast.Module) -> Tuple[DefaultDict[str, set], Dict[ast.Call, DataClassKw]]:
        self.visit(node)
        return self.collected_resolve_calls, self.node_to_dataclass_kw


class ResolveDataClassCallsKeywordCalls(ast.NodeVisitor):
    """collect all recolve instances and extracts dataclass structure"""

    def __init__(self, resolve_calls: DefaultDict[str, set]) -> None:
        super().__init__()
        self.resolve_calls = resolve_calls
        self.data_class_kw_value: DefaultDict[str, Dict[str, ast.expr]] = defaultdict(dict)
        self.visit_cnt = 0

    def visit_Call(self, node: ast.Call):
        self.visit_cnt += 1
        if isinstance(node.func, ast.Name):
            # check if is a dadaclass and hast keys to resolve
            if node.func.id in self.resolve_calls:
                dataclass_name = node.func.id
                assert len(node.args) == 0, f"only keyword support dataclass={dataclass_name}: {ast.dump(node)}"
                keys_to_resolve = self.resolve_calls[dataclass_name]
                assert len(keys_to_resolve) > 0, f"no kw to resolve for: {ast.dump(node)}"
                assert (
                    len(self.data_class_kw_value[dataclass_name]) == 0
                ), f"Not supported multi assigment for dataclass={dataclass_name}: {ast.dump(node)}"
                for kw in node.keywords:
                    assert kw.arg is not None, f"kw arg is None: {ast.dump(node)}"
                    dataclass_field_name = kw.arg
                    if dataclass_field_name in keys_to_resolve:
                        print(
                            f"INFO: Resolve dataclass from assigment: {dataclass_name}.{dataclass_field_name}={ast.dump(kw.value)}"
                        )
                        # if isinstance(kw.value, ast.Attribute):
                        assert (
                            dataclass_field_name not in self.data_class_kw_value[dataclass_name]
                        ), "mulitiassigment for {dataclass_name}.{dataclass_field_name}"
                        self.data_class_kw_value[dataclass_name][dataclass_field_name] = kw.value

        return node

    def visit_and_resolve(self, node: ast.Module) -> DefaultDict[str, Dict[str, ast.expr]]:
        self.visit(node)
        assert self.visit_cnt, "check requestet but nothing was visited"
        return self.data_class_kw_value


class HasOpenResolveCalls(ast.NodeVisitor):
    """collect all recolve instances and extracts dataclas structure"""

    def __init__(self, func_call_name_id: str) -> None:
        super().__init__()
        self.func_call_name_id = func_call_name_id
        self._open_resolve_found = False
        self.visit_cnt = 0

    def visit_Call(self, node: ast.Call):
        self.visit_cnt += 1
        if isinstance(node.func, ast.Name):
            if node.func.id == self.func_call_name_id:
                self._open_resolve_found = True

        return node

    def visit_and_check_open_resolves(self, node: ast.Module) -> bool:
        self.visit(node)
        # assert self.visit_cnt, "check requestet but nothing was visited" # no assert since all calls can be mapped to ast.const
        return self._open_resolve_found


class TransformResolves(ast.NodeTransformer):
    """collect all recolve instances and extracts dataclas structure"""

    def __init__(
        self,
        node_to_dataclass_kw: Dict[ast.Call, DataClassKw],
        resolved_dataclass_kw: DefaultDict[str, Dict[str, ast.expr]],
    ) -> None:
        super().__init__()
        self.node_to_dataclass_kw = node_to_dataclass_kw
        self.resolved_dataclass_kw = resolved_dataclass_kw
        self.visit_cnt = 0
        self.transform_cnt = 0
        self.resolved_dataclass_field: List[str] = []

    def visit_Call(self, node: ast.Call):
        self.visit_cnt += 1
        ret_transform = node
        if (data_class_kw := self.node_to_dataclass_kw.get(node)) is not None:
            value_call = self.resolved_dataclass_kw[data_class_kw.class_name].get(data_class_kw.field_name)
            id_dataclass_field = f"{data_class_kw.class_name}.{data_class_kw.field_name}"
            if value_call is not None:
                # assert value_call is not None, f" dataclass field cound not be resolved: {id_dataclass_field}"
                # print(f"DEBUG resolve transform: {id_dataclass_field}={ast.dump(value_call)}")
                self.transform_cnt += 1
                self.resolved_dataclass_field.append(id_dataclass_field)
                ret_transform = value_call
        if hasattr(node, "keywords"):
            for kw in node.keywords:
                self.visit(kw)
        if len(node.args):
            for kw in node.args:
                self.visit(kw)

        return ret_transform

    def visit_List(self, node: ast.List):
        # visit and update Calls
        elts = []
        for kw in node.elts:
            elts.append(self.visit(kw))
        node.elts = elts
        return node

    def visit_and_check(self, node: ast.Module) -> List[str]:
        self.visit(node)
        assert self.visit_cnt > 0, "expected at least one resolve transform"
        return self.resolved_dataclass_field


def _look_up_dataclass_default(dataclass_name: str, dataclass_field: str, imports, class_defs) -> ast.expr:
    ast_m = ast.parse("")
    ast_m.body.extend(imports)
    ast_m.body.extend(class_defs)
    # TODO maybe with meta lib or parse once
    # define function get default values when evaluated
    ast_func = ast.parse(
        r"""
def get_default(data_class, field_name):
    from dataclasses import is_dataclass, fields, is_dataclass
    found=False
    default_value = None
    default_souce = "const_value"
    is_dataclass_val = is_dataclass(data_class)
    if is_dataclass_val:
        field_name_to_field = {f.name:f for f in fields(data_class)}
        if (f:= field_name_to_field.get(field_name)) is not None:
            found=True
            if callable(f.default_factory):
                default_value = f.default_factory()
                default_souce = "factory"
            else:
                default_value = f.default
    return {"field_found" : found, "is_dataclass" : is_dataclass_val, 
            "default_value": default_value, 
            "default_from_factory" : default_souce}
"""
    )
    ast_m.body.extend(ast_func.body)
    # ast prase evaluation of function to get default values
    # and add an assing value to extract ast.expr to return
    result_name = "get_default_return_val"
    ast_func = ast.parse(f"{result_name} = get_default({dataclass_name},'{dataclass_field}')")
    ast_m.body.extend(ast_func.body)
    ast.fix_missing_locations(ast_m)

    # print(f"DEBUG: _look_up_dataclass_default ast_m: {unparse(ast_m)}") # __AUTO_GENERATED_PRINT_VAR__
    default_return_val = ast_to_dict(ast_m)[result_name]
    assert default_return_val[
        "is_dataclass"
    ], f"Resolve for default value {dataclass_name}.{dataclass_field} is not a dataclass"
    assert default_return_val[
        "field_found"
    ], f"Resolve for default value {dataclass_name}.{dataclass_field} field does not exits"

    default_value = default_return_val["default_value"]
    default_source = default_return_val["default_from_factory"]
    ast_expr_default_value = None
    print(
        f"INFO: resolved default value for {dataclass_name}.{dataclass_field}={default_value} source={default_source}"
    )
    simple_const_value_types = (str, int, float, Path)
    if isinstance(default_value, simple_const_value_types) or default_value is None:
        ast_value_expr = ast.parse(f"default_val = {default_value}").body[0]
        assert isinstance(ast_value_expr, ast.Assign)
        ast_expr_default_value = ast_value_expr.value
        print(
            f"DEBUG: resolved simple type default value for ast value{dataclass_name}.{dataclass_field}={ast.dump(ast_value_expr.value)}"
        )
    elif isinstance(default_value, (tuple, list, set)):
        assert all(isinstance(v, simple_const_value_types) for v in default_value)
        ast_value_expr = ast.parse(f"default_val = {default_value}").body[0]
        assert isinstance(ast_value_expr, ast.Assign)
        ast_expr_default_value = ast_value_expr.value
        # print(
        #     f"DEBUG: resolved iterabl default value for ast value{dataclass_name}.{dataclass_field}={ast.dump(ast_value_expr.value)}"
        # )
    else:
        # also dataclasses.MISSING here
        # TODO: add import and func call to get value
        # eg. a= RESOLVE(A.a) to from pyharams import get_dataclass_default_value; a= get_dataclass_default_value(A, a)
        raise NotImplementedError(
            f"complex type not supportd for dataclass default resovle {dataclass_name}.{dataclass_field} type={type(default_value)}"
        )

    return ast_expr_default_value


def _update_unresolved_with_dataclass_defaults(
    collected_resolve_calls: DefaultDict[str, set],
    data_class_kw_value: DefaultDict[str, Dict[str, ast.expr]],
    imports: List[Union[ast.Import, ast.ImportFrom]],
    class_def: List[ast.ClassDef],
) -> DefaultDict[str, Dict[str, ast.expr]]:
    """for dataclass field pairs with no resovle look up defaults"""

    for dataclass_name, dataclass_fields in collected_resolve_calls.items():
        for dataclass_field_name in dataclass_fields:
            if (
                dataclass_name not in data_class_kw_value
                or dataclass_field_name not in data_class_kw_value[dataclass_name]
            ):
                # id_dataclass_field = f"{dataclass_name}.{dataclass_field_name}"
                # assert False, f'failed to resolve {id_dataclass_field}'
                expr = _look_up_dataclass_default(dataclass_name, dataclass_field_name, imports, class_def)
                data_class_kw_value[dataclass_name][dataclass_field_name] = expr
    return data_class_kw_value


def ast_resolve_dataclass_filed(node: ast.Module) -> ast.Module:
    func_call_name_id = RESOLVE.__name__
    assert isinstance(func_call_name_id, str)
    # import pprint
    # for n in node.body:
    #     print(f"DEBUG:  node n: {pprint.pformat(ast.dump(n))}") # __AUTO_GENERATED_PRINT_VAR_END__
    collected_resolve_calls, node_to_dataclass_kw = CollectResolveCallsNodeVisitor(
        func_call_name_id
    ).visit_collect_resolves(node)

    if len(collected_resolve_calls):
        # TODO check dataclasses
        resolved = ResolveDataClassCallsKeywordCalls(collected_resolve_calls).visit_and_resolve(node)
        if sum((len(r) for r in collected_resolve_calls)) != sum((len(r) for r in resolved)):
            resolved = _update_unresolved_with_dataclass_defaults(
                collected_resolve_calls, resolved, get_imports(node), get_dataclass_def(node)
            )
        assert sum((len(r) for r in collected_resolve_calls)) == sum(
            (len(r) for r in resolved)
        ), "not all could be resolved"

        resolved_ids = TransformResolves(node_to_dataclass_kw, resolved).visit_and_check(node)

        # loop to resovle nested
        max_leved = 5
        for current_nested_resolve_level in range(max_leved):
            if not HasOpenResolveCalls(func_call_name_id).visit_and_check_open_resolves(node):
                break
            print(f"DEBUG: Start resolve nested level={current_nested_resolve_level}/{max_leved}")
            resolved_ids.extend(TransformResolves(node_to_dataclass_kw, resolved).visit_and_check(node))
        else:  # no break
            assert not HasOpenResolveCalls(func_call_name_id).visit_and_check_open_resolves(
                node
            ), f"failed to resolve all"
        # check no resolve
        for dataclass_name, dataclass_fields in resolved.items():
            for dataclass_field_name in dataclass_fields.keys():
                id_dataclass_field = f"{dataclass_name}.{dataclass_field_name}"
                assert id_dataclass_field in resolved_ids, f"failed to resolve {id_dataclass_field}"

    return node

    # print(resole_visit.collected_resolve_calls)
    # TODO: cout assign call thow if multiple data classes are used
