import pygame


def fitRatio(parent_shape: tuple[int, ...], fit_shape: tuple[int, ...]) -> float:
    """
    Get the ratio to fit the board to the window its allocated.
    """
    return min(p / f for p, f in zip(parent_shape, fit_shape))


def centerCoord(coord: tuple[int, ...], allocated_shape: tuple[int, ...], fit_shape: tuple[int, ...]) -> tuple[int, ...]:
    """
    Get the coordinate to center the board in the window.
    """
    return tuple(((p - f) // 2) + c for p, f, c in zip(allocated_shape, fit_shape, coord))


def mouseIn(coord: tuple[int, ...], size: tuple[int, ...]) -> bool:
    """
    Check if the mouse is in the given rectangle.
    :param coord: - the top left corner of the rectangle
    :param size:  - the size of the rectangle
    :return:    - True if the mouse is in the rectangle
    """
    x, y = pygame.mouse.get_pos()
    min_x, min_y = coord
    max_x, max_y = tuple(c + s for c, s in zip(coord, size))
    return min_x <= x <= max_x and min_y <= y <= max_y
