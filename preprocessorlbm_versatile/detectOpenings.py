import sys
import time
from collections.abc import Generator
from itertools import product
from typing import Literal

import numpy as np

from constants import VoxelType


def has_neighboring_unused_voxel(
    x: int | np.integer,
    y: int | np.integer,
    z: int | np.integer,
    data: np.ndarray,
) -> bool:
    return bool(
        data[z - 1][x][y] == VoxelType.UNUSED_VOXEL
        or data[z + 1][x][y] == VoxelType.UNUSED_VOXEL
        or data[z][x - 1][y] == VoxelType.UNUSED_VOXEL
        or data[z][x + 1][y] == VoxelType.UNUSED_VOXEL
        or data[z][x][y - 1] == VoxelType.UNUSED_VOXEL
        or data[z][x][y + 1] == VoxelType.UNUSED_VOXEL
    )


def get_all_inlet_outlet_fluid_voxels(
    walls: zip,
    data: np.ndarray,
) -> Generator[tuple[int, int, int]]:
    for z, x, y in walls:
        if data[z - 1][x][y] == VoxelType.FLUID_VOXEL:
            if has_neighboring_unused_voxel(x, y, z - 1, data):
                yield (z - 1, x, y)
        elif data[z + 1][x][y] == VoxelType.FLUID_VOXEL:
            if has_neighboring_unused_voxel(x, y, z + 1, data):
                yield (z + 1, x, y)
        elif data[z][x - 1][y] == VoxelType.FLUID_VOXEL:
            if has_neighboring_unused_voxel(x - 1, y, z, data):
                yield (z, x - 1, y)
        elif data[z][x + 1][y] == VoxelType.FLUID_VOXEL:
            if has_neighboring_unused_voxel(x + 1, y, z, data):
                yield (z, x + 1, y)
        elif data[z][x][y - 1] == VoxelType.FLUID_VOXEL:
            if has_neighboring_unused_voxel(x, y - 1, z, data):
                yield (z, x, y - 1)
        elif data[z][x][y + 1] == VoxelType.FLUID_VOXEL:
            if has_neighboring_unused_voxel(x, y + 1, z, data):
                yield (z, x, y + 1)


def get_neighbouring_unused_voxel_plane(
    x: int | np.integer,
    y: int | np.integer,
    z: int | np.integer,
    data: np.ndarray,
) -> Literal["x", "y", "z"] | None:
    if (
        data[z - 1][x][y] == VoxelType.UNUSED_VOXEL
        or data[z + 1][x][y] == VoxelType.UNUSED_VOXEL
    ):
        return "z"
    if (
        data[z][x - 1][y] == VoxelType.UNUSED_VOXEL
        or data[z][x + 1][y] == VoxelType.UNUSED_VOXEL
    ):
        return "x"
    if (
        data[z][x][y - 1] == VoxelType.UNUSED_VOXEL
        or data[z][x][y + 1] == VoxelType.UNUSED_VOXEL
    ):
        return "y"
    return None


def find_inlet_outlet(
    x: int,
    y: int,
    z: int,
    data: np.ndarray,
    plane: Literal["x", "y", "z"] | None,
) -> list[tuple[int, int, int]] | None:
    """Create a list of voxels (x, y, z) that make up the inlet/outlet for a voxel."""
    inlet_outlet = recur_find_inlet_outlet(x, y, z, [], data, plane)

    if len(inlet_outlet) > 1:
        print(" -> Found opening of size:", len(inlet_outlet))
        return inlet_outlet

    return None


def show_progress(progress: int, total: int) -> None:
    """Manual tqdm?."""
    sys.stdout.flush()
    sys.stdout.write(
        "\r[{}] {:.2f}%".format(
            "#" * int((progress * 10) / total),
            (progress * 100.0) / total,
        ),
    )
    sys.stdout.flush()


def voxel_is_not_yet_processed(
    x: int | np.integer,
    y: int | np.integer,
    z: int | np.integer,
    data: np.ndarray,
) -> bool:
    return data[z, x, y] != VoxelType.INVALID_VOXEL


def recur_find_inlet_outlet(
    x: int,
    y: int,
    z: int,
    result: list[tuple[int, int, int]],
    data: np.ndarray,
    plane: Literal["x", "y", "z"] | None,
) -> list[tuple[int, int, int]]:
    """Find the cells on a slice along a given plane which are inlet or outlet."""
    result.append((x, y, z))
    data[z, x, y] = VoxelType.INVALID_VOXEL

    # Only traverse parallel to plane
    dz_list = [0] if plane == "z" else [-1, 0, 1]
    dx_list = [0] if plane == "x" else [-1, 0, 1]
    dy_list = [0] if plane == "y" else [-1, 0, 1]

    for dz, dx, dy in product(dz_list, dx_list, dy_list):
        if (dx, dy, dz) == (0, 0, 0):
            continue
        x_n = x + dx
        y_n = y + dy
        z_n = z + dz
        if (
            data[z_n][x_n][y_n] == VoxelType.FLUID_VOXEL
            and has_neighboring_unused_voxel(x_n, y_n, z_n, data)
        ):
            result = recur_find_inlet_outlet(
                x_n,
                y_n,
                z_n,
                result,
                data,
                plane,
            )
    return result


def detect_inlets_outlets(
    data: np.ndarray,
) -> tuple[
    list[VoxelType],
    list[np.ndarray],
    np.ndarray,
]:
    """Detect all inlets and outlets of the vessel model.

    Assumes the following:
    - The vessel has only one inlet.
    - All outlets are smaller in diameter than the inlets.
    - The inlets and outlets are cut parallel to the x, y or z plane.
    - The openings are located on the boundaries
    """
    print("Detecting all fluid voxels surrounded by an unused voxel...")

    start = time.time()

    ############################ Method 1: Connected component analysis (very fast) ############################
    # Note: Only works if all openings lying on the boundary surfces
    # Drawbacks: Problems when detecting edge openings

    # boundaries = []
    # # Extract the boundary 2d matrix
    # # Because we know the openings can only locate on the boundaries
    # # Note data is (z,x,y), but inlet_outlet should be (x,y,z)
    # boundaries.append(data[0,:,:])
    # boundaries.append(data[-1,:,:])
    # boundaries.append(data[:,0,:])
    # boundaries.append(data[:,-1,:])
    # boundaries.append(data[:,:,0])
    # boundaries.append(data[:,:,-1])
    # # Validation
    # print(len(boundaries[0]), len(boundaries[2]), len(boundaries[4]))

    # # Optmized Connected-component labeling
    # inlets_outlets = []
    # from scipy.ndimage import label

    # for i, boundary in enumerate(boundaries):
    #     labeled_array, num_features = label(boundary)
    #     print(boundary.shape, num_features)
    #     for j in range(1, num_features+1):
    #         # A 2xN indexing array, first row is x indices, second row is y indices
    #         inlet_outlet = np.where(labeled_array == j)
    #         if i == 0:
    #             inlet_outlet = np.vstack((inlet_outlet, np.repeat(0, inlet_outlet[0].shape))) # (x,y) -> (x,y,z)
    #         elif i == 1:
    #             inlet_outlet = np.vstack((inlet_outlet, np.repeat(data.shape[0]-1, inlet_outlet[0].shape))) # (x,y) -> (x,y,z)
    #         elif i == 2:
    #             inlet_outlet = np.vstack((np.repeat(0, inlet_outlet[0].shape), inlet_outlet[1:], inlet_outlet[:1])) # (z,y) -> (x,y,z)
    #         elif i == 3:
    #             inlet_outlet = np.vstack((np.repeat(data.shape[1]-1, inlet_outlet[0].shape), inlet_outlet[1:], inlet_outlet[:1])) # (z,y) -> (x,y,z)
    #         elif i == 4:
    #             inlet_outlet = np.vstack((inlet_outlet[1:], np.repeat(0, inlet_outlet[0].shape), inlet_outlet[:1])) # (z,x) -> (x,y,z)
    #         else:
    #             inlet_outlet = np.vstack((inlet_outlet[1:], np.repeat(data.shape[2]-1, inlet_outlet[0].shape), inlet_outlet[:1])) # (z,x) -> (x,y,z)

    #         inlets_outlets.append(np.transpose(inlet_outlet))

    ############# Method 2: Iterate through all surface voxels (slow) ##################
    # Note: Only work if all openings are parallel to normal planes.
    # Drawbacks: Very slow, large memory consumption

    wall_voxels = zip(*np.where(data == VoxelType.WALL_VOXEL), strict=True)
    found_fluid_voxels = get_all_inlet_outlet_fluid_voxels(wall_voxels, data)

    inlets_outlets = []
    for z, x, y in found_fluid_voxels:
        if voxel_is_not_yet_processed(x, y, z, data):
            plane = get_neighbouring_unused_voxel_plane(x, y, z, data)
            inlet_outlet = find_inlet_outlet(x, y, z, data, plane)
            if inlet_outlet is not None:
                inlets_outlets.append(inlet_outlet)

    end = time.time()
    print(f"Find opening time: {end - start} sec")

    print(len(inlets_outlets))

    return paint_inlets_outlets(inlets_outlets, data)


def paint_inlets_outlets(
    inlets_outlets: list[list[tuple[int, int, int]]],
    voxel_volume: np.ndarray,
) -> tuple[
    list[VoxelType],
    list[np.ndarray],
    np.ndarray,
]:
    """Paint the inlets and outlets with their voxeltype.

    Uses the hardcoded ordering in the total surface of the inlets
    and outlets to paint the types in a copy of the voxel volume.

    Hardcoded inlets and outlets
    outlet 0/1: RPA side branches
    inlet 2: LHV
    inlet 3: MHV
    inlet 4: RHV
    outlet 5: LPA
    inlet 6: SVC
    inlet 7: IVC
    outlet 8: RPA

    Returns
    -------
    List of voxeltypes in same ordering as in upcoming returns.
    List of center coordinates of the inlets and outlets.
    Painted voxel volume.

    """
    opening_id = []  # Label identifying this opening
    opening_centers = []
    # openingQ = [] # Volume ratio assigned to this opening based on area (TODO: angle or R needed for this one)

    painted_voxels = np.copy(voxel_volume)

    """ Label the openings based on their area size """
    areas = np.array([len(x) for x in inlets_outlets])
    # Sort the inlets_outlets based on their area size
    sorted_borders = [
        x for _, x in sorted(zip(list(areas), inlets_outlets, strict=True))
    ]

    # Only uncomment when using Method 1: Connected component analysis.
    # # The rationale is, using connected component analysis, the algorithm will detect two clusters
    # # for the opening at the domain edge, so we need to remove it.
    # # Note: flawed, use carefully
    # inlets_outlets.pop(0)

    paint_dic = {
        6: VoxelType.INLET_SVC,
        7: VoxelType.INLET_IVC,
        4: VoxelType.INLET_RHV,
        3: VoxelType.INLET_MHV,
        2: VoxelType.INLET_LHV,
        5: VoxelType.OUTLET_LPA,
        8: VoxelType.OUTLET_RPA,
        0: VoxelType.OUTLET_SIDE_P,
        1: VoxelType.OUTLET_SIDE_V,
    }

    if len(sorted_borders) > len(paint_dic):
        e = "Found more open border than defined."
        raise ValueError(e)

    for i, opening in enumerate(sorted_borders):
        # Find the corresponding paint id based on surface ordering.
        paint_id = paint_dic[i]
        opening_id.append(paint_id)

        opening_center = np.zeros(3)
        for x, y, z in opening:
            painted_voxels[z][x][y] = paint_id
            opening_center += np.array((z, x, y))

        opening_centers.append(opening_center / len(opening))

    return (opening_id, opening_centers, painted_voxels)


def detect_openings(
    input_array: np.ndarray,
) -> tuple[
    list[VoxelType],
    list[np.ndarray],
    np.ndarray,
]:
    sys.setrecursionlimit(10000000)

    # Append surrounding layer to avoid boundary checking (THIS SHOULD NOT
    # BE NECESSARY! -> FLUID ON THE EDGE OF THE DOMAIN!) Note that if you use
    # Method 1 to detect opening voxels, you can not append surrounding layers,
    # just comment the following line out.
    data = np.pad(input_array, 1, "constant", constant_values=(VoxelType.UNUSED_VOXEL,))

    # NOTE: This code was uncommented, likely for method 1.
    # data = input_array

    # Detect openings
    opening_ids, opening_center, result = detect_inlets_outlets(data)

    # Take into account the padding added and removed
    for center in opening_center:
        center[:] = center - 1

    # Return result without outer layer (For Method 2)
    return (
        opening_ids,
        opening_center,
        result[1:-1, 1:-1, 1:-1].astype("int8", copy=False),
    )
    # (For Method 1)
    # return (opening_ids, openingCenter, inlets_outlets, result.astype('int8', copy=False) )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:", sys.argv[0], "input.nrrd output.nrrd")
        sys.exit(-1)

    import time

    import nrrd

    start_time = time.time()
    data, data_header = nrrd.read(sys.argv[1])

    # TODO: This does not match the function description.
    opening_descr, result = detect_openings(data)

    # Write result without the surrounding layer
    nrrd.write(sys.argv[2], result)

    end_time = time.time()
    time_elapsed = round((end_time - start_time) * 1000)
    print("Elapsed time:", time_elapsed, "[ms]")
