__version__=  '0.0.0dev'

from .data_class import config_dataclass
# private name for _PARAM_SUBSTITUTE from same user import -> ast same
from .data_class import _PARAM_SUBSTITUTE as  PARAM_SUBSTITUTE
from .config import Config

__all__ =  ["config_dataclass", "Config","PARAM_SUBSTITUTE"]
