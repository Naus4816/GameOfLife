import uuid
from uuid import UUID

import pygame
import math
from pathlib import Path
from render.Utils import fitRatio, centerCoord, mouseIn, cropText, scaledImage, scaledTab

ASSETS_PATH = Path(__file__).parent.parent / 'assets'
FONT_PATH: Path = ASSETS_PATH / 'font.ttf'


class Child:
    coord: tuple[int, ...]
    size: tuple[int, ...]
    parent: 'Container'
    can_interact: bool = False
    uuid: UUID

    def __init__(self, coord: tuple[int, ...], size: tuple[int, ...], parent: 'Container'):
        self.parent = parent
        self.size = tuple(math.floor(s * parent.ratio) for s in size)
        self.coord = tuple(math.floor(s * parent.ratio) + p for s, p in zip(coord, parent.coord))
        self.uuid = uuid.uuid4()

    def handleEvents(self):
        pass

    def render(self, screen: pygame.Surface):
        pass

    @property
    def rect(self) -> tuple:
        return *self.coord, *self.size

    def cleanup(self):
        self.parent.children.remove(self)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.uuid == other.uuid

    def __hash__(self):
        return hash(self.uuid)


class ScaledChild(Child):
    ratio: float
    content_size: tuple[int, ...]

    def __init__(self, coord: tuple[int, ...], size: tuple[int, ...],
                 content_size: tuple[int, ...], parent: 'Container'):
        self.ratio = fitRatio(size, content_size)
        self.content_size = content_size
        content_size = tuple(math.floor(s * self.ratio) for s in content_size)
        super().__init__(coord, content_size, parent)
        self.ratio *= parent.ratio
        self.coord = centerCoord(self.coord, tuple(math.floor(s * parent.ratio) for s in size), self.size)


class Container(ScaledChild):
    background: pygame.Surface
    children: list[Child]

    def __init__(self, coord: tuple[int, ...], size: tuple[int, ...] | None,
                 parent: 'Container', bg: Path | pygame.Surface):
        if isinstance(bg, Path):
            bg = pygame.image.load(str(bg))
        if size is None:  # consider a 1:1 background with its parent
            size = bg.get_size()
        super().__init__(coord, size, bg.get_size(), parent)
        self.background = pygame.transform.scale(bg, tuple(int(x * self.ratio) for x in bg.get_size()))
        self.children = []

    @staticmethod
    def fromScreen(screen: pygame.Surface, path: Path) -> 'Container':
        container: Container = Container.unit(screen.get_size())
        return Container(container.coord, container.size, container, path)

    @staticmethod
    def unit(size: tuple = (0, 0)) -> 'Container':
        container: Container = object.__new__(Container)
        container.__class__ = Container
        container.coord = (0, 0)
        container.size = size
        container.ratio = 1
        return container

    def handleEvents(self):
        for child in self.children[::-1]:
            child.handleEvents()

    def add(self, child):
        self.children.append(child)

    def render(self, screen: pygame.Surface):
        screen.blit(self.background, self.coord)
        for child in self.children:
            child.render(screen)

    def clear(self, type: type = None):
        if type is None:
            self.children.clear()
            return
        self.children = [c for c in self.children if not isinstance(c, type)]

    def get(self, type: type = None) -> list:
        if type is None:
            return self.children
        return [c for c in self.children if isinstance(c, type)]


class StaticTextRender(Child):
    text: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container',
                 text: str, color: tuple[int, int, int], font_size: int = 36, max_width: int = 0):
        font = pygame.font.Font(str(FONT_PATH), font_size)
        text = text if max_width == 0 else cropText(text, font, max_width)
        self.text = font.render(text, False, color)
        size = self.text.get_size()
        super().__init__(coord, size, parent)
        self.text = pygame.transform.scale(self.text, self.size)

    def render(self, screen: pygame.Surface):
        screen.blit(self.text, self.coord)


class BoldStaticTextRender(StaticTextRender):
    under_text: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container',
                 text: str, color: tuple[int, int, int], font_size: int = 36, max_width: int = 0):
        font = pygame.font.Font(str(FONT_PATH), font_size)
        text = text if max_width == 0 else cropText(text, font, max_width)
        super().__init__(coord, parent, text, color, font_size)
        self.under_text = font.render(text, False, (0, 0, 0))
        self.under_text = pygame.transform.scale(self.under_text, self.size)

    def render(self, screen: pygame.Surface):
        screen.blit(self.under_text, (self.coord[0] + 2, self.coord[1] + 2))
        super().render(screen)


class DynamicTextRender(Child):
    font: pygame.font.Font
    color: tuple[int, int, int]
    text_getter: callable
    max_width: int

    def __init__(self, coord: tuple[int, ...], parent: 'Container',
                 color: tuple[int, int, int], text_getter: callable, font_size: int = 36, max_width: int = 0):
        self.color = color
        self.text_getter = text_getter
        self.font = pygame.font.Font(str(FONT_PATH), font_size)
        self.max_width = max_width
        super().__init__(coord, (0, 0), parent)

    def render(self, screen: pygame.Surface):
        content = self.text_getter()
        content = content if self.max_width == 0 else cropText(content, self.font, self.max_width)
        text = self.font.render(content, False, self.color)
        size = tuple(int(s * self.parent.ratio) for s in text.get_size())
        text = pygame.transform.scale(text, size)
        screen.blit(text, self.coord)


class BoldDynamicTextRender(DynamicTextRender):

    def render(self, screen: pygame.Surface):
        content = self.text_getter()
        content = content if self.max_width == 0 else cropText(content, self.font, self.max_width)
        text = self.font.render(content, False, (0, 0, 0))
        size = tuple(int(s * self.parent.ratio) for s in text.get_size())
        text = pygame.transform.scale(text, size)
        screen.blit(text, (self.coord[0] + 2, self.coord[1] + 2))
        super().render(screen)


class Button(Child):
    base: pygame.Surface
    hover: pygame.Surface
    click: pygame.Surface = None
    disable: pygame.Surface = None
    dark_text: pygame.Surface = None
    light_text: pygame.Surface = None
    background_size: tuple[int, int]
    callback: callable
    can_interact: bool = True
    disabled: bool = False

    def __init__(self, coord: tuple[int, ...], parent: 'Container', path: Path, callback: callable,
                 has_pressed: bool = True, disabled: bool = False, text: str = None):
        image = Button.getVariant(path, 'base')  # used to get the size
        super().__init__(coord, image.get_size(), parent)
        self.callback = callback
        self.base = pygame.transform.scale(image, self.size)
        self.hover = pygame.transform.scale(Button.getVariant(path, 'hover'), self.size)
        if has_pressed:  # if the button has a pressed state
            self.click = pygame.transform.scale(Button.getVariant(path, 'click'), self.size)
        if disabled:
            self.disabled = disabled
            try:
                self.disable = pygame.transform.scale(Button.getVariant(path, 'disable'), self.size)
            except FileNotFoundError:
                print('ignoring disable texture as it was not found')
        if text is not None:
            b_w, b_h = image.get_size()
            font = pygame.font.Font(str(FONT_PATH), b_h - 10)
            text = cropText(text, font, b_w - 6)
            self.light_text = font.render(text, False, (255, 255, 255))
            self.dark_text = font.render(text, False, (0, 0, 0))
            size = tuple(int(s * self.parent.ratio) for s in self.light_text.get_size())
            self.light_text = pygame.transform.scale(self.light_text, size)
            self.dark_text = pygame.transform.scale(self.dark_text, size)

    @staticmethod
    def getVariant(path: Path, variant: str) -> pygame.Surface:
        return pygame.image.load(path.parent / (path.stem + f'_{variant}' + path.suffix))

    def handleEvents(self):
        if not mouseIn(self.coord, self.size) or self.disabled:
            return
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                self.callback()

    @property
    def background(self) -> pygame.Surface:
        if self.disable and self.disabled:
            return self.disable
        if mouseIn(self.coord, self.size) and not self.disabled:
            return self.click if pygame.mouse.get_pressed()[0] and self.click is not None else self.hover
        return self.base

    @property
    def foreground(self) -> tuple[pygame.surface, tuple[int, ...]] | None:
        if self.light_text is None:
            return None
        coord = centerCoord(
            self.coord,
            self.size,
            self.light_text.get_size()
        )
        if self.disabled or (mouseIn(self.coord, self.size) and pygame.mouse.get_pressed()[0]):
            return self.light_text, coord
        return self.dark_text, coord

    def render(self, screen: pygame.Surface):
        screen.blit(self.background, self.coord)
        if self.foreground:
            screen.blit(*self.foreground)


class RadioButton(Button):
    selected: bool
    selected_base: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container', path: Path,
                 callback: callable, selected: bool = False, disabled: bool = False, text: str = None):
        self.selected = selected
        super().__init__(coord, parent, path, callback, False, disabled, text)
        self.selected_base = pygame.transform.scale(Button.getVariant(path, 'selected'), self.size)

    def handleEvents(self):
        if not mouseIn(self.coord, self.size) or self.disabled or self.selected:
            return
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                self.selected = True
                self.callback()

    @property
    def background(self) -> pygame.Surface:
        if self.disabled and self.disable:
            return self.disable
        if mouseIn(self.coord, self.size) and not self.disabled and not self.selected:
            return self.hover
        return self.selected_base if self.selected else self.base


class ToggleButton(Button):
    on: bool
    on_base: pygame.Surface
    on_hover: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container', path: Path,
                 callback: callable, on: bool = False, disabled: bool = False, text: str = None):
        self.on = on
        super().__init__(
            coord, parent,
            path.parent / f'{path.stem}_off{path.suffix}',
            callback, False,
            disabled, text
        )
        self.on_base = pygame.transform.scale(Button.getVariant(path, 'on_base'), self.size)
        self.on_hover = pygame.transform.scale(Button.getVariant(path, 'on_hover'), self.size)

    def handleEvents(self):
        if not mouseIn(self.coord, self.size) or self.disabled:
            return
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                self.on = not self.on
                self.callback(self.on)

    @property
    def background(self) -> pygame.Surface:
        if self.disabled and self.disable:
            return self.disable
        if mouseIn(self.coord, self.size) and not self.disabled:
            return self.on_hover if self.on else self.hover
        return self.on_base if self.on else self.base

    @property
    def foreground(self) -> tuple[pygame.surface, tuple[int, ...]] | None:
        if self.light_text is None:
            return None
        coord = centerCoord(
            self.coord,
            self.size,
            self.light_text.get_size()
        )
        if self.on:
            return self.light_text, coord
        return self.dark_text, coord


class Input(Child):
    font: pygame.font.Font
    on_validate: callable
    suggestion: str
    text: str
    max_width: int
    editing: bool
    bg: pygame.Surface
    bg_edit: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container', on_validate: callable, suggestion: str, max_width: int, font_size: int = 36):
        self.font = pygame.font.Font(str(FONT_PATH), font_size)
        self.on_validate = on_validate
        self.suggestion = suggestion
        self.text = ''
        self.max_width = max_width
        self.editing = False
        bg_size = (max_width + 6, font_size + 6)
        super().__init__(coord, bg_size, parent)
        self.bg = pygame.surface.Surface(bg_size)
        self.bg.fill((160, 160, 160))
        pygame.draw.rect(self.bg, (0, 0, 0), (1, 1, bg_size[0] - 2, bg_size[1] - 2))
        self.bg = pygame.transform.scale(self.bg, self.size)

        self.bg_edit = pygame.surface.Surface(bg_size)
        self.bg_edit.fill((252, 252, 252))
        pygame.draw.rect(self.bg_edit, (0, 0, 0), (1, 1, bg_size[0] - 2, bg_size[1] - 2))
        self.bg_edit = pygame.transform.scale(self.bg_edit, self.size)

    def handleEvents(self):
        # enter editing context
        if not self.editing and mouseIn(self.coord, self.size):
            for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
                if event.button == 1:
                    self.editing = True

        # quit editing context
        elif self.editing and not mouseIn(self.coord, self.size):
            for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
                if event.button == 1:
                    self.editing = False
                pygame.event.post(event)  # might get consumed by button click

        if self.editing:
            for event in pygame.event.get([pygame.KEYDOWN]):
                if (pygame.K_a <= event.key <= pygame.K_z
                        or pygame.K_0 <= event.key <= pygame.K_9
                        or event.key in [pygame.K_SPACE, pygame.K_UNDERSCORE]):
                    self.text += event.unicode
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                elif event.key == pygame.K_RETURN:
                    self.editing = False
                    self.on_validate(self.text)
                else:  # resubmit unused events
                    pygame.event.post(event)
                    continue
                # consume key specific event
                pygame.event.get([pygame.USEREVENT + event.key])

    def visibleRect(self, text_surface: pygame.Surface) -> tuple[int, int, int, int]:
        if not self.editing:
            return (
                0,
                0,
                min(text_surface.get_size()[0], math.floor(self.max_width * self.parent.ratio)),
                text_surface.get_size()[1]
            )
        return (
            max(0, text_surface.get_size()[0] - math.floor(self.max_width * self.parent.ratio)),
            0,
            text_surface.get_size()[0],
            text_surface.get_size()[1]
        )

    def render(self, screen: pygame.Surface):
        screen.blit(self.bg_edit if self.editing else self.bg, self.coord)

        content = self.suggestion if len(self.text) == 0 else self.text

        under_text = self.font.render(content, False, (62, 62, 62))
        text = self.font.render(content, False, (91, 91, 91) if len(self.text) == 0 else (252, 252, 252))
        size = tuple(int(s * self.parent.ratio) for s in text.get_size())
        under_text = pygame.transform.scale(under_text, size)
        text = pygame.transform.scale(text, size)

        screen.blit(
            under_text,
            tuple(c + 5 * self.parent.ratio for c in self.coord),
            self.visibleRect(under_text)
        )
        screen.blit(
            text,
            tuple(c + 3 * self.parent.ratio for c in self.coord),
            self.visibleRect(text)
        )
