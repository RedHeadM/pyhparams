
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import tempfile
import pyhparams
from tempfile import TemporaryDirectory

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


