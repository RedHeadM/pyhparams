import ast
from typing import Any, Dict, List, Optional

def ast_to_dict(tree: ast.Module)-> Dict[str,Any]:
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


if __name__ == '__main__':

    #  example for some development debug print
    c = r'''
BAR = 1
BAR = {"HHHAALLO": lataclasses.MISSING}
'''

    codes = ast.parse(c)
    for i, c in enumerate(codes.body):
        print(f"{i}:\n{ast.dump(c)}")
