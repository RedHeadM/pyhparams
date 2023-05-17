# based on OpenMMLab. All rights reserved and significant changes made to software.
import ast
import os.path as osp
import types
import dataclasses
from argparse import Action, ArgumentParser, Namespace
from collections import abc
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple, Union, Dict
import ast

# from addict import Dict
# from yapf.yapflib.yapf_api import FormatCode

# from mmengine.fileio import dump, load
# from mmengine.utils import (get_installed_path,
#                              import_modules_from_strings, is_installed)
# from .utils import (RemoveAssignFromAST, _get_external_cfg_base_path,
#                     _get_external_cfg_path, _get_package_and_cfg_path)

BASE_KEY = '_base_'
DELETE_KEY = '_delete_'
DEPRECATION_KEY = '_deprecation_'
RESERVED_KEYS = ['filename', 'text', 'pretty_text', 'env_variables']

import re  # type: ignore


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

def _dict_from_file(filename: str):
    base_cfg_dict = {}
    if filename.endswith('.py'):
        with open(filename, encoding='utf-8') as f:
            codes = ast.parse(f.read())
            print(f"DEBUG: _dict_from_file codes: {ast.dump(codes)}") # __AUTO_GENERATED_PRINT_VAR__
            codes = _RemoveAssignFromAST(BASE_KEY).visit(codes)
            print(f"DEBUG: _dict_from_file codes: {codes}") # __AUTO_GENERATED_PRINT_VAR__
        codeobj = compile(codes, '', mode='exec')
        # Support load global variable in nested function of the
        # config.
        global_locals_var = {'_base_': base_cfg_dict}
        ori_keys = set(global_locals_var.keys())
        eval(codeobj, global_locals_var, global_locals_var)
        cfg_dict = {
            key: value
            for key, value in global_locals_var.items()
            if (key not in ori_keys and not key.startswith('__'))
        }
    else:
        raise NotImplementedError(f"file not supported: {filename}")
    # rm python file dics
    for key, value in list(cfg_dict.items()):
        if isinstance(value, (types.FunctionType, types.ModuleType)):
            cfg_dict.pop(key)
    return cfg_dict


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
            raise OSError('Only py/yml/yaml/json type are supported now!')

        # read config and get base files list
        dict_f = _dict_from_file(filename)
        return dataclasses.make_dataclass('Config', dict_f)(**dict_f)
        #     dict_f)
