# based on OpenMMLab. All rights reserved and significant changes made to software.
import ast
import os.path as osp
import os
import dataclasses
from pathlib import Path
from typing import TypeVar, Union, Optional, Tuple, Dict
from pyhparams import ast as ast_helper
from pyhparams.ast_data_fields_resolve import ast_resolve_dataclass_filed


BASE_KEY_ID = '_base_'
BASE_KEY_CONFIG_EXTRACT = '_config_'



def check_file_exist(filename, msg_tmpl='file "{}" does not exist'):
    if not osp.isfile(filename):
        raise FileNotFoundError(msg_tmpl.format(filename))

class _RemoveAssignFromAST(ast.NodeTransformer):
    """Remove Assign node if the target's name match the key.

    Args:
        key (str): The target name of the Assign node.
    """

    def __init__(self, key):
        self.key = key

    def visit_Assign(self, node):
        if (isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == self.key):
            return None
        else:
            return node

def _expand_base_vars(filename: str, base_path_variables: Optional[Dict[str, str]]) -> str :
    filename_expand = os.path.expandvars(filename)
    if base_path_variables is not None:
        for var_name, var_to in base_path_variables.items():
            if var_name in filename_expand:
                filename_expand = filename_expand.replace(var_name, var_to)
    if filename_expand != filename: 
        print(f"INFO: expand pase form={filename} to={filename_expand}")
    return filename_expand

def _ast_from_file(filename: str, base_path_variables: Optional[Dict[str, str]]) -> ast.Module:
    # TODO str to pathlib
    if filename.endswith(('.py', '.pyhparams')):
        expr_target = ast_helper.parse_file(filename)
        # codes = _RemoveAssignFromAST(BASE_KEY).visit(expr_target)
        base_files = ast_helper.extract_assign_base_files(expr_target, BASE_KEY_ID, imports= "from pathlib import Path") 
        print(f"INFO: config loading target config: {filename}") # TODO: logging
        for base_file_name in base_files:
            base_file_name = _expand_base_vars(base_file_name, base_path_variables)
            print(f"INFO: config merge with base: {base_file_name}")
            expr_base = ast_helper.parse_file(base_file_name)
            expr_target = ast_helper.merge(expr_target, base=expr_base)
        # Support load global variable in nested function of the

        resolved_epxpr_target = ast_resolve_dataclass_filed(expr_target)
        return resolved_epxpr_target

    elif filename.endswith(('.yml', '.yaml', '.json')):
        raise NotImplementedError(f"file not supported: {filename}")
        # cfg_dict = load(temp_config_file.name)
    else:
        raise ValueError(f"file not supported: {filename}")


_T = TypeVar("_T")
class Config:
    @staticmethod
    def create_from_file(filename: Union[str, Path],
                 merged_output_file: Optional[Union[str,Path]] = None,
                 base_path_vars: Optional[Dict[str, str]] = None) -> Tuple[_T, Optional[Path]]:
        """Build a Config instance from config file(.py pyhparam).

        Args:
            filename (str or Path): Name of config file.
            use_predefined_variables (bool, optional): Whether to use
                predefined variables. Defaults to True.
            import_custom_modules (bool, optional): Whether to support
                importing custom modules in config. Defaults to True.

        Returns:
            Config: Config instance built from config file.
        """
        filename = osp.abspath(osp.expanduser(filename))
        check_file_exist(filename)
        fileExtname = osp.splitext(filename)[1]
        if fileExtname not in ['.py', '.json', '.yaml', '.yml']:
            raise OSError('Only py/yml/yaml/json type are not supported')


        # read config and get base files list
        merged_ast_from_file = _ast_from_file(filename, base_path_vars)

        ret_merged_output_file = None
        if merged_output_file is None:
            dict_f = ast_helper.ast_to_dict(merged_ast_from_file)
        else: 
            if ast_helper.to_unparse_file(merged_output_file, merged_ast_from_file):
                dict_f = ast_helper.ast_to_dict(merged_ast_from_file)
                ret_merged_output_file = merged_output_file
            else:
                print(f"WARN: config to file failed: {filename}") 
                dict_f = ast_helper.ast_to_dict(merged_ast_from_file)

        if (conf := dict_f.get(BASE_KEY_CONFIG_EXTRACT)) is not None:
            return (conf, ret_merged_output_file)
        else:
            dc = dataclasses.make_dataclass('Config', dict_f)(**dict_f)
            return (dc, ret_merged_output_file)
