import threading
from logic.Board import Board, Preset
from pathlib import Path
import pygame


class LogicHandler(threading.Thread):
    board: Board
    presets: list[Preset | None]
    data_path: Path
    running: bool
    tick_rate: int
    current_tps: float

    def __init__(self, board: Board, tick_rate: int = 10):
        super().__init__()
        self.board = board
        self.running = True
        self.tick_rate = tick_rate
        self.current_tps = 0
        self.presets = [None]

        self.data_path = Path(__file__).parent / 'data'
        self.__loadPresets__()

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.board.tick()
            clock.tick(self.tick_rate)
            self.current_tps = clock.get_fps()

    def __loadPresets__(self) -> None:
        for file in self.data_path.glob('*.preset'):
            self.presets.append(Preset(file, file.stem))
            print(f'Loaded preset {file.stem}')

    def setPreset(self, name: str | None) -> None:
        # clear last preset to be the None one (so nothing is drawn)
        if name is None:
            self.presets.remove(None)
            self.presets.insert(0, None)
        # move the preset to the front of the list
        else:
            preset = next((p for p in self.presets if p.name == name), None)
            if preset is not None:
                self.presets.remove(preset)
                self.presets.insert(0, preset)

    def addPreset(self, preset: Preset) -> None:
        self.presets.append(preset)
        preset.save(self.data_path)

    def removePreset(self, name: str) -> None:
        preset = next((p for p in self.presets if p.name == name), None)
        if preset is not None:
            self.presets.remove(preset)

            del preset

    def presetSize(self, board_ratio: float = 1) -> tuple[int, ...]:
        if self.preset is None:
            return 0, 0
        return tuple(int(x * board_ratio) for x in self.preset.getSize())

    def nextPreset(self):
        if len(self.presets) <= 1:
            return
        self.presets.append(self.presets.pop(0))

    @property
    def preset(self):
        return self.presets[0]