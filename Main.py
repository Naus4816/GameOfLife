import pygame
from logic.Board import Board
from logic.Handler import LogicHandler
from render.Utils import fitRatio
from pathlib import Path
from render.Components import Container, BoardRender, TpsRender, BoldStaticTextRender, Button
import win32api
import win32con
import win32gui

RUNNING = True


def kill():
    global RUNNING
    RUNNING = False


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption("Game of Life")
    screen = pygame.display.set_mode((1532, 960), pygame.NOFRAME, pygame.SRCALPHA)
    clock = pygame.time.Clock()

    # Make window transparent see https://stackoverflow.com/questions/550001/fully-transparent-windows-in-pygame
    # Create layered window
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    # Set window transparency color
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*(0, 0, 0)), 0, win32con.LWA_COLORKEY)

    board = Board(True, True, 370, 370)
    Board.background_color = 33
    ratio = fitRatio(screen.get_size(), board.getSize())
    new_size = tuple(int(x*ratio) for x in board.getSize())

    # initialise the logic handler with the board
    # running = True
    logic = LogicHandler(board)

    # create the main container
    assets = Path(__file__).parent / 'assets'
    background = assets / 'background.png'
    main = Container.fromScreen(screen, background)
    main.add(BoardRender((19, 70), (370, 370), main, board))
    tps_render = TpsRender((19, 70), main, logic, 12)
    main.add(tps_render)
    main.add(BoldStaticTextRender((6, 6), main, "Game of Life", (255, 255, 255), 26))
    main.add(Button((739, 3), main, assets / 'close.png', kill))

    logic.start()
    while RUNNING:
        # handle the events
        main.handleEvents()
        for event in pygame.event.get():
            pass  # consume remaining events

        # display the main container
        main.render(screen)

        # flip to refresh the screen
        pygame.display.flip()
        clock.tick(144)

    logic.running = False
    pygame.quit()
