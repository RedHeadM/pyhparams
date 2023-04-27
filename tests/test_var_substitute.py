
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import tempfile
# from pyhparams.data_class import PARAM_SUBSTITUTE
#
# # TODO: move to func
# @contextmanager
# def config_file(content : str, suffix :str = ".py") -> Iterator[Path]:
#     with tempfile.NamedTemporaryFile(mode="w+", suffix=suffix) as tmp_file:
#         print(content, file=tmp_file, end='') 
#         tmp_file.flush()
#         yield Path(str(tmp_file.name))


# def test_tmp_conf_one_multi_line():
#     base_conf = r'''
#     from pyhparams.data_class import PARAM_SUBSTITUTE
#     bar = 1
#     '''
#     with config_file(base_conf) as f_base:
#         contetn_child = f'''
#         import pyhparams
#         _base_ = {f_base}
#         bar = data_class.PARAM_SUBSTITUTE
#         foo = bar
#         '''
#         with config_file(contetn_child) as f_child:
#             conf = Config.create_from_file(f_child)

# def test_load_int():
