import numpy as np

from geometryTypes import Vector


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
    return tuple(set(pt_list))


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

