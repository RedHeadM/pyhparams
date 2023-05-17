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

def _merge_dict(target: ast.Dict, base: ast.Dict) -> ast.Dict:

    base_key_value = dict(zip(base.keys, base.values))
    keys_merged = []
    values_merged = []
    # TODO: fix this fuktion 
    def _get(ast_dict, key):
        for k,v in ast_dict.items():
            if compare(k,key):
                return v
        return None

    for k, v in zip(target.keys, target.values):
        if k is None:
            continue
        assert isinstance(k, ast.Constant), f'dict key must be const {ast.dump(k)}'
        keys_merged.append(k)
        
        if (same_value_base := _get(base_key_value, k)) is not None and \
             isinstance(same_value_base, ast.Dict) and isinstance(v, ast.Dict):
                # merge dict
                values_merged.append(_merge_dict(v, same_value_base))
        else:
            # keep value 
            values_merged.append(v)
    # add not merged base items
    for k_base, v_base in base_key_value.items():
        if k_base is None:
            continue
        if any((compare(k_base,s) for s in keys_merged ) ):
            continue
        else:
            # not merged before and not in target
            keys_merged.append(k_base)
            values_merged.append(v_base)

    return ast.Dict(keys =keys_merged,  values =values_merged)

# def _merge_dict(target: ast.Dict, base: ast.Dict) -> ast.Dict:

def _merge_assign_dict(target: ast.Assign, base: ast.Assign) -> ast.Assign:
    # check if both are expected dict type
    for s in (target, base):
        assert isinstance(s, ast.Assign)
        assert len(s.targets) == 1
        assert isinstance(s.targets[0], ast.Name)
        # assert isinstance(s.value, ast.Dict)

    assert isinstance(target.value, ast.Call)
    assert isinstance(base.value, ast.Call)
    target.value= _merge_dict(target.value, base.value)
    return target
# {} Dict key[list[cost]] value
# dict Call keywords=[keyword(arg='name', value=Constant(value='foo'))]

# dc only kwargs keywords=[keyword(arg='name', value=Constant(value='foo'))]

def _is_mergeable(target: ast.stmt, base: ast.stmt) -> Optional:
    ''' if dict (can be ast.Dict ast.Call to dict) oder dataclass''' 
    pass

def _merge_keyword(target: List[ast.keyword], base: List[ast.keyword]) -> List[ast.keyword]:
    target_kw = {k.arg: k.value for k in target}
    base_kw = {k.arg: k.value for k in base}
    merged_kew = dict()
    # TODO: fix this fuktion 
    # def _get(ast_dict, key):
    #     for k,v in ast_dict.items():
    #         if compare(k,key):
    #             return v
    #     return None

    for k, v in target_kw.items():
        if k is None:
            continue
        assert isinstance(k, ast.Constant), f'dict key must be const {ast.dump(k)}'
        keys_merged.append(k)
        
        if (same_value_base := base_kw.get( k)) is not None and \
             isinstance(same_value_base, ast.Dict) and isinstance(v, ast.Dict):
                # merge dict
                merged_kew[k]=_merge_dict(v, same_value_base)
        else:
            # keep value 
            merged_kew[k]=v
    # add not merged base items
    for k_base, v_base in base_key_value.items():
        if k_base is None:
            continue
        if any((compare(k_base,s) for s in keys_merged ) ):
            continue
        else:
            # not merged before and not in target
            keys_merged.append(k_base)
            values_merged.append(v_base)

    return ast.Dict(keys =keys_merged,  values =values_merged)

def _merge_assign_data_class(target: ast.Assign, base: ast.Assign) -> ast.Assign:
    # check if both are expected dict type
    # for s in (target, base):
    #     assert isinstance(s, ast.Assign)
    #     assert len(s.targets) == 1
    #     assert isinstance(s.targets[0], ast.Name)
    #     # assert isinstance(s.value, ast.Dict)
    #
    # assert isinstance(target.value, ast.Dict)
    # assert isinstance(base.value, ast.Dict)
    # target.value= _merge_call(target.value,base.value)
    return target

def _is_dict_assign(stmt: ast.stmt) -> bool:
    # TODO: Assign(targets=[Name(id='FOO3_attr', ctx=Store())], value=Call(func=Name(id='dict', ctx=Load()), args=[], keywords=[keyword(arg='name', value=Constant(value='foo'))]))
    return isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Dict)

def _is_dataclass_assign(assign: ast.Assign, imports: List[Union[ast.Import, ast.ImportFrom]]) -> bool:
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

    for i, c in enumerate(ast_m.body):
        print(f"{i}:\n{ast.dump(c)}")
    return ast_to_dict(ast_m)[is_dataclass_result_assign_var_name]


def _body_idx_after_last_import(target: ast.Module) -> int: 
    for i, stmt in  enumerate(reversed(target.body)):
        if _is_import(stmt):
            return len(target.body)-i 

    return 0


def merge(target: ast.Module, base: ast.Module) -> ast.Module:
    base_assigments = [s for s in base.body if isinstance(s, ast.Assign)]

    base_assigments_id_merged: List[str] = []
    fix_missing_locations_needed = False
    # all_import = get_imports(base).extend(target)
    imports_base = get_imports(target)
    imports_target = get_imports(base)

    assignments_stmt = (a for a in target.body if isinstance(a, ast.Assign))
    for i, stm in enumerate(assignments_stmt):
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
                AstAssinTransform(stm_merged).visit(target)
                fix_missing_locations_needed = True
            elif _is_dataclass_assign(stm, imports_target) and _is_dataclass_assign(same_base_assign,imports_base):
                raise NotImplementedError("merge dataclass_assign")

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
        print(f"DEBUG print {i}:\n{ast.dump(c)}")
    #
    # for i, c in enumerate(base.body):
    #     print(f"BASE {i}:\n{ast.dump(c)}")
    return target

class AstAssinTransform(ast.NodeTransformer):
    ''' extracts args for class a call'''
    def __init__(self, new_assign: ast.Assign):
        self.new_assign = new_assign

        assert len(new_assign.targets) == 1
        assert isinstance(new_assign.targets[0], ast.Name)

    def visit_Assign(self, node):
        # class is used to create a class
        if len(node.targets) != 1:
            return node

        if isinstance(node.targets[0], ast.Name):
            if self.new_assign.targets[0] == node.targets[0]:
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
