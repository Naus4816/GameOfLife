import pygame
from logic.Board import Board
from logic.Handler import LogicHandler
from render.Utils import centerCoord
from render.Components import Container, BoldStaticTextRender, Button, Graph, ToggleButton, ASSETS_PATH
from render.ComplexComponents import BoardRender, TpsRender, TimeBarRender, PresetContainer, SavePopup
import win32api
import win32con
import win32gui


class Interface:
    running: bool
    main: Container
    fps: int
    screen: pygame.Surface
    logic: LogicHandler
    board: Board

    def __init__(self, screen, fps, logic, board: Board = None):
        self.running = True
        self.screen = screen
        self.fps = fps
        self.logic = logic
        self.setBoard(board)

    def setBoard(self, board: Board):
        """
        Set the board to be used by the logic handler and render and reset the components.
        """
        self.board = board
        self.logic.setBoard(board)
        self.makeComponents()

    def makeComponents(self):
        self.main = Container.fromScreen(self.screen, ASSETS_PATH / 'background.png')
        board_render = BoardRender((19, 70), (370, 370), self.main, self.board)
        self.main.add(board_render)
        self.main.add(TpsRender((19, 70), self.main, self.logic, 12))
        self.main.add(BoldStaticTextRender((6, 6), self.main, "Game of Life", (255, 255, 255), 26))
        self.main.add(Button((739, 3), self.main, ASSETS_PATH / 'buttons' / 'close.png', self.kill))
        self.main.add(TimeBarRender(centerCoord((15, 447), (378, 18), (99, 18)), self.main, self.logic))
        preset_container = PresetContainer((405, 39), self.main, board_render)
        self.main.add(preset_container)
        self.main.add(Button(
            (15, 447), self.main,
            ASSETS_PATH / 'buttons' / 'save.png',
            lambda: SavePopup(
                self.main,
                board_render,
                lambda b: self.setBoard(b),
                lambda: preset_container.loadPresets()
            )
        ))
        self.main.add(Button((35, 447), self.main, ASSETS_PATH / 'buttons' / 'quit.png', lambda: self.setBoard(None)))

        # add graphs
        generation_dataset = Graph.DataSet()
        time_dataset = Graph.DataSet(color=(120, 120, 120))
        alive_dataset = Graph.DataSet(color=(0, 120, 0), max_percent=0.2)
        births_dataset = Graph.DataSet(color=(0, 0, 120), max_percent=0.2)
        deaths_dataset = Graph.DataSet(color=(120, 0, 0), max_percent=0.2)
        self.board.setTrackers(
            generation=generation_dataset,
            time=time_dataset,
            alive=alive_dataset,
            births=births_dataset,
            deaths=deaths_dataset
        )
        self.main.add(Graph(
            (530, 270), (217, 111), self.main,
            generation_dataset, 200,
            [alive_dataset, births_dataset, deaths_dataset],
            5, 5, 8
        ))
        self.main.add(Graph(
            (530, 407), (217, 54), self.main,
            generation_dataset, 300,
            [time_dataset],
            5, 2, 8
        ))

        # add toggle buttons
        self.main.add(BoldStaticTextRender((411, 251), self.main, "Datasets", (255, 255, 255), 14))
        self.main.add(BoldStaticTextRender((411, 403), self.main, "Tick", (255, 255, 255), 14))
        self.main.add(BoldStaticTextRender((411, 420), self.main, "Time", (255, 255, 255), 14))
        self.main.add(ToggleButton((423, 272), self.main, ASSETS_PATH / 'toggles' / 'checkbox.png', lambda x: alive_dataset.changeVisibility(x), True))
        self.main.add(BoldStaticTextRender((440, 276), self.main, "Alive", (255, 255, 255), 8))
        self.main.add(ToggleButton((423, 291), self.main, ASSETS_PATH / 'toggles' / 'checkbox.png', lambda x: births_dataset.changeVisibility(x), True))
        self.main.add(BoldStaticTextRender((440, 295), self.main, "Births", (255, 255, 255), 8))
        self.main.add(ToggleButton((423, 310), self.main, ASSETS_PATH / 'toggles' / 'checkbox.png', lambda x: deaths_dataset.changeVisibility(x), True))
        self.main.add(BoldStaticTextRender((440, 314), self.main, "Deaths", (255, 255, 255), 8))

    def run(self):
        self.logic.start()
        clock = pygame.time.Clock()
        while self.running:
            # process key press in individual events for granular use
            for event in pygame.event.get([pygame.KEYDOWN]):
                pygame.event.post(pygame.event.Event(pygame.USEREVENT + event.key))
                pygame.event.post(event)  # post the original event back to the queue
            # handle the events
            self.main.handleEvents()
            for event in pygame.event.get():
                pass  # consume remaining events

            # display the main container
            screen.fill(BACKGROUND_COLOR)
            self.main.render(screen)

            # flip to refresh the screen
            pygame.display.flip()
            clock.tick(self.fps)

        # stop the logic handler if blocked at pause
        # otherwise the program will wait for the iteration to finish
        self.logic.running = False
        if self.logic.isPaused():
            self.logic.resume()
        pygame.quit()

    def kill(self):
        self.running = False


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption("Game of Life")
    screen = pygame.display.set_mode((1532, 960), pygame.NOFRAME)
    pygame.display.set_icon(pygame.image.load(ASSETS_PATH / 'icon.png'))

    # Make window transparent see https://stackoverflow.com/questions/550001/fully-transparent-windows-in-pygame
    # Create layered window
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    # Set window transparency color
    BACKGROUND_COLOR = (12, 90, 1)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*BACKGROUND_COLOR), 0, win32con.LWA_COLORKEY)

    # board = Board(True, False, 185, 185)
    Board.background_color = 33

    # create interface instance given the screen, clock, logic handler, and board
    Interface(screen, 144, LogicHandler(), Board(True, True, 185*16, 185*16)).run()
