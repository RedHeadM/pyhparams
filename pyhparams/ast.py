import ast
import itertools
from contextlib import redirect_stdout
from sys import modules
from typing import Any, Dict, List, Optional

def ast_to_dict(tree: ast.Module)-> Dict[str,Any]:
    ''' runs ast modules and exports local and global var at top level to dict '''
    codeobj = compile(tree, '', mode='exec')
    # Support load global variable in nested function of the
    # config.
    global_locals_var = {}
    eval(codeobj,global_locals_var,global_locals_var)
    cfg_dict = {
        key: value
        for key, value in global_locals_var.items()
        if (not key.startswith('__'))
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
    for k, v in zip(target.keys, target.values):
        if k is None:
            continue
        assert isinstance(k, ast.Constant), f'dict key must be const {ast.dump(k)}'
        keys_merged.append(k)
        
        if (same_value_base := base_key_value.get(k)) is not None and \
             isinstance(same_value_base, ast.Dict) and isinstance(v, ast.Dict):
                # merge dict
                values_merged.append(_merge_dict(v, same_value_base))
        else:
            # keep value 
            values_merged.append(v)
        print(f"target with key {ast.dump(k)} value {ast.dump(v)}")
    # add 
    # assert compare_ast(ast.Constant("asd"), ast.Constant("asd"))
    assert len(keys_merged) ==2
    for k_base, v_base in base_key_value.items():
        if k_base is None:
            continue
        if any((compare(k_base,s) for s in keys_merged ) ):
            continue
        else:
            # not merged before and not in target
            keys_merged.append(k_base)
            values_merged.append(v_base)
            print(f"-- base with {ast.dump(k_base)} value {ast.dump(v_base)}")

    return ast.Dict(keys =keys_merged,  values =values_merged)

def _merge_assign_dict(target: ast.Assign, base: ast.Assign) -> ast.Assign:
    # check if both are expected dict type
    for s in (target, base):
        assert isinstance(s, ast.Assign)
        assert len(s.targets) == 1
        assert isinstance(s.targets[0], ast.Name)
        # assert isinstance(s.value, ast.Dict)

    assert isinstance(target.value, ast.Dict)
    assert isinstance(base.value, ast.Dict)
    target.value= _merge_dict(target.value,base.value)
    return target

def _is_dict_assign(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Dict)

def merge(target: ast.Module, base: ast.Module) -> ast.Module:
    # TODO merge imports
    base_assigments = [s for s in base.body if isinstance(s, ast.Assign)]

    base_assigments_id_merged: List[str] = []
    fix_missing_locations_needed = False

    for i, stm in enumerate(target.body):
        if not isinstance(stm,ast.Assign):
            continue
        # merge or add assignments 
        print(f"DEBUG: _get_same_assign stm: {ast.dump(stm)}") # __AUTO_GENERATED_PRINT_VAR__

        assert len(stm.targets) == 1, "not implemented"
        assert isinstance(stm.targets[0], ast.Name)

        if (same_base_assign := _get_same_assign(stm, base_assigments)) is not None:

            base_assigments_id_merged.append(stm.targets[0].id)
            if _is_dict_assign(stm) and _is_dict_assign(same_base_assign):
                # merge two dicts
                stm_merged = _merge_assign_dict(stm, same_base_assign)
                # TODO: check im manipulation while iter is ok
                AstAssinTransform(stm_merged).visit(target)
                fix_missing_locations_needed = True

            else: 
                # replace value py not merging later
                pass
    # TODO add merge
    for stm_base in base_assigments:
        assert isinstance(stm_base.targets[0], ast.Name)
        if stm_base.targets[0].id not in  base_assigments_id_merged:
            target.body.append(stm_base)
    if fix_missing_locations_needed:
        ast.fix_missing_locations(target)
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

if __name__ == '__main__':

    #  example for some development debug print
    c = r'''
BAR = 1
BAR = {"HHHAALLO": lataclasses.MISSING}
'''

    codes = ast.parse(c)
    for i, c in enumerate(codes.body):
        print(f"{i}:\n{ast.dump(c)}")
