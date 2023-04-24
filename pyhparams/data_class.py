# from dataclasses import dataclass, is_dataclass, Field, MISSING
import dataclasses
from typing import Any, Union, Callable, Optional, TypeVar
import typing
import functools 
import os
import typing

config_dataclass = functools.partial(dataclasses.dataclass, kw_only =True)
is_config_dataclass = dataclasses.is_dataclass
# ConfigField = dataclasses.Field

# Num = Union[int, float]

''' A sentinel value signifying a missing default '''
PARAM_MISSING = dataclasses.MISSING
''' indicate to substitute '''
# PARAM_SUBSTITUTE = dataclasses.MISSING
_PARAM_SUBSTITUTE = dataclasses.field(default=None)


# TODO: not nedded can be be just with os pat
class _PARAM_SUBSTITUTE:
    def __init__(self,name : str):
        self.name = name

    def __div__(self, val: str):
        ''' join path '''
        return os.path.join(str(self.name), val)

# @config_dataclass
# class ParmsTrainer:
#     # my_path: str = ENV_VAR('HOME') /
#     my_path: str = PARAM_FROM_BASE

# class Callbacks:
#     callbacks : typing.List[lightning.pytorch.callbacks.ModelCheckpoint]
#
# config
#
# img_shape = (23,32)
# _base_params = ["img_shape" : img_shape]
# _base_params = ["img_shape" : img_shape]
# _base_conf_ = ['foo.py']
#
# @config_dataclass
# class parmstrainer:
#     # my_path: str = env_var('home') /
#     my_path: str = param_from_base
#
# # foo.py
# import torchvision
# train_trainform = torchvision.transforms.compose([
#         torchvision.transforms.resize(param_load("var_name")),
#     ]) 
#
#
def is_dataclass_instance(obj: typing.Any) -> bool:
    return is_config_dataclass(obj) and not isinstance(obj, type)

# T = TypeVar('T')
# TODO: typing with args and kwargs
# def config_dataclass(fund: Any, *args: Any, **kwargs: Any) -> Callable[..., Callable[..., T]]:
#     @dataclass(*args, **kwargs) 
#     def inner(*args_d, **kwargs_d):
#         func(*args_d, **kwargs_d)
#
#         # return inner
#     return wrapper
#
