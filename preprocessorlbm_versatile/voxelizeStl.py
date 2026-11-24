import multiprocessing
import time
from collections.abc import Generator
from pathlib import Path

import numpy as np
import stl

import perimeter
from geometryTypes import Triangle
from slice import (
    calculate_scale_and_shift,
    scale_and_shift_mesh,
    swap_axis,
    to_intersecting_lines,
)
from util import remove_dups_from_point_list

_worker_mesh: list[Triangle] | None = None
_worker_domain: list[int] | None = None
_worker_is_shell = False


def _init_worker(
    mesh: list[Triangle],
    domain: list[int],
    is_shell: bool,
) -> None:
    """Keep inherited geometry in each worker instead of sending it per task."""
    global _worker_mesh, _worker_domain, _worker_is_shell  # noqa: PLW0603
    _worker_mesh = mesh
    _worker_domain = domain
    _worker_is_shell = is_shell


def _render_height(height: int) -> np.ndarray:
    """Render a slice using the geometry installed by the pool initializer."""
    if _worker_mesh is None or _worker_domain is None:
        raise RuntimeError("Voxelization worker has not been initialized")
    return render_slice(
        height,
        mesh=_worker_mesh,
        domain=_worker_domain,
        is_mesh_a_shell=_worker_is_shell,
    )


def voxelize(
    input_path: Path,
    target_elements: int,
    domain_data: tuple[
        list[float],
        list[float],
        list[int],
        list[list[float]],
    ]
    | None = None,
    rotation: int = -1,
    *,
    is_mesh_a_shell: bool = False,
) -> tuple[
    np.ndarray,
    tuple[
        list[float],
        list[float],
        list[list[float]],
    ],
]:
    """Rasterize an STL mesh into a zero-padded voxel domain.

    Parameters
    ----------
    input_path : Path
        STL file to load. Only its filename is used, so it must be accessible
        from the current working directory.
    target_elements : int
        Target resolution used to calculate the scale when domain_data is None.
    domain_data : tuple, optional
        Existing (scale, shift, domain, bounding_box) to use instead of
        calculating a new voxel coordinate system.
        Note: be carful with custom domain_data, as it may lead to difficulty
            indexing in the voxelized domain.
    rotation : int
        Swap x/y before slicing for 0, or y/z for 1; other values leave the
        slicing axes unchanged. The swaps are undone before returning.
    is_mesh_a_shell : bool
        Rasterize only the mesh boundary if True; otherwise fill slice interiors.

    Returns
    -------
    tuple
        An int8 occupancy array in (x, y, z) order and the metadata tuple
        (scale, shift, domain, bounding_box). Occupied voxels are 1.
        The metadata domain records the padded shape before the final axis
        swaps, rather than necessarily matching the returned array's shape.

    Notes
    -----
    Slices are processed by 16 workers using a local fork context. Geometry is
    inherited once per worker; only slice heights are sent as tasks. Interior
    filling assumes slice contours support outside-to-inside crossing parity;
    open contours are not automatically capped or repaired.

    """
    mesh = list(import_stl_file(input_path))

    if domain_data is None:
        scale, shift, domain, bounding_box = calculate_scale_and_shift(
            mesh,
            target_elements,
        )
    else:
        scale, shift, domain, bounding_box = domain_data

    # Shift all points to Voxel dimensions, [0, domain]
    mesh = list(scale_and_shift_mesh(mesh, scale, shift))

    # If it is a shell mesh, rotate here for different projections!
    if rotation == 0:
        mesh = list(swap_axis(mesh, 0, 1))
        domain = [domain[1], domain[0], domain[2]]
    elif rotation == 1:
        mesh = list(swap_axis(mesh, 1, 2))
        domain = [domain[0], domain[2], domain[1]]

    start = time.time()

    # Parallel
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(
        16,
        initializer=_init_worker,
        initargs=(mesh, domain, is_mesh_a_shell),
    ) as p:
        # Voxelize each layer in z-direction.
        vol = np.array(
            p.map(
                _render_height,
                range(int(domain[2])),
            ),
            dtype=np.int8,
        )

    end = time.time()
    print(f"Voxelization time: {end - start}")

    # If it is a shell mesh, rotate back here the different projections!
    if rotation == 0:
        vol = np.swapaxes(vol, 1, 2)
    elif rotation == 1:
        vol = np.swapaxes(vol, 0, 2)

    # At the very end here fix the [z][x][y] back to [x][y][z]
    vol = np.swapaxes(vol, 0, 2)
    vol = np.swapaxes(vol, 0, 1)

    return (vol, (scale, shift, bounding_box))


def render_slice(
    height: int,
    mesh: list[Triangle],
    domain: list[int],
    *,
    is_mesh_a_shell: bool = False,
) -> np.ndarray[tuple[int, int], np.dtype[np.bool]]:
    """Rasterize the mesh intersection with the z-plane at height.

    Mesh coordinates and height are in voxel units. Return an unpadded boolean
    array indexed as (x, y), with shape (domain[0], domain[1]). Boundary pixels
    are True; interiors are also filled unless is_mesh_a_shell is True.
    """
    lines = to_intersecting_lines(mesh, height)
    prepixel = np.zeros((domain[0], domain[1]), dtype=np.bool)
    perimeter.lines_to_voxels(lines, prepixel, is_shell=is_mesh_a_shell)
    return prepixel


def import_stl_file(
    input_path: Path,
) -> Generator[Triangle]:
    """Load an STL file and return an iterator over its valid triangle vertices.

    Faces with duplicate vertices are excluded by get_stl_faces.
    """
    imported_mesh = stl.mesh.Mesh.from_file(str(input_path))
    return get_stl_faces(imported_mesh)


def get_stl_faces(
    mesh: stl.mesh.Mesh,
) -> Generator[Triangle]:
    """Yield each mesh face as a tuple of three vertex coordinate tuples.

    Skip faces whose vertices are not distinct according to
    remove_dups_from_point_list; collinearity is not checked.
    """
    for i, j, k in zip(mesh.v0, mesh.v1, mesh.v2, strict=True):
        v1, v2, v3 = tuple(i), tuple(j), tuple(k)
        corners = 3
        if len(remove_dups_from_point_list([v1, v2, v3])) == corners:
            yield (v1, v2, v3)
        else:
            pass


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage:", sys.argv[0], "input.nrrd output.nrrd targetElementNum")
        sys.exit(-1)

    from nrrd import write

    output_volume, domain_data = voxelize(sys.argv[1], int(sys.argv[3]))

    write(sys.argv[2], output_volume)
