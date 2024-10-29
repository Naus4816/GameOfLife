import pygame
from logic.Board import Board
from logic.Handler import LogicHandler
from render.Utils import centerCoord
from render.Components import Container, BoldStaticTextRender, Button, ASSETS_PATH
from render.ComplexComponents import BoardRender, TpsRender, TimeBarRender, PresetContainer
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
    screen = pygame.display.set_mode((1532, 960), pygame.NOFRAME)
    pygame.display.set_icon(pygame.image.load(ASSETS_PATH / 'icon.png'))
    clock = pygame.time.Clock()

    # Make window transparent see https://stackoverflow.com/questions/550001/fully-transparent-windows-in-pygame
    # Create layered window
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    # Set window transparency color
    BACKGROUND_COLOR = (12, 90, 1)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*BACKGROUND_COLOR), 0, win32con.LWA_COLORKEY)

    # board = Board(True, False, 185, 185)
    board = Board(True, False, 185, 185)
    Board.background_color = 33

    # initialise the logic handler with the board
    # running = True
    logic = LogicHandler(board)

    # create the main container
    main = Container.fromScreen(screen, ASSETS_PATH / 'background.png')
    board_render = BoardRender((19, 70), (370, 370), main, board)
    main.add(board_render)
    main.add(TpsRender((19, 70), main, logic, 12))
    main.add(BoldStaticTextRender((6, 6), main, "Game of Life", (255, 255, 255), 26))
    main.add(Button((739, 3), main, ASSETS_PATH / 'buttons' / 'close.png', kill))
    main.add(TimeBarRender(centerCoord((15, 447), (378, 18), (99, 18)), main, logic))
    main.add(PresetContainer((405, 39), main, board_render))

    logic.start()
    while RUNNING:
        # process key press in individual events for granular use
        for event in pygame.event.get([pygame.KEYDOWN]):
            pygame.event.post(pygame.event.Event(pygame.USEREVENT + event.key))
            pygame.event.post(event)  # post the original event back to the queue
        # handle the events
        main.handleEvents()
        for event in pygame.event.get():
            pass  # consume remaining events

        # display the main container
        screen.fill(BACKGROUND_COLOR)
        main.render(screen)

        # flip to refresh the screen
        pygame.display.flip()
        clock.tick(144)

    logic.running = False
    if logic.isPaused():
        logic.resume()
    pygame.quit()
