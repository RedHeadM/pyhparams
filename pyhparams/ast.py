import ast
import runpy
import sys
import itertools
from types import ModuleType
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import black


def ast_to_dict(tree: ast.Module) -> Dict[str, Any]:
    """runs ast modules and exports local and global var at top level to dict"""
    codeobj = compile(tree, "", mode="exec")
    # Support load global variable in nested function of the
    # config.
    global_locals_var = {}  # {"__name__":""}
    try:
        eval(codeobj, global_locals_var, global_locals_var)
    except Exception as e:
        raise Exception(f"failed to eval ast:\n {unparse(tree)}\n with {e}") from e

    cfg_dict = {
        key: value
        for key, value in global_locals_var.items()
        if (not key.startswith("__")) and (not isinstance(value, ModuleType))
    }
    return cfg_dict


def _get_same_assign(target: ast.Assign, base: List[ast.Assign]) -> Optional[ast.Assign]:
    assert isinstance(target, ast.Assign)
    assert len(target.targets) == 1
    assert isinstance(target.targets[0], ast.Name)

    for stm in base:
        assert isinstance(target, ast.Assign)
        assert isinstance(stm.targets[0], ast.Name)
        assert len(stm.targets) == 1
        if stm.targets[0].id is target.targets[0].id:
            # if stm.targets[0] is  target.targets[0]: # TODO
            return stm
    return None


def compare(node1, node2):
    ## TODO: simpler func here
    if type(node1) is not type(node2):
        return False
    if isinstance(node1, ast.AST):
        for k, v in vars(node1).items():
            if k in ("lineno", "col_offset", "ctx"):
                continue
            if not compare(v, getattr(node2, k)):
                return False
        return True
    elif isinstance(node1, list):
        return all(itertools.starmap(compare, zip(node1, node2)))
    else:
        return node1 == node2


def _merge_assign_dict(target: ast.Assign, base: ast.Assign,target_imports: Optional[List[Union[ast.Import, ast.ImportFrom]]]) -> ast.Assign:
    # check if both are expected dict type
    for s in (target, base):
        assert isinstance(s, ast.Assign)
        assert len(s.targets) == 1
        assert isinstance(s.targets[0], ast.Name)

    target.value = _merge_dict_call(target.value, base.value, target_imports)
    return target


def _merge_dict_call(target: ast.expr, base: ast.expr, target_imports: Optional[List[Union[ast.Import, ast.ImportFrom]]]) -> ast.Call:
    kw_base = _unpack_keywords(base)
    kw_target = _unpack_keywords(target)
    assert kw_base is not None and kw_target is not None  # TODO
    kw_merged = _merge_keyword(kw_target, kw_base, target_imports)
    # allway map ast.Dict to ast.Call with function dict
    return ast.Call(func=ast.Name(id="dict", ctx=ast.Load()), args=[], keywords=kw_merged)


def _merge_assign_data_class(
    target: ast.Assign,
    base: ast.Assign,
    target_imports: Optional[List[Union[ast.Import, ast.ImportFrom]]]
) -> ast.Assign:
    # check if both are expected dict type
    for s in (target, base):
        assert isinstance(s, ast.Assign)
        assert len(s.targets) == 1
        assert isinstance(s.targets[0], ast.Name)
        # assert isinstance(s.value, ast.Call)
    assert isinstance(target.value, ast.Call)
    assert isinstance(base.value, ast.Call)
    target.value = _merge_data_class_call(target.value, base.value, target_imports)
    return target


def _merge_data_class_call(
    target: ast.Call,
    base: ast.Call,
    target_imports: Optional[List[Union[ast.Import, ast.ImportFrom]]]
    ) -> ast.Call:

    kw_base = _unpack_keywords(base)
    kw_target = _unpack_keywords(target)
    assert kw_base is not None and kw_target is not None  # TODO
    kw_merged = _merge_keyword(kw_target, kw_base, target_imports, no_dict_merge=True)
    target.keywords = kw_merged
    return target


def _merge_keyword(target: List[ast.keyword], base: List[ast.keyword], import_target: Optional[List[Union[ast.Import, ast.ImportFrom]]], no_dict_merge: bool=False) -> List[ast.keyword]:
    target_kw = {k.arg: k.value for k in target}
    base_kw = {k.arg: k.value for k in base}
    merged_kew = dict(base_kw)
    print("DEBUG _merge_keyword call")


    if import_target is not None:
        print(f"DEBUG: _merge_keyword import_target: {len(import_target)}") # __AUTO_GENERATED_PRINT_VAR_END__

    for k, v in target_kw.items():
        assert k is not None
        assert isinstance(k, (ast.Constant, str)), f"dict key must be const got: {ast.dump(k)}"

        if (
            not no_dict_merge and
            (same_value_base := base_kw.get(k)) is not None
            and _nested_call_is_dict(same_value_base)
            and _nested_call_is_dict(v)
        ):
            # recusive call for now
            merged_kew[k] = _merge_dict_call(v, same_value_base, import_target)


        elif (
            (same_value_base := base_kw.get(k)) is not None
            # and is_dataclass(same_value_base, import_base)
            # and is_dataclass(v, import_target)
            and is_dataclass_same(v, same_value_base, import_target)
        ):
            assert isinstance(same_value_base, ast.Call)
            assert isinstance(v, ast.Call)
            merged_kew[k] = _merge_data_class_call(v, same_value_base, import_target)
        else:
            # keep value from target if not Dict or dataclass
            merged_kew[k] = v
    return [ast.keyword(arg=k, value=v) for k, v in merged_kew.items()]


def _nested_call_is_dict(assign_value: ast.expr) -> bool:
    """extract kwargs for dict call"""

    # if sys.version_info >= (3, 10):
    #     match assign_value:
    #         case ast.Call(
    #             func=ast.Call(func=ast.Name(id='dict', ctx=ast.Load()),),
    #         ):
    #             return True
    #         case ast.Dict():
    #             return True
    #         case _:
    #             return False
    if (
        isinstance(assign_value, ast.Call)
        and isinstance(assign_value.func, ast.Call)
        and isinstance(assign_value.func.func, ast.Name)
        and assign_value.func.func.id == "dict"
    ):
        # TODO: not called in test
        return True
    elif isinstance(assign_value, ast.Dict):
        return True
    else:
        return False


def _unpack_keywords(assign_value: ast.expr) -> Optional[List[ast.keyword]]:
    """extract kwargs for dict call"""
    # match assign_value:
    #     case ast.Call():
    #         assert assign_value.args is None or len(assign_value.args) == 0
    #         return assign_value.keywords
    #     case ast.Dict():
    #         assert assign_value.values is not None
    #         assert assign_value.keys is not None
    #         # NOTE: caution a never use ast.keyword(args=... instead of ast.keyword(arg=....
    #         return [ast.keyword(arg=_uppack_dict_key(k), value=v) for k, v in zip(assign_value.keys, assign_value.values) if k is not None]
    #     case _:
    #         return None

    if isinstance(assign_value, ast.Call):
        assert assign_value.args is None or len(assign_value.args) == 0
        return assign_value.keywords
    elif isinstance(assign_value, ast.Dict):
        assert assign_value.values is not None
        assert assign_value.keys is not None
        # NOTE: caution a never use ast.keyword(args=... instead of ast.keyword(arg=....
        return [
            ast.keyword(arg=_uppack_dict_key(k), value=v)
            for k, v in zip(assign_value.keys, assign_value.values)
            if k is not None
        ]
    else:
        return None


def _uppack_dict_key(key: ast.expr) -> str:
    # match key:
    #     case ast.Constant():
    #         return key.value
    #     case None:
    #         raise ValueError(f'got none for key {ast.dump(key)}')
    #     case _:
    #         return key

    if isinstance(key, ast.Constant):
        return key.value
    elif key is None:
        raise ValueError(f"got none for key {ast.dump(key)}")
    else:
        return key


def _is_dict_assign(stmt: ast.Assign) -> bool:
    # TODO: Assign(targets=[Name(id='FOO3_attr', ctx=Store())], value=Call(func=Name(id='dict', ctx=Load()), args=[], keywords=[keyword(arg='name', value=Constant(value='foo'))]))
    assert isinstance(stmt, ast.Assign)
    return isinstance(stmt.value, ast.Dict) or _assign_is_dict_func_call(stmt)


def _assign_is_dict_func_call(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Dict)


def is_dataclass(assign: Union[ast.Assign, ast.Call, str], imports: Optional[List[Union[ast.Import, ast.ImportFrom]]]) -> bool:
    """for assign check if the call is a dataclass by calling by using imports dataclasses.is_dataclass"""
    is_dataclass_args = None
    # TODO:clean up
    if isinstance(assign, str):
        is_dataclass_args = [ast.Name(id=assign, ctx=ast.Load())]
        assert False, f" got {assign}"
    elif isinstance(assign, ast.Assign) and isinstance(assign.value, ast.Call):
        if isinstance(assign.value.func, (ast.Name, ast.Attribute)):
            is_dataclass_args = [assign.value.func]
        else:
            raise ValueError(f"check is dataclass unexpected type:{ast.dump(assign)}")

    elif isinstance(assign, ast.Call):
        if isinstance(assign.func, (ast.Name, ast.Attribute)):
            is_dataclass_args = [assign.func]
        else:
            raise ValueError(f"check is dataclass unexpected type:{ast.dump(assign)}")
    else:
        return False
    # add ast expr with assignment to check if is dataclass
    # eg.  is_dataclass_return = is_dataclass(is_dataclass_args)
    is_dataclass_call = ast.Call(func=ast.Name(id="is_dataclass", ctx=ast.Load()), args=is_dataclass_args, keywords=[])

    is_dataclass_result_assign_var_name = "is_dataclass_return"
    is_dataclass_result_assign = ast.Assign(
        targets=[ast.Name(id=is_dataclass_result_assign_var_name, ctx=ast.Store())], value=is_dataclass_call
    )

    ast_m = ast.parse("from dataclasses import is_dataclass")
    if imports is not None:
        ast_m.body.extend(imports)
    ast_m.body.append(is_dataclass_result_assign)

    ast.fix_missing_locations(ast_m)

    return ast_to_dict(ast_m)[is_dataclass_result_assign_var_name]

def _get_dataclass_expr(assign: Union[ast.Assign, ast.Call, str]) -> Optional[Union[ast.Name, ast.Attribute]]:
    is_dataclass_args: Optional[Union[ast.Name, ast.Attribute]] = None
    if isinstance(assign, str):
        is_dataclass_args = ast.Name(id=assign, ctx=ast.Load())
        assert False, f" got {assign}"
    elif isinstance(assign, ast.Assign) and isinstance(assign.value, ast.Call):
        if isinstance(assign.value.func, (ast.Name, ast.Attribute)):
            is_dataclass_args = assign.value.func
        else:
            raise ValueError(f"check is dataclass unexpected type:{ast.dump(assign)}")

    elif isinstance(assign, ast.Call):
        if isinstance(assign.func, (ast.Name, ast.Attribute)):
            is_dataclass_args = assign.func
        else:
            raise ValueError(f"check is dataclass unexpected type:{ast.dump(assign)}")
    else:
        return None
    return is_dataclass_args

def is_dataclass_same(assign_target: Union[ast.Assign, ast.Call, str], assign_base: Union[ast.Assign, ast.Call, str], imports: Optional[List[Union[ast.Import, ast.ImportFrom]]]) -> bool:
    """for assign check if the call is a dataclass by calling by using imports dataclasses.is_dataclass"""
    is_dataclass_args_target = _get_dataclass_expr(assign_target)
    is_dataclass_args_base = _get_dataclass_expr(assign_base)
    if is_dataclass_args_target is None or  is_dataclass_args_base is None:
        return False
    
    # add ast expr with assignment to check if is dataclass
    # eg.  is_dataclass_return = is_dataclass(is_dataclass_args)

    # AST for is_dataclass_return_target = is_dataclass(target_class_name)
    is_dataclass_call_target = ast.Call(func=ast.Name(id="is_dataclass", ctx=ast.Load()), args=[is_dataclass_args_target], keywords=[])
    is_dataclass_result_assign_var_name_target = "is_dataclass_return_target"
    is_dataclass_result_assign_target = ast.Assign(
        targets=[ast.Name(id=is_dataclass_result_assign_var_name_target, ctx=ast.Store())], value=is_dataclass_call_target
    )

    # AST for is_dataclass_return_base = is_dataclass(base_class_name)
    is_dataclass_result_assign_var_name_base = "is_dataclass_return_base"
    is_dataclass_call_base = ast.Call(func=ast.Name(id="is_dataclass", ctx=ast.Load()), args=[is_dataclass_args_base], keywords=[])
    assert is_dataclass_result_assign_var_name_base != is_dataclass_result_assign_var_name_target
    is_dataclass_result_assign_base = ast.Assign(
        targets=[ast.Name(id=is_dataclass_result_assign_var_name_base, ctx=ast.Store())], value=is_dataclass_call_base
    )

    # AST Comparator comparar_same_class = base_class_name == target_class_name
    same_class_result_assign_var_name = "compare_same_class"
    compare_call_base = ast.Compare(ops=[ast.Eq()],left=is_dataclass_args_target, 
                                    comparators=[is_dataclass_args_base])
    is_dataclass_result_assign_campare = ast.Assign(
        targets=[ast.Name(id=same_class_result_assign_var_name, ctx=ast.Store())],
        value=compare_call_base,
    )
    
    ast_m = ast.parse("from dataclasses import is_dataclass")
    if imports is not None:
        ast_m.body.extend(imports)
        print(f"DEBUG: is_dataclass_same imports added: {len(imports)}") # __AUTO_GENERATED_PRINT_VAR_END__
    else:
        print(f"DEBUG: not added ") # __AUTO_GENERATED_PRINT_VAR_END__
    ast_m.body.append(is_dataclass_result_assign_base)
    ast_m.body.append(is_dataclass_result_assign_target)
    ast_m.body.append(is_dataclass_result_assign_campare)

    ast.fix_missing_locations(ast_m)
    eval_dict = ast_to_dict(ast_m)
    return eval_dict[is_dataclass_result_assign_var_name_target] and eval_dict[is_dataclass_result_assign_var_name_base] and eval_dict[same_class_result_assign_var_name]



def _is_dataclass_name_id(
    name_id: Union[str, ast.Name, ast.Attribute], imports: List[Union[ast.Import, ast.ImportFrom]]
) -> bool:
    """for assign check if the call is a dataclass by calling by using imports dataclasses.is_dataclass"""


    is_dataclass_args = [name_id]
    # add ast expr with assignment to check if is dataclass
    # eg.  is_dataclass_return = is_dataclass()
    is_dataclass_call = ast.Call(func=ast.Name(id="is_dataclass", ctx=ast.Load()), args=is_dataclass_args, keywords=[])

    is_dataclass_result_assign_var_name = "is_dataclass_return"
    is_dataclass_result_assign = ast.Assign(
        targets=[ast.Name(id=is_dataclass_result_assign_var_name, ctx=ast.Store())], value=is_dataclass_call
    )

    ast_m = ast.parse("from dataclasses import is_dataclass")
    ast_m.body.extend(imports)
    ast_m.body.append(is_dataclass_result_assign)

    return ast_to_dict(ast_m)[is_dataclass_result_assign_var_name]


def _body_idx_after_last_import(target: ast.Module) -> int:
    for i, stmt in enumerate(reversed(target.body)):
        if _is_import(stmt):
            return len(target.body) - i

    return 0


def extract_assign_base_files(expr_target: ast.Module, assign_arget_name_id: str, imports: str) -> List[str]:
    ast_m = ast.parse(imports)
    for expr in expr_target.body:
        # match expr:
        #     case ast.Assign(targets = [ast.Name(),],):
        #         if len(expr.targets) and expr.targets[0].id == assign_arget_name_id:
        #             ast_m.body.append(expr)
        #     case _:
        #         continue
        if (
            isinstance(expr, ast.Assign)
            and len(expr.targets)
            and isinstance(expr.targets[0], ast.Name)
            and expr.targets[0].id == assign_arget_name_id
        ):
            ast_m.body.append(expr)
        else:
            continue

    base_files = ast_to_dict(ast_m).get(assign_arget_name_id)
    if base_files is None:
        return []
    elif isinstance(base_files, str):
        return [base_files]
    elif isinstance(base_files, list) and all((isinstance(v, str) for v in base_files)):
        return base_files
    else:
        raise ValueError(
            f"Config base file type not supported, must be str or List[str] got value={base_files} type={type(base_files)}"
        )


def parse_file(file_name: Union[Path, str]):

    with open(file_name, encoding='utf-8') as f_target:
        try:
            return ast.parse(f_target.read())
        except SyntaxError as e:
            runpy.run_path(str(file_name)) # better error msg


def merge(target: ast.Module, base: ast.Module) -> ast.Module:
    # TODO merge imports
    base_assigments = [s for s in base.body if isinstance(s, ast.Assign)]

    base_assigments_id_merged: List[str] = []
    fix_missing_locations_needed = False
    # all_import = get_imports(base).extend(target)
    imports_base = get_imports(target)
    imports_target = get_imports(base)
    imports_combinded = [*imports_base,*imports_target]
    for a in  imports_combinded:
        print(f"DEBUG: merge a: {ast.dump(a)}") # __AUTO_GENERATED_PRINT_VAR_END__

    for i, stm in enumerate(target.body):
        if not isinstance(stm, ast.Assign):
            continue
        # merge or add assignment

        assert len(stm.targets) == 1, "not implemented multiple targets"
        assert isinstance(stm.targets[0], ast.Name)
        # merge target dics with base
        if (same_base_assign := _get_same_assign(stm, base_assigments)) is not None:
            base_assigments_id_merged.append(stm.targets[0].id)
            if _is_dict_assign(stm) and _is_dict_assign(same_base_assign):
                # merge two dicts
                stm_merged = _merge_assign_dict(stm, same_base_assign, imports_combinded)
                # TODO: check im manipulation while iter is ok
                ast_trans = AstAssinTransform(stm_merged)
                ast_trans.visit(target)
                assert ast_trans.num_replacement == 1
                fix_missing_locations_needed = True
            # elif is_dataclass(stm, imports_combinded) and is_dataclass(same_base_assign, imports_combinded):
            elif is_dataclass_same(stm, same_base_assign, imports_combinded):

                stm_merged = _merge_assign_data_class(stm, same_base_assign, imports_combinded)
                # TODO: check im manipulation while iter is ok
                ast_trans = AstAssinTransform(stm_merged)
                ast_trans.visit(target)
                assert ast_trans.num_replacement == 1
                fix_missing_locations_needed = True

    # add base imports to target at top via revered order, skip merged assignments
    # for stm_import in base_imports:
    #     target.body.insert(0, stm_import)
    # add base assigments which are not in target and not merge before

    for stm_base in reversed(base.body):
        # if _is_import(stm_base):
        #     continue
        # TODO: perf iter to get idx can be avoided
        target_idx_blow_import = _body_idx_after_last_import(target)
        if isinstance(stm_base, ast.Assign):
            assert isinstance(stm_base.targets[0], ast.Name)
            if stm_base.targets[0].id not in base_assigments_id_merged:
                target.body.insert(target_idx_blow_import, stm_base)
        else:
            target.body.insert(target_idx_blow_import, stm_base)
    # TODO: check for same imports
    if fix_missing_locations_needed:
        ast.fix_missing_locations(target)

    # for i, c in enumerate(target.body):
    #     print(f"{i}:\n{ast.dump(c)}")
    #
    # for i, c in enumerate(base.body):
    #     print(f"BASE {i}:\n{ast.dump(c)}")
    return target


class AstAssinTransform(ast.NodeTransformer):
    """extracts args for class a call"""

    def __init__(self, new_assign: ast.Assign):
        self.new_assign = new_assign
        self.num_replacement = 0
        assert len(new_assign.targets) == 1
        assert isinstance(new_assign.targets[0], ast.Name)

    def visit_Assign(self, node):
        # class is used to create a class
        if len(node.targets) != 1:
            return node

        if isinstance(node.targets[0], ast.Name):
            if self.new_assign.targets[0] == node.targets[0]:
                self.num_replacement += 1
                return self.new_assign
        return node


class AstLoadClassCallArgsExtrator(ast.NodeTransformer):
    """extracts args for class a call"""

    def __init__(self, class_atrr: Optional[str], class_name: str):
        self.class_name = class_name
        self.class_module = class_atrr
        # collect args and kwargs
        self.collected_args: List[ast.expr] = []

    def visit_Call(self, node):
        # class is used to create a class
        assert isinstance(node, ast.Call)  # k
        if isinstance(node.func, ast.Name) and isinstance(node.func.ctx, ast.Load):
            # class definition is local or imorted with "form xyz import TheClass"
            if node.func.id == self.class_name:
                self.collected_args.extend(node.args)
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == self.class_module and node.func.attr == self.class_name:
                self.collected_args.extend(node.args)
        return node

    def visit_Assign(self, node):
        # visit all Call create for assignment with visit_Call
        return self.generic_visit(node)


def has_multi_name_assigment(tree: ast.Module) -> bool:
    return True


def unparse(tree: ast.Module) ->Optional[str]:
    if sys.version_info >= (3, 9):
        return str(ast.unparse(tree)) 
    return None

def to_unparse_file(file_name: Union[str, Path], tree: ast.Module) -> bool:
    if (content := unparse(tree)) is not None:
        content = black.format_str(content, 
                                   mode = black.FileMode(),)
        with open(file_name, "w") as f:
            print(content, file=f)
        return True
    return False

def _is_import(stmt: ast.stmt) -> bool:
    return isinstance(stmt, (ast.Import, ast.ImportFrom))


def get_imports(codes: ast.Module) -> List[Union[ast.Import, ast.ImportFrom]]:
    stm_imports = []
    for i, stm in enumerate(codes.body):
        if _is_import(stm):
            stm_imports.append(stm)
    return stm_imports


def get_dataclass_def(codes: ast.Module) -> List[ast.ClassDef]:
    stm_imports = []
    for stm in codes.body:
        # TODO check for decorator_list better
        if isinstance(stm, ast.ClassDef) and len(stm.decorator_list):
            stm_imports.append(stm)
    return stm_imports

class _RemoveAssignFromAST(ast.NodeTransformer):
    """Remove Assign node if the target's name match the key.

    Args:
        key (str): The target name of the Assign node.
    """

    def __init__(self, key:str):
        self.key = key
        self.rm_cnt =0

    def visit_Assign(self, node):
        if (isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == self.key):

            self.rm_cnt +=1
            return None
        else:
            return node

def remove_assigment(var_name:str,tree: ast.Module) -> int:
    vister = _RemoveAssignFromAST(key = var_name)
    vister.visit(tree)
    return vister.rm_cnt


if __name__ == "__main__":
    #  example for some development debug print
    c = r"""
BAR = 1
BAR = {"HHHAALLO": lataclasses.MISSING}
"""

    codes = ast.parse(c)
    for i, c in enumerate(codes.body):
        print(f"{i}:\n{ast.dump(c)}")

