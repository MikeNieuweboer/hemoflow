from collections.abc import Generator

from geometryTypes import Line, Triangle, Vector


def to_intersecting_lines(
    mesh: list[Triangle],
    height: float,
) -> list[tuple[Vector, Vector]]:
    relevant_triangles = list(filter(lambda tri: is_above_and_below(tri, height), mesh))
    not_tame_triangles = filter(
        lambda tri: not is_intersecting_triangle(tri, height),
        relevant_triangles,
    )
    return [triangle_to_intersecting_lines(tri, height) for tri in not_tame_triangles]


def linear_interpolation(
    p1: Vector,
    p2: Vector,
    distance: float,
) -> Vector:
    """
    :param p1: Point 1
    :param p2: Point 2
    :param distance: Between 0 and 1, Lower numbers return points closer to p1.
    :return: A point on the line between p1 and p2

    """
    slopex = p1[0] - p2[0]
    slopey = p1[1] - p2[1]
    slopez = p1[2] - p2[2]
    return (
        p1[0] - distance * slopex,
        p1[1] - distance * slopey,
        p1[2] - distance * slopez,
    )


def is_above_and_below(
    point_list: Triangle,
    height: float,
) -> bool:
    """:param pointList: Can be line or triangle
    :param height:
    :return: true if any line from the triangle crosses or is on the height line,
    """
    above = list(filter(lambda pt: pt[2] > height, point_list))
    below = list(filter(lambda pt: pt[2] < height, point_list))
    same = list(filter(lambda pt: pt[2] == height, point_list))
    return bool(len(same) == 3 or len(same) == 2 or (above and below))


def is_intersecting_triangle(
    triangle: Triangle,
    height: float,
) -> bool:
    assert len(triangle) == 3
    same = list(filter(lambda pt: pt[2] == height, triangle))
    return len(same) == 3


def triangle_to_intersecting_lines(
    triangle: Triangle,
    height: float,
) -> Line:
    assert len(triangle) == 3

    above = list(filter(lambda pt: pt[2] > height, triangle))
    below = list(filter(lambda pt: pt[2] < height, triangle))
    same = list(filter(lambda pt: pt[2] == height, triangle))

    assert len(same) != 3

    if len(same) == 2:
        return same[0], same[1]
    if len(same) == 1:
        side1 = where_line_crosses_z(above[0], below[0], height)
        return side1, same[0]
    lines = []
    for a in above:
        for b in below:
            lines.append((b, a))
    # Project triangle to line on plane with z=height
    side1 = where_line_crosses_z(lines[0][0], lines[0][1], height)
    side2 = where_line_crosses_z(lines[1][0], lines[1][1], height)
    return side1, side2


def where_line_crosses_z(
    p1: Vector,
    p2: Vector,
    z: float,
) -> Vector:
    if p1[2] > p2[2]:
        t = p1
        p1 = p2
        p2 = t
    # now p1 is below p2 in z
    distance = 0 if p2[2] == p1[2] else (z - p1[2]) / (p2[2] - p1[2])
    return linear_interpolation(p1, p2, distance)


def calculate_scale_and_shift(
    mesh: list[Triangle],
    target_elements: int,
) -> tuple[list[float], list[float], list[int], list[list[float]]]:
    """Compute the mesh-to-voxel transform and unpadded domain dimensions.

    Parameters
    ----------
    mesh : list of triangles
        Triangle vertices in geometry coordinates. Must be nonempty and have
        a bounding box with positive extent along every axis.
    target_elements : int
        Positive target voxel count for the bounding box, not the vessel interior.
        Integer truncation makes the resulting count approximate.

    Returns
    -------
    scale : list of float
        Uniform scale factors, derived from the truncated x-domain size.
    shift : list of float
        Negated bounding-box minima. Transform points as
        ``voxel_point = (point + shift) * scale`` componentwise.
    domain : list of int
        Unpadded voxel counts in x, y, z order, obtained by truncating the
        bounding-box extents multiplied by the initial target-based scale.
    bounding_box : list of lists of float
        Minimum and maximum coordinates, ``[mins, maxs]``, in geometry units.

    """
    all_points = [item for sublist in mesh for item in sublist]
    mins = [0, 0, 0]
    maxs = [0, 0, 0]
    ds = [0, 0, 0]
    for i in range(3):
        mins[i] = min(all_points, key=lambda tri: tri[i])[i]
        maxs[i] = max(all_points, key=lambda tri: tri[i])[i]
        ds[i] = maxs[i] - mins[i]

    bounding_box = [mins, maxs]
    volume = ds[0] * ds[1] * ds[2]
    # Compute size of each voxel
    vox_scale = (target_elements / volume) ** (1.0 / 3)

    # The amount of voxels in each dimension.
    domain = [int(x) for x in [vox_scale * ds[0], vox_scale * ds[1], vox_scale * ds[2]]]

    # Shift to get most minimum of bounding box to origin.
    shift = [-minimum for minimum in mins]

    # Actual scale to exactly cover the x range with the voxels in domain.
    xyscale = domain[0] / ds[0]
    scale = [
        xyscale,
        xyscale,
        xyscale,
    ]

    return (scale, shift, domain, bounding_box)


def scale_and_shift_mesh(
    mesh: list[Triangle],
    scale: list[float],
    shift: list[float],
) -> Generator[Triangle]:
    for tri in mesh:
        new_tri = []
        for pt in tri:
            newpt = [0, 0, 0]
            for i in range(3):
                newpt[i] = (pt[i] + shift[i]) * scale[i]
            shifted_point: Vector = tuple(newpt)  # ty: ignore[invalid-assignment]
            new_tri.append(shifted_point)
        yield new_tri  # ty: ignore[invalid-yield]


def swap_axis_with_z(
    mesh: list[Triangle],
    axis: int,
) -> Generator[Triangle]:
    # axis = 0 -> swap x - z
    # axis = 1 -> swap y - z
    for tri in mesh:
        new_tri = []
        for pt in tri:
            newpt = [0, 0, 0]
            if axis == 0:
                newpt[0] = pt[2]
                newpt[1] = pt[1]
                newpt[2] = pt[0]
            elif axis == 1:
                newpt[0] = pt[0]
                newpt[1] = pt[2]
                newpt[2] = pt[1]
            else:
                newpt = pt
            new_tri.append(tuple(newpt))
        yield tuple(new_tri)  # ty: ignore[invalid-yield]


def swap_axis(
    mesh: list[Triangle],
    axis1: int,
    axis2: int,
) -> Generator[Triangle]:
    for tri in mesh:
        new_tri = []
        for pt in tri:
            newpt = [pt[0], pt[1], pt[2]]
            newpt[axis1] = pt[axis2]
            newpt[axis2] = pt[axis1]
            new_tri.append(tuple(newpt))
        yield tuple(new_tri)  # ty: ignore[invalid-yield]
