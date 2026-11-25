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
    x_shape, y_shape = pixels.shape
    for x in range(x_shape):
        is_black = False
        # Get all lines which could have this x coordinate.
        lines = find_relevant_lines(line_list, x)
        # Get y of each boundary point.
        target_ys = [int(generate_y(line, x)) for line in lines]
        target_ys.sort()
        prev_y = 0
        for y in target_ys:
            if y >= y_shape:
                break
            if is_black and (not is_shell) and y > prev_y:
                pixels[x][prev_y + 1 : y] = True

            is_black = not is_black
            if y < 0:
                continue
            pixels[x][y] = True
            prev_y = y
        if is_black and (not is_shell):
            pixels[x][prev_y + 1 : y_shape] = True


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
    return (
        int(max(line[0][0], line[1][0])) >= x
        and int(min(line[0][0], line[1][0])) <= x
        and int(max(line[0][1], line[1][1])) >= y
        and int(min(line[0][1], line[1][1])) <= y
    )
