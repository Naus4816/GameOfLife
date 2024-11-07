import pygame
import math
import numpy as np
from render.Utils import mouseIn, centerCoord
from logic.Board import Board, Preset
from logic.Handler import LogicHandler
from threading import Thread
from pathlib import Path
from render.Components import Child, Container, BoldStaticTextRender, Button, ToggleButton, BoldDynamicTextRender, ScaledChild, Input, ASSETS_PATH

DATA_PATH = Path(__file__).parent.parent / 'data'


class TimeBarRender(Child):
    logic: LogicHandler
    # store children in a list with play_pause, step, speed_1, speed_2, speed_3, supper_fast
    children: tuple[ToggleButton, Button, ToggleButton, ToggleButton, ToggleButton, ToggleButton]

    def __init__(self, coord: tuple[int, ...], parent: 'Container', logic: LogicHandler):
        self.logic = logic
        x, y = coord
        self.children = (
            ToggleButton((x, y), parent, ASSETS_PATH / 'toggles' / 'play_pause.png', self.toggle, True),
            Button((x + 21, y), parent, ASSETS_PATH / 'buttons' / 'step.png', self.step, False, True),
            ToggleButton((x + 42, y), parent, ASSETS_PATH / 'toggles' / 'speed.png', self.speedSetter(5), True),
            ToggleButton((x + 55, y), parent, ASSETS_PATH / 'toggles' / 'speed.png', self.speedSetter(10), True),
            ToggleButton((x + 68, y), parent, ASSETS_PATH / 'toggles' / 'speed.png', self.speedSetter(20)),
            ToggleButton((x + 81, y), parent, ASSETS_PATH / 'toggles' / 'super_speed.png', self.speedSetter(100))
        )
        self.setStates(not self.logic.isPaused())
        super().__init__(coord, (99, 18), parent)

    def handleEvents(self):
        # handle keys for ease of use
        if pygame.event.get([pygame.USEREVENT + pygame.K_SPACE]):
            self.toggle(not self.children[0].on)
        if pygame.event.get([pygame.USEREVENT + pygame.K_1]):
            self.setSpeed(5)
        if pygame.event.get([pygame.USEREVENT + pygame.K_2]):
            self.setSpeed(10)
        if pygame.event.get([pygame.USEREVENT + pygame.K_3]):
            self.setSpeed(20)
        if pygame.event.get([pygame.USEREVENT + pygame.K_4]):
            self.setSpeed(100)
        # handle events for each child
        for child in self.children:
            child.handleEvents()

    def render(self, screen: pygame.Surface):
        for child in self.children:
            child.render(screen)

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
            self.setStates(False)
            return

        self.logic.tick_rate = tick_rate
        self.setStates(True)

        # make sure to resume if previously paused
        if self.logic.isPaused():
            self.logic.resume()

    def setStates(self, running: bool):
        # set the correct states for each toggle and disable stepping
        tick_rate = self.logic.tick_rate

        # set states for each buttons
        self.children[0].on = running
        self.children[1].disabled = running
        self.children[2].on = tick_rate >= 5 and running
        self.children[3].on = tick_rate >= 10 and running
        self.children[4].on = tick_rate >= 20 and running
        self.children[5].on = tick_rate == 100 and running

    def speedSetter(self, tick_rate: int) -> callable:
        """
        returns a function that handles speed changes
        :param tick_rate: the tick rate to set the board to
        :return: a function that will be used as callback
        """
        return lambda x: self.setSpeed(tick_rate) \
            if x or self.logic.tick_rate > tick_rate else \
            self.setSpeed(next(s for s in [100, 20, 10, 5, 0] if s < tick_rate))


class TpsRender(BoldDynamicTextRender):
    logic: LogicHandler

    def __init__(self, coord: tuple[int, ...], parent: 'Container', logic: LogicHandler, font_size: int = 36):
        self.logic = logic
        super().__init__(coord, parent, (255, 255, 255), lambda: f'{self.logic.current_tps:.2f} TPS', font_size)


class BoardRender(ScaledChild):
    board: Board | Preset

    def __init__(self, coord: tuple[int, ...], size: tuple[int, ...],
                 parent: 'Container', board: Board | Preset):
        self.board = board
        super().__init__(coord, size, board.getSize(), parent)
        parent.add(BoldStaticTextRender(  # add title to parent with relative pos
            (coord[0]-4, coord[1]-25), parent,
            board.name if isinstance(board, Preset) else 'New Board',
            (255, 255, 255), 18,
            size[0] + 8
        ))

    def render(self, screen: pygame.Surface):
        image = self.board.getImage()
        pyg_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
        screen.blit(pygame.transform.scale(pyg_image, self.size), self.coord)


class PresetRender(BoardRender):
    referer: 'BoardRender'

    def __init__(self, parent: 'Container', referer: 'BoardRender', preset: Preset):
        self.referer = referer
        super().__init__((0, 0), preset.getSize(), parent, preset)
        self.ratio = referer.ratio
        self.size = tuple(math.floor(s * self.ratio) for s in preset.getSize())

    def handleEvents(self):
        if not mouseIn(*self.placement_box):
            return
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                Thread(target=lambda: self.referer.board.paste(self.board, *self.relative_coord)).start()

    def render(self, screen: pygame.Surface):
        if not mouseIn(*self.placement_box):
            return
        image = self.board.getImage()
        pyg_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
        screen.blit(pygame.transform.scale(pyg_image, self.size), self.snap_coord)

    @property
    def placement_box(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        p_x, p_y = self.referer.coord
        p_w, p_h = self.referer.size
        width, height = self.size
        return (p_x + width, p_y + height), (p_w - width, p_h - height)

    @property
    def relative_coord(self):
        x, y = pygame.mouse.get_pos()
        p_x, p_y = self.referer.coord
        ratio = self.referer.ratio
        c_w, c_h = self.board.getSize()
        return math.floor((x - p_x) / ratio) - c_w, math.floor((y - p_y) / ratio) - c_h

    @property
    def snap_coord(self):
        p_x, p_y = self.referer.coord
        ratio = self.referer.ratio
        r_x, r_y = self.relative_coord
        return math.ceil(r_x * ratio) + p_x, math.ceil(r_y * ratio) + p_y


class PresetContainer(Container):
    current_page: int
    preset: Preset
    presets: list[Preset]
    referer: BoardRender
    left_preset: Container | None
    right_preset: Container | None
    left_arrow: Button
    right_arrow: Button
    pencil: ToggleButton
    eraser: ToggleButton

    def __init__(self, coord: tuple[int, ...], parent: 'Container', referer: BoardRender):
        super().__init__(coord, None, parent, ASSETS_PATH / 'preset_container.png')
        self.preset = None
        self.current_page = 0
        self.referer = referer
        self.left_arrow = Button(
            (6, 91), self,
            ASSETS_PATH / 'buttons' / 'left_arrow.png',
            lambda: self.changePage(self.current_page - 1),
            disabled=True
        )
        self.right_arrow = Button(
            (328, 91), self,
            ASSETS_PATH / 'buttons' / 'right_arrow.png',
            lambda: self.changePage(self.current_page + 1),
            disabled=True
        )
        self.pencil = ToggleButton(
            (375, 447), referer.parent,
            ASSETS_PATH / 'toggles' / 'edit.png',
            self.presetSetter('__pencil__')
        )
        self.eraser = ToggleButton(
            (354, 447), referer.parent,
            ASSETS_PATH / 'toggles' / 'erase.png',
            self.presetSetter('__eraser__')
        )
        referer.parent.add(self.pencil)
        referer.parent.add(self.eraser)

        self.presets = []
        self.loadPresets()

    def loadPresets(self):
        self.presets.clear()
        for file in DATA_PATH.glob('*.preset'):
            self.presets.append(Preset(file, file.stem))
            print(f'Loaded preset {file.stem}')
        self.changePage(0)

    def changePage(self, page: int) -> None:
        self.current_page = page
        self.left_preset = None
        self.right_preset = None

        offset = page * 2
        for i, preset in enumerate(self.presets[offset:offset + 2]):
            elem = Container((27 + (152 * i), 6), None, self, ASSETS_PATH / 'preset_template.png')
            if i == 0:
                self.left_preset = elem
            else:
                self.right_preset = elem

            elem.add(BoardRender((10, 31), (126, 126), elem, preset))
            elem.add(ToggleButton(
                (6, 164), elem,
                ASSETS_PATH / 'toggles' / 'select.png',
                self.presetSetter(preset.name),
                on=self.preset is not None and self.preset == preset,
                text='Select'
            ))
            elem.add(Button(
                (122, 164), elem,
                ASSETS_PATH / 'buttons' / 'delete.png',
                self.presetDeleter(preset.name)
            ))
        self.left_arrow.disabled = self.current_page == 0
        self.right_arrow.disabled = (page + 1) == (len(self.presets) + 1) // 2

    def presetSetter(self, name: str) -> callable:
        return lambda x: self.setPreset(name) if x else self.setPreset(None)

    def presetDeleter(self, name: str) -> callable:
        return lambda: self.deletePreset(name)

    def addPreset(self, board_region: np.ndarray, name: str) -> None:
        preset = Preset(board_region, name)
        preset.save(DATA_PATH)
        self.presets.append(preset)
        if len(self.presets) - self.current_page * 2 == 1:
            self.changePage(self.current_page)

    def deletePreset(self, name: str) -> None:
        preset = next(p for p in self.presets if p.name == name)
        preset.delete()
        self.presets.remove(preset)
        self.changePage(self.current_page)

    def setPreset(self, name: str | Preset | None) -> None:
        self.referer.parent.clear(type=PresetRender)
        if name is None:
            self.preset = None
        elif name.startswith('__'):
            preset = np.zeros((3, 3), dtype=bool)
            if name == '__pencil__':
                preset[1, 1] = True

            preset = Preset(preset, name)
            if name == '__eraser__':
                preset.refresh()
                preset.background_color = (108, 0, 0)
                preset.getImage(False)

            self.preset = preset
        else:
            self.preset = next((p for p in self.presets if p.name == name), None)
        if self.preset is not None:
            self.referer.parent.add(PresetRender(self, self.referer, self.preset))
        self.pencil.on = name == '__pencil__'
        self.eraser.on = name == '__eraser__'
        for child in [self.left_preset, self.right_preset]:
            if child is not None:
                child.get(type=ToggleButton)[0].on = self.preset == child.get(type=BoardRender)[0].board

    def rotatePreset(self):
        if self.preset is None:
            return
        self.preset = self.preset.rotate()
        self.referer.parent.clear(type=PresetRender)
        self.referer.parent.add(PresetRender(self, self.referer, self.preset))

    def handleEvents(self):
        if pygame.event.get([pygame.USEREVENT + pygame.K_r]):
            self.rotatePreset()
        for child in [self.left_arrow, self.right_arrow, self.left_preset, self.right_preset]:
            if child is None:
                continue
            child.handleEvents()

    def render(self, screen: pygame.Surface):
        super().render(screen)
        for child in [self.left_preset, self.right_preset, self.left_arrow, self.right_arrow]:
            if child is None:
                continue
            child.render(screen)


class SavePopup(Container):
    input_element: Input
    make_preset: ToggleButton
    referer: BoardRender
    on_board_saved: callable
    on_presets_saved: callable

    def __init__(self, parent: 'Container', referer: 'BoardRender', on_board_saved: callable, on_presets_saved: callable):
        coord = centerCoord((19, 70), (378, 378), (308, 72))
        self.referer = referer
        self.on_board_saved = on_board_saved
        self.on_presets_saved = on_presets_saved
        super().__init__(coord, None, parent, ASSETS_PATH / 'save_popup.png')

        self.input_element = Input(
            (82, 27), self,
            lambda text: self.save(),
            referer.board.name if isinstance(referer.board, Preset) else '*',
            214, 12
        )
        self.input_element.editing = True  # start editing immediately

        self.make_preset = ToggleButton(
            (6, 48), self,
            ASSETS_PATH / 'toggles' / 'edit.png',
            lambda x: None
        )

        self.add(BoldStaticTextRender((6, 6), self, 'Save File', (255, 255, 255), 18))
        self.add(Button((287, 1), self, ASSETS_PATH / 'buttons' / 'exit.png', self.close))
        self.add(BoldStaticTextRender((6, 28), self, 'Name:', (255, 255, 255), 16))
        self.add(self.input_element)
        self.add(self.make_preset)
        self.add(Button((284, 48), self, ASSETS_PATH / 'buttons' / 'save.png', self.save))
        parent.add(self)

    def handleEvents(self):
        super().handleEvents()
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1 and not mouseIn(self.coord, self.size):
                self.close()
        pygame.event.get()  # clear the event queue

    def close(self):
        self.parent.children.remove(self)

    def save(self):
        board = self.referer.board
        name = self.input_element.text
        if not isinstance(board, Preset) and len(name) > 0:
            board = Preset(board, name, self.make_preset.on, not self.make_preset.on and board.use_gpu)
        elif name == '':
            name = board.name
        else:
            return
        board.save(DATA_PATH, name, self.make_preset.on)

        if not self.make_preset.on:
            self.on_board_saved(board)
        else:
            self.on_presets_saved()
        self.close()
