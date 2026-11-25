from enum import IntEnum


class VoxelType(IntEnum):
    """Per voxel class identifier."""

    UNUSED_VOXEL = 0
    WALL_VOXEL = 1
    FLUID_VOXEL = 2
    INLET_SVC = 10
    INLET_IVC = 11
    INLET_RHV = 12
    INLET_MHV = 13
    INLET_LHV = 14
    OUTLET_RPA = 15
    OUTLET_LPA = 16
    OUTLET_SIDE_V = 17
    OUTLET_SIDE_P = 18
    INVALID_VOXEL = 19
