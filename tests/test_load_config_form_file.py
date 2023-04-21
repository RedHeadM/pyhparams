
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import tempfile
import pyhparams

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

def test_tmp_conf_one_multi_line():
    contetn_in = r'''
    bar = klsjd
    foo =2
    '''
    with config_file(contetn_in) as f:
        assert  contetn_in == f.read_text()

def test_create_from_file_single_var():
    contet_in = r"foo=0"
    with config_file(contet_in) as f:
        conf = pyhparams.Config.create_from_file(str(f)) 
        assert conf.foo == 0

# def test_load_int():
