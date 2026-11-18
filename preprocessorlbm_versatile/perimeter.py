from collections.abc import Generator

import numpy as np

from geometryTypes import Line


def lines_to_voxels(
    line_list: list[Line],
    pixels: np.ndarray,
    *,
    is_shell: bool,
) -> None:
    """Rasterize line segments into the 2D ``pixels[x, y]`` array in place.

    Set boundary pixels to True when ``is_shell`` is True; otherwise also
    fill interiors by toggling inside/outside at each scanline crossing.
    Coordinates are truncated with ``int()``, and existing True pixels are
    never cleared. Only the first two coordinates of each endpoint are used.
    """
    for x in range(len(pixels)):
        is_black = False
        # Get all lines which could have this x coordinate.
        lines = list(find_relevant_lines(line_list, x))
        # Get y of each boundary point.
        target_ys = [int(generate_y(line, x)) for line in lines]
        for y in range(len(pixels[x])):
            if is_black and (not is_shell):
                pixels[x][y] = True
            if y in target_ys:
                for line in lines:
                    if on_line(line, x, y):
                        is_black = not is_black
                        pixels[x][y] = True


def find_relevant_lines(
    line_list: list[Line],
    x: float,
    ind: int = 0,
) -> Generator[Line]:
    """Yield segments whose coordinate interval contains ``x`` along ``ind``.

    Include the lower endpoint and exclude the upper endpoint, i.e.
    ``min_coord <= x < max_coord``. Segments constant along the selected axis
    are excluded. The default axis is the endpoint x coordinate.
    """
    for line in line_list:
        same = False
        above = False
        below = False
        for pt in line:
            if pt[ind] > x:
                above = True
            elif pt[ind] == x:
                same = True
            else:
                below = True
        if (above and below) or (same and above):
            yield line


def generate_y(
    line: Line,
    x: float,
) -> float:
    """Return the y coordinate on the line at ``x``, or -1 for a vertical line.

    Use only endpoint x/y coordinates. Interpolation is not restricted to the
    segment bounds, so x values outside the segment extrapolate the line.
    """
    if line[1][0] == line[0][0]:
        return -1
    ratio = (x - line[0][0]) / (line[1][0] - line[0][0])
    ydist = line[1][1] - line[0][1]
    return line[0][1] + ratio * ydist


def on_line(
    line: Line,
    x: int,
    y: int,
) -> bool:
    """Test whether integer pixel ``(x, y)`` matches a segment's rasterization.

    Require y to equal ``int(generate_y(line, x))`` and check each coordinate
    against the segment bounds, allowing truncated endpoint coordinates.
    Only endpoint x/y coordinates are used; this is not an exact geometric
    point-on-segment test.
    """
    newy = generate_y(line, x)
    if int(newy) != y:
        return False
    if (
        int(line[0][0]) != x
        and int(line[1][0]) != x
        and (max(line[0][0], line[1][0]) < x or min(line[0][0], line[1][0]) > x)
    ):
        return False
    return not (
        int(line[0][1]) != y
        and int(line[1][1]) != y
        and (max(line[0][1], line[1][1]) < y or min(line[0][1], line[1][1]) > y)
    )
