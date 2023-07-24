import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import tempfile
import warnings
import pyhparams
from tempfile import TemporaryDirectory
import ast

from pyhparams.ast import ast_to_dict

@contextmanager
def config_file(content : str, suffix :str = ".py") -> Iterator[Path]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=suffix) as tmp_file:
        print(content, file=tmp_file, end='') 
        tmp_file.flush()
        yield Path(str(tmp_file.name))

def test_tmp_conf_one_line():
    contet_in = r"bar"
    with config_file(contet_in) as f:
        assert  contet_in == f.read_text()


def test_create_from_file_single_var():
    contet_in = r"foo=0"
    with config_file(contet_in) as f:
        conf,_ = pyhparams.Config.create_from_file(str(f)) 
        assert conf.foo == 0

def test_tmp_conf_one_multi_line():
    contetn_in = r'''
bar = "val1"
foo = 2
    '''
    with config_file(contetn_in) as f:
        conf,_ = pyhparams.Config.create_from_file(str(f)) 
        assert conf.foo == 2
        assert conf.bar == "val1"

def test_tmp_conf_merge_with_base():
    conf_base = r'''
will_be_changed_by_target = "val1"
not_touched_by_target = 2
    '''
    with config_file(conf_base) as f_base:
        conf_target = f'''
_base_ = "{f_base}" 
will_be_changed_by_target = "val2"
added_by_target = 10
    '''
        with config_file(conf_target) as f_target:
            conf,_ = pyhparams.Config.create_from_file(str(f_target)) 
            assert conf.not_touched_by_target == 2
            assert conf.will_be_changed_by_target == "val2"
            assert conf.added_by_target == 10

def test_tmp_conf_merge_with_multi_base():
    conf_base1 = r'''
will_be_changed_by_target = "bbase1"
not_touched_by_target_or_base2 = 1
    '''
    conf_base2 = r'''
will_be_changed_by_target = "bbase2"
will_be_changed_by_base1 = "base2"
not_touched_by_target_or_base1 = 2
    '''
    with config_file(conf_base1) as f_base1, config_file(conf_base2) as f_base2:
        conf_target = f'''
_base_ = ["{f_base1}","{f_base2}"]
will_be_changed_by_target = "target1"
added_by_target = "target2"
    '''
        with config_file(conf_target) as f_target:
            conf,_ = pyhparams.Config.create_from_file(str(f_target)) 
            assert conf.will_be_changed_by_target == "target1"
            assert conf.not_touched_by_target_or_base2 == 1
            assert conf.not_touched_by_target_or_base1 == 2
            assert conf.added_by_target == "target2"

def test_tmp_conf_merge_with_resolve():
    conf_base = r'''
from pyhparams.utils import UtilsTestParams
a = UtilsTestParams(x=10,y=100)
    '''
    with config_file(conf_base) as f_base:
        conf_target = f'''
_base_ = "{f_base}" 
from pyhparams.utils import UtilsTestParams2
from pyhparams import RESOLVE
b = UtilsTestParams2(z= RESOLVE(UtilsTestParams.x))
    '''
        with config_file(conf_target) as f_target:
            conf,_ = pyhparams.Config.create_from_file(str(f_target)) 
            assert conf.a.x == 10
            assert conf.a.y == 100
            assert conf.b.z == 10


def test_tmp_conf_with_save_file_es():
    contetn_in = r'''
bar = "val1"
foo = 2
    '''
    with config_file(contetn_in) as f, TemporaryDirectory() as dir:
        conf, file_exe = pyhparams.Config.create_from_file(str(f), Path(dir) /"test_conf.py") 
        assert file_exe.exists()
        assert conf.foo == 2
        assert conf.bar == "val1"
        # uparse saved again and check if save
        conf2, out_f2 = pyhparams.Config.create_from_file(file_exe) 
        assert out_f2 is None

        assert conf2.foo == 2
        assert conf2.bar == "val1"



def test_tmp_conf_merge_with_base_var_name():
    conf_base = r'''
will_be_changed_by_target = "val1"
not_touched_by_target = 2
    '''
    with TemporaryDirectory() as dir:
        base_file_name= "base_file.py"
        base_file_dir_var_name = "$CONF_DIR"
        conf_target = f'''
_base_ = "{base_file_dir_var_name}/{base_file_name}" 
will_be_changed_by_target = "val2"
added_by_target = 10
    '''
        base_path_name = Path(str(dir)) / base_file_name
        base_path_name.write_text(conf_base)

        with config_file(conf_target) as f_target:
            base_path_vars={base_file_dir_var_name:str(dir)}
            conf,_ = pyhparams.Config.create_from_file(str(f_target), 
                                                       base_path_vars=base_path_vars) 
            assert conf.not_touched_by_target == 2
            assert conf.will_be_changed_by_target == "val2"
            assert conf.added_by_target == 10

def test_tmp_conf_check_if_base_key_is_removed():
    if sys.version_info < (3, 9):
        warnings.warn("test not run for python version test_name=\
                test_tmp_conf_check_if_base_key_is_removed")
        return

    conf_base = r'''
base="base_value"
    '''
    with config_file(conf_base) as f_base:
        conf_target = f'''
_base_ = "{f_base}" 
target="target_value"
    '''
        with config_file(conf_target) as f_target, TemporaryDirectory() as dir:
            out_put_file = Path(str(dir))/"outputfile.py"
            conf, out_put_file = pyhparams.Config.create_from_file(str(f_target),
                                                       merged_output_file=out_put_file,) 
            assert conf.base == "base_value"
            assert conf.target == "target_value"
            assert not hasattr(conf, pyhparams.config.BASE_KEY_ID)
            ast_merded_file = ast_to_dict(ast.parse(out_put_file.read_text()))
            assert ast_merded_file.get("base") ==  "base_value"
            assert ast_merded_file.get("target") ==  "target_value"
            assert ast_merded_file.get(pyhparams.config.BASE_KEY_ID) is None
