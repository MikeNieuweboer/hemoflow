from geometryTypes import Vector
import numpy as np


def manhattan_distance(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    d: int = 2,
) -> float:
    assert len(p1) == len(p2)
    all_distances = 0
    for i in range(d):
        all_distances += abs(p1[i] - p2[i])
    return all_distances


def remove_dups_from_point_list(
    pt_list: list[Vector],
) -> tuple[Vector, ...]:
    new_list = pt_list[:]
    return tuple(set(new_list))


def array_to_white_greyscale_pixel(
    array: np.ndarray, pixels: np.ndarray,
) -> None:
    """Create a black and white (0/255) representation of array in pixels."""
    for i in range(array.shape[0]):
        for j in range(array.shape[1]):
            if array[i, j]:
                pixels[i, j] = 255
            else:
                pixels[i, j] = 0


def pad_voxel_array(voxels: np.ndarray) -> np.ndarray:
    """Add a padding layer around each edge of the domain.

    Parameters
    ----------
    voxels: np.ndarray
        A 3-Dimensional numpy array.

    Returns
    -------
    A copy of voxels of size (x_shape + 2, y_shape + 2, z_shape + 2)

    """
    shape = voxels.shape
    new_shape = (shape[0] + 2, shape[1] + 2, shape[2] + 2)
    vol = np.zeros(new_shape, dtype=np.int8)

    vol[1:-1, 1:-1, 1:-1] = voxels

    return vol
