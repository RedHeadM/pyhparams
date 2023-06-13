import ast
import sys
import itertools
from contextlib import redirect_stdout
from sys import modules
from types import ModuleType
from typing import Any, Dict, List, Optional, Union

def ast_to_dict(tree: ast.Module)-> Dict[str,Any]:
    ''' runs ast modules and exports local and global var at top level to dict '''
    codeobj = compile(tree, '', mode='exec')
    # Support load global variable in nested function of the
    # config.
    global_locals_var = {} #{"__name__":""}
    eval(codeobj,global_locals_var,global_locals_var)

    cfg_dict = {
        key: value
        for key, value in global_locals_var.items()
        if (not key.startswith('__')) and (not isinstance(value,ModuleType))
    }
    return cfg_dict

def _get_same_assign(target: ast.Assign, base: List[ast.Assign] ) -> Optional[ast.Assign]:

    assert isinstance(target, ast.Assign)
    assert len(target.targets) == 1
    assert isinstance(target.targets[0], ast.Name)

    for stm in base:
        assert isinstance(target, ast.Assign)
        assert isinstance(stm.targets[0], ast.Name)
        assert len(stm.targets) == 1
        if stm.targets[0].id is  target.targets[0].id:
        # if stm.targets[0] is  target.targets[0]: # TODO
            return stm
    return None

def compare(node1, node2):
    ## TODO: simpler func here
    if type(node1) is not type(node2):
        return False
    if isinstance(node1, ast.AST):
        for k, v in vars(node1).items():
            if k in ('lineno', 'col_offset', 'ctx'):
                continue
            if not compare(v, getattr(node2, k)):
                return False
        return True
    elif isinstance(node1, list):
        return all(itertools.starmap(compare, zip(node1, node2)))
    else:
        return node1 == node2


def _merge_assign_dict(target: ast.Assign, base: ast.Assign) -> ast.Assign:
    # check if both are expected dict type
    for s in (target, base):
        assert isinstance(s, ast.Assign)
        assert len(s.targets) == 1
        assert isinstance(s.targets[0], ast.Name)

    target.value = _merge_dict_call(target.value,base.value)
    return target

def _merge_dict_call(target: ast.expr, base: ast.expr) -> ast.Call:
    kw_base  = _unpack_keywords(base)
    kw_target  = _unpack_keywords(target)
    assert kw_base is not None and kw_target is not None # TODO 
    kw_merged = _merge_keyword(kw_target, kw_base)
    # allway map ast.Dict to ast.Call with function dict
    return ast.Call(func=ast.Name(id='dict', ctx=ast.Load()), args=[], keywords=kw_merged) 

def _merge_assign_data_class(target: ast.Assign, base: ast.Assign, ) -> ast.Assign:
    # check if both are expected dict type
    for s in (target, base):
        assert isinstance(s, ast.Assign)
        assert len(s.targets) == 1
        assert isinstance(s.targets[0], ast.Name)
        assert isinstance(s.value, ast.Call)

    kw_base  = _unpack_keywords(base.value)
    kw_target = _unpack_keywords(target.value)
    assert kw_base is not None and kw_target is not None # TODO 
    kw_merged = _merge_keyword(kw_target, kw_base)
    assert isinstance(target.value, ast.Call)
    target.value.keywords = kw_merged 
    return target

def _merge_keyword(target: List[ast.keyword], base: List[ast.keyword]) -> List[ast.keyword]:
    target_kw = {k.arg: k.value for k in target}
    base_kw = {k.arg: k.value for k in base}
    merged_kew = dict(base_kw)
    # assert False, f"{[ast.dump(k) for k in target]}"

    for k, v in target_kw.items():
        assert k is not None
        assert isinstance(k, (ast.Constant, str)), f'dict key must be const got: {ast.dump(k)}'
        
        if (same_value_base := base_kw.get(k)) is not None and \
            _nested_call_is_dict(same_value_base) and _nested_call_is_dict(v):
                # recusive call for now
                merged_kew[k] = _merge_dict_call(v, same_value_base) 
            # TODO: nested dataclasses
        else:
            # keep value from target
            merged_kew[k] = v
    return [ast.keyword(arg=k, value=v) for k, v in merged_kew.items()]



def _nested_call_is_dict(assign_value: ast.expr) -> bool:
    ''' extract kwargs for dict call'''
    match assign_value:
        case ast.Call(
            func=ast.Call(func=ast.Name(id='dict', ctx=ast.Load()),),
        ):
            return True
        case ast.Dict():
            return True
        case _:
            return False

def _unpack_keywords(assign_value: ast.expr) -> Optional[List[ast.keyword]]:
    ''' extract kwargs for dict call'''
    # assert False, f"stm_merged :\n{ast.dump(assign_value)}"
    match assign_value:
        case ast.Call(
            # func=ast.Call(func=ast.Name(id='dict', ctx=ast.Load()),),
        ):
            assert assign_value.args is None or len(assign_value.args) == 0
            return assign_value.keywords
        case ast.Dict():
            assert assign_value.values is not None
            assert assign_value.keys is not None
            # NOTE: caution a never use ast.keyword(args=... instead of ast.keyword(arg=....
            return [ast.keyword(arg=_uppack_dict_key(k), value=v) for k, v in zip(assign_value.keys, assign_value.values) if k is not None]
        case _:
            return None

def _uppack_dict_key(key: ast.expr) -> str:
    match key:
        case ast.Constant():
            return key.value
            # return strkey
        case None:
            raise ValueError(f'got none for key {ast.dump(key)}')
        case _:
            return key

def _is_dict_assign(stmt: ast.Assign) -> bool:
    # TODO: Assign(targets=[Name(id='FOO3_attr', ctx=Store())], value=Call(func=Name(id='dict', ctx=Load()), args=[], keywords=[keyword(arg='name', value=Constant(value='foo'))]))
    assert isinstance(stmt, ast.Assign)
    return isinstance(stmt.value, ast.Dict) or _assign_is_dict_func_call(stmt)

def _assign_is_dict_func_call(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Dict)

def _is_dataclass_assign(assign: ast.Assign, imports: List[Union[ast.Import, ast.ImportFrom]]) -> bool:
    ''' for assign check if the call is a dataclass by calling by using imports dataclasses.is_dataclass'''
    ast_m = ast.parse("from dataclasses import is_dataclass")
    is_dataclass_args =None
    # TODO:clean up
    if isinstance(assign.value, ast.Call):
        assign_call = assign.value.func
        if isinstance(assign_call, ast.Name):
            is_dataclass_args = [assign_call] 
        elif isinstance(assign_call, ast.Attribute):
            is_dataclass_args = [assign_call] 
        else: 
            raise ValueError("check is dataclass")
    else:
        return False
    is_dataclass_call = ast.Call(func=ast.Name(id='is_dataclass', ctx=ast.Load()), 
                        args=is_dataclass_args, keywords=[])

    is_dataclass_result_assign_var_name = 'is_dataclass_return'
    is_dataclass_result_assign = ast.Assign(targets=[ast.Name(id=is_dataclass_result_assign_var_name, 
            ctx=ast.Store())], value=is_dataclass_call)   
    ast_m.body.extend(imports)
    ast_m.body.append(is_dataclass_result_assign)

    ast.fix_missing_locations(ast_m)
    # for i, c in enumerate(ast_m.body):
    #     print(f"{i}:\n{ast.dump(c)}")

    return ast_to_dict(ast_m)[is_dataclass_result_assign_var_name]


def _body_idx_after_last_import(target: ast.Module) -> int: 
    for i, stmt in  enumerate(reversed(target.body)):
        if _is_import(stmt):
            return len(target.body)-i 

    return 0


def merge(target: ast.Module, base: ast.Module) -> ast.Module:
    # TODO merge imports
    base_assigments = [s for s in base.body if isinstance(s, ast.Assign)]

    base_assigments_id_merged: List[str] = []
    fix_missing_locations_needed = False
    # all_import = get_imports(base).extend(target)
    imports_base = get_imports(target)
    imports_target = get_imports(base)

    for i, stm in enumerate(target.body):
        if not isinstance(stm,ast.Assign):
            continue
        # merge or add assignment

        assert len(stm.targets) == 1, "not implemented multiple targets"
        assert isinstance(stm.targets[0], ast.Name)
        # merge target dics with base
        if (same_base_assign := _get_same_assign(stm, base_assigments)) is not None:
            base_assigments_id_merged.append(stm.targets[0].id)
            if _is_dict_assign(stm) and _is_dict_assign(same_base_assign):
                # merge two dicts
                stm_merged = _merge_assign_dict(stm, same_base_assign)
                # TODO: check im manipulation while iter is ok
                ast_trans = AstAssinTransform(stm_merged)
                ast_trans.visit(target)
                assert  ast_trans.num_replacement == 1
                fix_missing_locations_needed = True
            elif _is_dataclass_assign(stm, imports_target) and _is_dataclass_assign(same_base_assign,imports_base):
                stm_merged = _merge_assign_data_class(stm, same_base_assign)
                # TODO: check im manipulation while iter is ok
                print(f"stm_merged {i}:\n{ast.dump(stm_merged)}")
                ast_trans = AstAssinTransform(stm_merged)
                ast_trans.visit(target)
                assert  ast_trans.num_replacement == 1
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
        if isinstance(stm_base, ast.Assign) :
            assert isinstance(stm_base.targets[0], ast.Name)
            if stm_base.targets[0].id not in base_assigments_id_merged:
                target.body.insert(target_idx_blow_import, stm_base)
        else:
            target.body.insert(target_idx_blow_import, stm_base)
    # TODO: check for same imports
    if fix_missing_locations_needed:
        ast.fix_missing_locations(target)

    for i, c in enumerate(target.body):
        print(f"{i}:\n{ast.dump(c)}")
    #
    # for i, c in enumerate(base.body):
    #     print(f"BASE {i}:\n{ast.dump(c)}")
    return target

class AstAssinTransform(ast.NodeTransformer):
    ''' extracts args for class a call'''
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
                self.num_replacement +=1
                return self.new_assign
        return node

class AstLoadClassCallArgsExtrator(ast.NodeTransformer):
    ''' extracts args for class a call'''
    def __init__(self,  class_atrr: Optional[str], class_name:str):
        self.class_name = class_name
        self.class_module = class_atrr
        # collect args and kwargs
        self.collected_args: List[ast.expr] = []

    
    def visit_Call(self, node):
        # class is used to create a class
        assert isinstance(node, ast.Call) #k
        if isinstance(node.func, ast.Name) and isinstance(node.func.ctx, ast.Load):
            #class definition is local or imorted with "form xyz import TheClass"
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

def unparse(tree: ast.Module):
    if sys.version_info[0] == 3 and sys.version_info[1] > 9 :
        return str(ast.unparse(tree)) 

def _is_import(stmt: ast.stmt) -> bool:
    return isinstance(stmt, (ast.Import,ast.ImportFrom))

def get_imports(codes: ast.Module) -> List[Union[ast.Import, ast.ImportFrom]]:
    stm_imports = []
    for i, stm in enumerate(codes.body):
        if _is_import(stm):
            stm_imports.append(stm)
    return stm_imports

if __name__ == '__main__':

    #  example for some development debug print
    c = r'''
BAR = 1
BAR = {"HHHAALLO": lataclasses.MISSING}
'''

    codes = ast.parse(c)
    for i, c in enumerate(codes.body):
        print(f"{i}:\n{ast.dump(c)}")
