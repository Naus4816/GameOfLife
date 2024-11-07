import pygame
from pathlib import Path


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


def cropText(text: str, font: pygame.font.Font, width: int) -> str:
    """
    Crop the text to fit the width.
    """
    if font.size(text)[0] <= width:
        return text
    while font.size(text + '...')[0] > width:
        new_text = text.rsplit(' ', 1)[0]
        if new_text == text:
            break
        text = new_text
    else:
        return text + '...'
    while font.size(text + '...')[0] > width:
        if len(text) == 0:
            return '...'
        text = text[:-1]
    return text + '...'


def scaledImage(child_size: tuple[int, int],
                bg_folder: Path, bg_color: tuple[int, int, int],
                bg_margin: int = 2, margin: int = 6) -> pygame.Surface:
    """
    Creates a scaled background image.
    """
    element_names = ('top_left', 'top_right', 'bottom_left', 'bottom_right', 'top', 'bottom', 'left', 'right')
    elements = [pygame.image.load(bg_folder / f'{name}.png') for name in element_names]
    width, height = tuple(c + (margin * 2) for c in child_size)
    thick = elements[0].get_width()
    image = pygame.surface.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(image, bg_color, (bg_margin, bg_margin, width - bg_margin * 2, height - bg_margin * 2))
    image.blit(elements[0], (0, 0))
    image.blit(elements[1], (width - thick, 0))
    image.blit(elements[2], (0, height - thick))
    image.blit(elements[3], (width - thick, height - thick))
    image.blit(pygame.transform.scale(elements[4], (width - thick * 2, thick)),(thick, 0))
    image.blit(pygame.transform.scale(elements[5], (width - thick * 2, thick)),(thick, height - thick))
    image.blit(pygame.transform.scale(elements[6], (thick, height - thick * 2)),(0, thick))
    image.blit(pygame.transform.scale(elements[7], (thick, height - thick * 2)),(width - thick, thick))
    return image


def scaledTab(child_size: tuple[int, int],
              bg_folder: Path, bg_color: tuple[int, int, int],
              bg_margin: int = 2, margin: int = 6) -> pygame.Surface:
    """
    Creates a scaled tab background image.
    """
    element_names = ('top_left', 'top_right', 'bottom_left', 'bottom_right', 'top', 'left', 'right')
    elements = [pygame.image.load(bg_folder / f'{name}.png') for name in element_names]
    width, height = tuple(c + (margin * 2) for c in child_size)
    thick = elements[0].get_width()
    image = pygame.surface.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(image, bg_color, (bg_margin, bg_margin, width - bg_margin * 2, height - bg_margin))
    image.blit(elements[0], (0, 0))
    image.blit(elements[1], (width - thick, 0))
    image.blit(elements[2], (0, height - thick))
    image.blit(elements[3], (width - thick, height - thick))
    image.blit(pygame.transform.scale(elements[4], (width - thick * 2, thick)), (thick, 0))
    image.blit(pygame.transform.scale(elements[5], (thick, height - thick * 2)), (0, thick))
    image.blit(pygame.transform.scale(elements[6], (thick, height - thick * 2)), (width - thick, thick))
    return image
