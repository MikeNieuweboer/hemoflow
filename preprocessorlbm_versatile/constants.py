from collections.abc import Callable
from typing import NoReturn, TypeVar

ConstantT = TypeVar("ConstantT")


def constant(f: Callable[[], ConstantT]) -> property:
    def fset(self: object, value: ConstantT) -> NoReturn:
        raise TypeError
    def fget(self: object) -> ConstantT:
        return f()
    return property(fget, fset)

class const(object):
    @constant
    def UNUSED_VOXEL() -> int:
        return 0
    @constant
    def WALL_VOXEL() -> int:
        return 1
    @constant
    def FLUID_VOXEL() -> int:
        return 2
    @constant
    def INLET_SVC() -> int:
        return 10
    @constant
    def INLET_IVC() -> int:
        return 11
    @constant
    def INLET_RHV() -> int:
        return 12
    @constant
    def INLET_MHV() -> int:
        return 13
    @constant
    def INLET_LHV() -> int:
        return 14
    @constant
    def OUTLET_RPA() -> int:
        return 15
    @constant
    def OUTLET_LPA() -> int:
        return 16
    @constant
    def OUTLET_SIDE_V() -> int:
        return 17
    @constant
    def OUTLET_SIDE_P() -> int:
        return 18
