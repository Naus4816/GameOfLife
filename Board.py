import numpy as np
from time import time
from matplotlib import pyplot as plt
from numba import cuda, jit
from glob import glob
from PIL import Image

class Board(np.ndarray):
    """
    Implements the storage and logic of the Game of Life board.
    """
    use_gpu: bool
    new_board: np.ndarray

    def __new__(cls, _: bool, height: int, width: int):
        obj = np.zeros((height + 2, width + 2), dtype=bool).view(cls)
        return obj

    def __init__(self, try_cuda: bool = True, *args, **kwargs):
        self.use_gpu = try_cuda and cuda.is_available()
        # Create second array to store the next state and be space efficient
        self.new_board = np.zeros_like(self, dtype=bool)
        if try_cuda and not self.use_gpu:
            print("CUDA is not available, defaulting to CPU instead.")

    @staticmethod
    @cuda.jit
    def updateGpu(board, new_board, width, height):
        """
        Ticks part of the board to compute next state using cuda.
        """
        x, y = cuda.grid(2)
        if 0 < x < width and 0 < y < height:
            alive_count = 0
            for i in range(-1, 2):
                for j in range(-1, 2):
                    alive_count += board[x + i, y + j]
            alive_count -= board[x, y]
            new_board[x, y] = alive_count in [2, 3] if board[x, y] else alive_count == 3

    def updateCPU(self):
        """
        Ticks the board to compute next state using cpu (slower but works everywhere).
        """
        for i, j in np.ndindex(self.shape):
            alive_count = self[i - 1:i + 2, j - 1:j + 2].sum() - self[i, j]
            self.new_board[i, j] = alive_count in [2, 3] if self[i, j] else alive_count == 3
        self[...] = self.new_board

    def tick(self):
        """
        Ticks the board to compute next state.
        """
        if self.use_gpu:  # use cuda if available (determined at init)
            d_board = cuda.to_device(self)
            d_new_board = cuda.to_device(self.new_board)

            threads_per_blocks = (16, 16)
            blocks_per_grid = (
                (self.shape[0] + threads_per_blocks[0] - 1) // threads_per_blocks[0],
                (self.shape[1] + threads_per_blocks[1] - 1) // threads_per_blocks[1]
            )
            self.updateGpu[blocks_per_grid, threads_per_blocks](d_board, d_new_board, *self.shape)
            self[...] = d_new_board.copy_to_host()
        else:
            self.updateCPU()

    def countAlive(self, i: int, j: int) -> bool:
        """
        Get the amount of alive neighbors of a cell.
        """
        return self[i - 1:i + 2, j - 1:j + 1].sum() - self[i, j]



if __name__ == "__main__":
    rows, cols = 126, 126
    board = Board(False, rows, cols)

    # Add Glider to board at position (10, 100)
    board[10:13, 100:103] = [[0, 1, 0], [0, 0, 1], [1, 1, 1]]

    # Add Blinker to board at position (100, 10)
    board[100:103, 10:13] = [[1, 1, 1]]

    # Add Beacon to board at position (100, 100)
    board[100:102, 100:102] = [[1, 1], [1, 0]]
    board[102:104, 102:104] = [[0, 1], [1, 1]]

    # Save initial state
    plt.imshow(board, cmap='gray')
    plt.savefig(f'output/init.png')
    # start timing
    start = time()

    # Make 100 ticks while saving the results as animation using matplotlib
    for i in range(10):
        start_tick = time()
        board.tick()
        print(f'Tick {i} done! in {time() - start_tick}s')
        # Check if Glider returned to original position

        start_save = time()
        plt.imshow(board, cmap='gray')
        plt.savefig(f'output/{i:03}.png')
        print(f'Saved {i}.png in {time() - start_save}s')

    # end timing
    end = time()

    # Save all images as gif
    files = glob('output/*.png')
    out = 'output/game_of_life.gif'
    images = [Image.open(img) for img in files]
    images[0].save('output/game_of_life.gif', save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)


    print(f'Done in {end - start}s!')