from dataclasses import dataclass


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
class WithNested:
    """test data class for testing mgerges"""
    nested: TestParamsStr

@dataclass
class NesttedTwoLevel:
    """test data class for testing mgerges"""
    nested2: WithNested
