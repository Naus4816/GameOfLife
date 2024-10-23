
def fitRatio(parent_shape: tuple[int, ...], fit_shape: tuple[int, ...]) -> float:
    """
    Get the ratio to fit the board to the window its allocated.
    """
    print(parent_shape, fit_shape, min(p / f for p, f in zip(parent_shape, fit_shape)))
    return min(p / f for p, f in zip(parent_shape, fit_shape))


def centerCoord(coord: tuple[int, ...], allocated_shape: tuple[int, ...], fit_shape: tuple[int, ...]) -> tuple[int, ...]:
    """
    Get the coordinate to center the board in the window.
    """
    print(coord, allocated_shape, fit_shape, (allocated_shape[0] - fit_shape[0]) // 2, (allocated_shape[1] - fit_shape[1]) // 2)
    return tuple(((p - f) // 2) + c for p, f, c in zip(allocated_shape, fit_shape, coord))
