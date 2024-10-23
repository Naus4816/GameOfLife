import math
import pygame
from logic.Board import Board
from logic.Handler import LogicHandler
from render.Utils import fitRatio
from pathlib import Path
from render.Components import Container, BoardRender, TpsRender, BoldTextRender


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption("Game of Life")
    screen = pygame.display.set_mode((1532, 960))
    clock = pygame.time.Clock()

    board = Board(True, True, 126, 126)
    Board.background_color = 33
    ratio = fitRatio(screen.get_size(), board.getSize())
    new_size = tuple(int(x*ratio) for x in board.getSize())

    # initialise the logic handler with the board
    logic = LogicHandler(board)

    # create the main container
    background = Path(__file__).parent / 'assets' / 'background.png'
    main = Container.fromScreen(screen, background)
    main.add(BoardRender((19, 70), (370, 370), main, board))
    main.add(TpsRender((19, 70), main, logic, 18))
    main.add(BoldTextRender((6, 6), main, "Game of Life", (255, 255, 255), 26))

    running = True
    logic.start()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                # toggle the simulation
                if event.key == pygame.K_SPACE:
                    if logic.running:
                        logic.running = False
                        print("Paused")
                    else:
                        logic = LogicHandler(board, logic.tick_rate)
                        logic.start()
                        print("Resumed")
                # speed up the simulation
                elif event.key == pygame.K_UP:
                    if logic.tick_rate < 100:
                        logic.tick_rate += 5
                        print(f'Tick rate: {logic.tick_rate}')
                # slow down the simulation
                elif event.key == pygame.K_DOWN:
                    if logic.tick_rate > 5:
                        logic.tick_rate -= 5
                        print(f'Tick rate: {logic.tick_rate}')
                # change the preset
                elif event.key == pygame.K_r:
                    logic.nextPreset()
                    if logic.preset is not None:
                        print(f'Selected preset: {logic.preset.name}')
                    else:
                        print("No preset selected")
            # add glider to the board where the cursor is
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and logic.preset is not None:
                    mouse_pos = pygame.mouse.get_pos()
                    width, height = logic.presetSize()
                    x, y = tuple(math.floor(x / ratio) for x, y in zip(mouse_pos, logic.presetSize(ratio)))
                    if y+1-width <=0 or x+1-height <= 0 or y+2 >= board.shape[0] or x+2 >= board.shape[1]:
                        print("Out of bounds")
                        continue
                    board[y+1-width:y+1, x+1-height:x+1] = logic.preset[1:width+1, 1:height+1]
                    board.refresh()

        # # start with a blank slate
        # screen.fill((255, 255, 255))
        #
        # # get the image from the board and display it
        # image = board.getImage()
        # pyg_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
        # screen.blit(pygame.transform.scale(pyg_image, new_size), (0, 0))
        #
        # if logic.preset is not None:
        #     preset_size = logic.presetSize(ratio)
        #     # render glider at cursor position snapping to the board grid
        #     mouse_pos = pygame.mouse.get_pos()
        #     snap_pos = tuple(math.ceil(math.floor(x / ratio) * ratio) - y for x, y in zip(mouse_pos, preset_size))
        #     # render preset image
        #     preset_image = logic.preset.getImage()
        #     pyg_preset_image = pygame.image.fromstring(preset_image.tobytes(), preset_image.size, preset_image.mode)
        #     screen.blit(pygame.transform.scale(pyg_preset_image, preset_size), snap_pos)
        #
        # # display the current tick rate
        # font = pygame.font.Font(None, 36)
        # text = font.render(f"TPS: {logic.current_tps:.2f}", True, (0, 0, 0))
        # text_border = font.render(f"TPS: {logic.current_tps:.2f}", True, (255, 255, 255))
        # screen.blit(text, (12, 12))
        # screen.blit(text_border, (10, 10))

        # display the main container
        main.render(screen)

        # flip to refresh the screen
        pygame.display.flip()
        clock.tick(144)

    logic.running = False
    pygame.quit()
