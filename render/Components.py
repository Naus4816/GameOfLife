import pygame
import math
from pathlib import Path
from render.Utils import fitRatio, centerCoord
from logic.Board import Board
from logic.Handler import LogicHandler

FONT_PATH: Path = Path(__file__).parent.parent / 'assets' / 'font.ttf'


class Child:
    coord: tuple[int, ...]
    size: tuple[int, ...]
    parent: 'Container'
    can_interact: bool = False

    def __init__(self, coord: tuple[int, ...], size: tuple[int, ...], parent: 'Container'):
        self.parent = parent
        self.size = tuple(math.floor(s * parent.ratio) for s in size)
        self.coord = tuple(math.floor(s * parent.ratio) + p for s, p in zip(coord, parent.coord))

    def handleEvents(self):
        pass

    def render(self, screen: pygame.Surface):
        pass


class Container(Child):
    background: pygame.Surface
    children: list[Child]
    ratio: float

    def __init__(self, coord: tuple[int, ...], size: tuple[int, ...], parent: 'Container', path: Path):
        bg = pygame.image.load(str(path))
        self.ratio = fitRatio(size, bg.get_size())
        self.background = pygame.transform.scale(bg, tuple(int(x * self.ratio) for x in bg.get_size()))
        self.children = []
        super().__init__(coord, self.background.get_size(), parent)
        self.coord = centerCoord(self.coord, size, self.background.get_size())

    @staticmethod
    def fromScreen(screen: pygame.Surface, path: Path) -> 'Container':
        container: Container = object.__new__(Container)
        container.__class__ = Container
        container.coord = (0, 0)
        container.size = screen.get_size()
        container.ratio = 1
        return Container(container.coord, container.size, container, path)

    @property
    def can_interact(self) -> bool:
        return any(i for i in self.children)

    def handleEvents(self):
        for child in self.children[::-1]:
            child.handleEvents()

    def onClick(self):
        x, y = pygame.mouse.get_pos()
        for min_x, min_y in self.children:  # TODO
            pass

    def add(self, child):
        self.children.append(child)

    def render(self, screen: pygame.Surface):
        screen.blit(self.background, self.coord)
        for child in self.children:
            child.render(screen)


class StaticTextRender(Child):
    text: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container',
                 text: str, color: tuple[int, int, int], font_size: int = 36):
        font = pygame.font.Font(str(FONT_PATH), font_size)
        self.text = font.render(text, False, color)
        size = self.text.get_size()
        super().__init__(coord, size, parent)
        self.text = pygame.transform.scale(self.text, self.size)

    def render(self, screen: pygame.Surface):
        screen.blit(self.text, self.coord)


class BoldStaticTextRender(StaticTextRender):
    under_text: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container',
                 text: str, color: tuple[int, int, int], font_size: int = 36):
        super().__init__(coord, parent, text, color, font_size)
        font = pygame.font.Font(str(FONT_PATH), font_size)
        self.under_text = font.render(text, False, (0, 0, 0))
        self.under_text = pygame.transform.scale(self.under_text, self.size)

    def render(self, screen: pygame.Surface):
        screen.blit(self.under_text, (self.coord[0] + 2, self.coord[1] + 2))
        super().render(screen)


class DynamicTextRender(Child):
    font: pygame.font.Font
    color: tuple[int, int, int]
    text_getter: callable

    def __init__(self, coord: tuple[int, ...], parent: 'Container',
                 color: tuple[int, int, int], text_getter: callable, font_size: int = 36):
        self.color = color
        self.text_getter = text_getter
        self.font = pygame.font.Font(str(FONT_PATH), font_size)
        super().__init__(coord, (0, 0), parent)

    def render(self, screen: pygame.Surface):
        text = self.font.render(self.text_getter(), False, self.color)
        size = tuple(int(s * self.parent.ratio) for s in text.get_size())
        text = pygame.transform.scale(text, size)
        screen.blit(text, self.coord)


class BoldDynamicTextRender(DynamicTextRender):

    def render(self, screen: pygame.Surface):
        text = self.font.render(self.text_getter(), False, (0, 0, 0))
        size = tuple(int(s * self.parent.ratio) for s in text.get_size())
        text = pygame.transform.scale(text, size)
        screen.blit(text, (self.coord[0] + 2, self.coord[1] + 2))
        super().render(screen)


class Button(Child):
    normal: pygame.Surface
    hover: pygame.Surface
    click: pygame.Surface
    callback: callable
    can_interact: bool = True

    def __init__(self, coord: tuple[int, ...], parent: 'Container', path: Path, callback: callable):
        image = Button.getVariant(path, 'base')  # used to get the size
        super().__init__(coord, image.get_size(), parent)
        self.callback = callback
        self.normal = pygame.transform.scale(image, self.size)
        self.hover = pygame.transform.scale(Button.getVariant(path, 'hover'), self.size)
        self.click = pygame.transform.scale(Button.getVariant(path, 'click'), self.size)

    @staticmethod
    def getVariant(path: Path, variant: str) -> pygame.Surface:
        return pygame.image.load(path.parent / (path.stem + f'_{variant}' + path.suffix))

    def handleEvents(self):
        if not self.mouseIn():
            return
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                self.callback()

    def mouseIn(self):
        x, y = pygame.mouse.get_pos()
        min_x, min_y = self.coord
        max_x, max_y = tuple(c + s for c, s in zip(self.coord, self.size))
        return min_x <= x <= max_x and min_y <= y <= max_y

    @property
    def background(self) -> pygame.Surface:
        if self.mouseIn():
            return self.click if pygame.mouse.get_pressed()[0] else self.hover
        return self.normal

    def render(self, screen: pygame.Surface):
        screen.blit(self.background, self.coord)


class TpsRender(BoldDynamicTextRender):
    logic: LogicHandler

    def __init__(self, coord: tuple[int, ...], parent: 'Container', logic: LogicHandler, font_size: int = 36):
        self.logic = logic
        super().__init__(coord, parent, (255, 255, 255), lambda: f'{self.logic.current_tps:.2f} TPS', font_size)


class BoardRender(Child):
    board: Board

    def __init__(self, coord: tuple[int, ...], size: tuple[int, ...], parent: 'Container', board: Board):
        self.board = board
        super().__init__(coord, size, parent)

    def render(self, screen: pygame.Surface):
        image = self.board.getImage()
        pyg_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
        screen.blit(pygame.transform.scale(pyg_image, self.size), self.coord)
