from dataclasses import dataclass,field
from typing import Dict


@dataclass
class UtilsTestParams:
    """test data class for testing merges"""

    x: int = 0
    y: int = 1

@dataclass
class UtilsTestParams2:
    """test data class for testing merges"""

    z: int = 0
    y: int = 1

@dataclass
class TestParamsStr:
    """test data class for testing mgerges"""
    value1: str = "not_set"
    value2: str = "not_set2"

@dataclass
class TestParamsDictStr:
    """test data class for testing mgerges"""
    value: Dict[str,str] = field(default_factory=lambda:{"val":"not_changed"})

@dataclass
class WithNested:
    """test data class for testing mgerges"""
    nested: TestParamsStr
    value_not_nested: str ="not_nested_default"

@dataclass
class NesttedTwoLevel:
    """test data class for testing mgerges"""
    nested2: WithNested
