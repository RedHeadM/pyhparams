# from dataclasses import dataclass, is_dataclass, Field, MISSING
import dataclasses
from typing import Any, Union, Callable, Optional, TypeVar
import functools 
import pathlib
import os

config_dataclass = functools.partial(dataclasses.dataclass, kw_only =True)
is_config_dataclass = dataclasses.is_dataclass
ConfigField = dataclasses.Field

Num = Union[int, float]

''' A sentinel value signifying a missing default '''
PARAM_MISSING = dataclasses.MISSING
''' indicate to substitute '''
PARAM_SUBSTITUTE = dataclasses.MISSING


# TODO: not nedded can be be just with os pat
class ENV_VAR:
    ''' indicate can envoit varialbe '''
    def __init__(self,name : str):
        self.name = name

    def __div__(self, val: str):
        ''' join path '''
        return os.path.join(str(self.name), val)



# @config_dataclass
# class ParmsTrainer:
#     my_path: str  = ENV_VAR('HOME') /

def is_dataclass_instance(obj: Any) -> bool:
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
