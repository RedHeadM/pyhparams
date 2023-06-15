# based on OpenMMLab. All rights reserved and significant changes made to software.
import ast
import os.path as osp
import types
import dataclasses
from argparse import Action, ArgumentParser, Namespace
from collections import abc
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple, Union, Dict
from pyhparams import ast as ast_helper
from pyhparams import ast_data_fields_resolve 
from pyhparams.ast_data_fields_resolve import ast_resolve_dataclass_filed

# from addict import Dict
# from yapf.yapflib.yapf_api import FormatCode

# from mmengine.fileio import dump, load
# from mmengine.utils import (get_installed_path,
#                              import_modules_from_strings, is_installed)
# from .utils import (RemoveAssignFromAST, _get_external_cfg_base_path,
#                     _get_external_cfg_path, _get_package_and_cfg_path)

BASE_KEY_ID = '_base_'
# DELETE_KEY = '_delete_'
# RESERVED_KEYS = ['filename', 'text', 'pretty_text', 'env_variables']

# from dataclasses import dataclass
# # default config
# @dataclass
# class MLConfig():
#     data_root:str = "" 
#     @dataclass
#     class Trainer():
#         lr: float  = 0.001
#         epochs: int = 1000
#         # dataset = torch.dataset.MINIST(data_root= "$DATA_ROOT")
#         dataset = torch.dataset.MINIST(data_root= Config.EXPAND_VAR("DATA_ROOT", str))
#     trainer: Trainer = Trainer()
#
# # config py
# _config_ = Config(
#             trainer = Trainer(lr = 0.1, epochs =1)
#         )
#     



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

def _dict_from_file(filename: str) -> dict:
    # TODO str to pathlib
    base_cfg_dict = {}
    if filename.endswith(('.py', '.pyhparams')):
        expr_target = ast_helper.parse_file(filename)
        # codes = _RemoveAssignFromAST(BASE_KEY).visit(expr_target)
        base_files = ast_helper.extract_assign_base_files(expr_target, BASE_KEY_ID, imports= "from pathlib import Path") 
        print(f"INFO: config loading target config: {filename}") # TODO: logging
        for base_file_name in base_files:
            print(f"INFO: config merge with base: {base_file_name}")
            expr_base = ast_helper.parse_file(base_file_name)
            expr_target = ast_helper.merge(expr_target, base=expr_base)
        # Support load global variable in nested function of the

        resolved_epxpr_target = ast_resolve_dataclass_filed(expr_target)
        return ast_helper.ast_to_dict(resolved_epxpr_target)

    elif filename.endswith(('.yml', '.yaml', '.json')):
        raise NotImplementedError(f"file not supported: {filename}")
        # cfg_dict = load(temp_config_file.name)
    else:
        raise ValueError(f"file not supported: {filename}")

class Config:
    @staticmethod
    def create_from_file(filename: Union[str, Path],
                 use_predefined_variables: bool = True,
                 import_custom_modules: bool = True,
                 use_environment_variables: bool = True) -> 'Config':
        """Build a Config instance from config file.

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
        dict_f = _dict_from_file(filename)
        return dataclasses.make_dataclass('Config', dict_f)(**dict_f)
