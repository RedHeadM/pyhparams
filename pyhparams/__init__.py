__version__=  '0.0.0dev'

from .data_class import config_dataclass
# private name for _PARAM_SUBSTITUTE from same user import -> ast same
from .data_class import _PARAM_SUBSTITUTE as  PARAM_SUBSTITUTE
from .config import Config
from .utils import *
from .ast_data_fields_resolve import RESOLVE

__all__ =  ["RESOLVE", "Config","utils"]
