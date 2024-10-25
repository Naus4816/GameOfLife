import pygame
import math
from pathlib import Path
from render.Utils import fitRatio, centerCoord
from logic.Board import Board
from logic.Handler import LogicHandler

ASSETS_PATH = Path(__file__).parent.parent / 'assets'
FONT_PATH: Path = ASSETS_PATH / 'font.ttf'


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
    base: pygame.Surface
    hover: pygame.Surface
    click: pygame.Surface = None
    disable: pygame.Surface = None
    callback: callable
    can_interact: bool = True
    disabled: bool = False

    def __init__(self, coord: tuple[int, ...], parent: 'Container', path: Path, callback: callable,
                 has_pressed: bool = True, disabled: bool = False):
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

    @staticmethod
    def getVariant(path: Path, variant: str) -> pygame.Surface:
        return pygame.image.load(path.parent / (path.stem + f'_{variant}' + path.suffix))

    def handleEvents(self):
        if not self.mouseIn() or self.disabled:
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
        if self.disable and self.disabled:
            return self.disable
        if self.mouseIn() and not self.disabled:
            return self.click if pygame.mouse.get_pressed()[0] and self.click is not None else self.hover
        return self.base

    def render(self, screen: pygame.Surface):
        screen.blit(self.background, self.coord)


class ToggleButton(Button):
    on: bool
    on_base: pygame.Surface
    on_hover: pygame.Surface

    def __init__(self, coord: tuple[int, ...], parent: 'Container', path: Path, callback: callable, on: bool = False):
        self.on = on
        super().__init__(coord, parent, path.parent / f'{path.stem}_off{path.suffix}', callback, False)
        self.on_base = pygame.transform.scale(Button.getVariant(path, 'on_base'), self.size)
        self.on_hover = pygame.transform.scale(Button.getVariant(path, 'on_hover'), self.size)

    def handleEvents(self):
        if not self.mouseIn() or self.disabled:
            return
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                self.on = not self.on
                self.callback(self.on)

    @property
    def background(self) -> pygame.Surface:
        if self.mouseIn() and not self.disabled:
            return self.on_hover if self.on else self.hover
        return self.on_base if self.on else self.base


class TimeBarRender(Child):
    logic: LogicHandler
    # store children in a list with play_pause, step, speed_1, speed_2, speed_3, supper_fast
    children: tuple[ToggleButton, Button, ToggleButton, ToggleButton, ToggleButton, ToggleButton]

    def toggle(self, on: bool):
        self.setSpeed(self.logic.tick_rate if on else 0)

    def step(self):
        # only step when the board is paused
        if self.logic.paused.locked():
            self.logic.board.tick()
        else:
            self.children[1].disabled = True

    def setSpeed(self, tick_rate: int):
        if tick_rate == 0:  # stop instead
            self.logic.pause()
            self.children[0].on = False
            self.children[1].disabled = False
            for child in self.children[2:]:
                child.on = False
            return

        # set the correct states for each toggle and disable stepping
        self.logic.tick_rate = tick_rate

        # set states for each buttons
        self.children[0].on = True
        self.children[1].disabled = True
        self.children[2].on = tick_rate >= 5
        self.children[3].on = tick_rate >= 10
        self.children[4].on = tick_rate >= 20
        self.children[5].on = tick_rate == 100

        # make sure to resume if previously paused
        if self.logic.isPaused():
            self.logic.resume()

    def speedSetter(self, tick_rate: int) -> callable:
        """
        returns a function that handles speed changes
        :param tick_rate: the tick rate to set the board to
        :return: a function that will be used as callback
        """
        return lambda x: self.setSpeed(tick_rate) \
            if x or self.logic.tick_rate > tick_rate else \
            self.setSpeed(next(s for s in [100, 20, 10, 5, 0] if s < tick_rate))

    def __init__(self, coord: tuple[int, ...], parent: 'Container', logic: LogicHandler):
        self.logic = logic
        x, y = coord
        self.children = (
            ToggleButton((x, y), parent, ASSETS_PATH / 'play_pause.png', self.toggle, True),
            Button((x + 21, y), parent, ASSETS_PATH / 'step.png', self.step, False, True),
            ToggleButton((x + 42, y), parent, ASSETS_PATH / 'speed.png', self.speedSetter(5), True),
            ToggleButton((x + 55, y), parent, ASSETS_PATH / 'speed.png', self.speedSetter(10), True),
            ToggleButton((x + 68, y), parent, ASSETS_PATH / 'speed.png', self.speedSetter(20)),
            ToggleButton((x + 81, y), parent, ASSETS_PATH / 'super_speed.png', self.speedSetter(100))
        )
        super().__init__(coord, (99, 18), parent)

    def handleEvents(self):
        for child in self.children:
            child.handleEvents()

    def render(self, screen: pygame.Surface):
        for child in self.children:
            child.render(screen)


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
