from pyhparams import config_dataclass 
from dataclasses import dataclass



def test_wrapper_int():
    val = 10
    @config_dataclass 
    class TestParams:
        value: int =  val+1
    assert TestParams(value = val).value == val

def test_wrapper_str():
    class TestParams2:
        value: int =  0

    assert str(TestParams2()) != ''
