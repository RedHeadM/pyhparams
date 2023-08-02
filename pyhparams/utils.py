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
