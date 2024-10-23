import numpy as np
from time import time
from numba import cuda
from glob import glob
from PIL import Image
from typing import Callable
from pathlib import Path


class Board(np.ndarray):
    """
    Implements the storage and logic of the Game of Life board.
    """
    use_gpu: bool
    image: Image
    new_board: np.ndarray
    background_color: int = 0

    def __new__(cls, _: bool, random: bool, height: int, width: int):
        width, height = width + 2, height + 2
        if random:
            return np.random.choice([False, True], (height, width), p=[0.5, 0.5]).view(cls)
        else:
            return np.zeros((height, width), dtype=bool).view(cls)

    def __init__(self, try_cuda: bool = True, *args, **kwargs):
        # Create second array to store the next state and be space efficient
        self.new_board = np.zeros_like(self, dtype=bool)

        self.image = None
        self.use_gpu = try_cuda and cuda.is_available()
        if try_cuda and not self.use_gpu:
            print("CUDA is not available, defaulting to CPU instead.")

    def updateCPU(self):
        """
        Ticks the board to compute next state using cpu (slower but works everywhere).
        """
        for i, j in np.ndindex(self.shape):
            alive_count = self.countAlive(i, j)
            self.new_board[i, j] = alive_count in [2, 3] if self[i, j] else alive_count == 3
        self[...] = self.new_board

    def countAlive(self, i: int, j: int) -> bool:
        """
        Get the amount of alive neighbors of a cell.
        """
        return self[i - 1:i + 2, j - 1:j + 2].sum() - self[i, j]

    @staticmethod
    @cuda.jit
    def updateGpu(board, new_board, width: int, height: int):
        """
        Ticks part of the board to compute next state using cuda.
        """
        x, y = cuda.grid(2)
        if 0 < x < width - 1 and 0 < y < height - 1:
            alive_count = 0
            for i in range(-1, 2):
                for j in range(-1, 2):
                    alive_count += board[x + i, y + j]
            alive_count -= board[x, y]
            new_board[x, y] = alive_count in [2, 3] if board[x, y] else alive_count == 3

    def tick(self):
        """
        Ticks the board to compute next state.
        """
        if self.use_gpu:  # use cuda if available (determined at init)
            self[...] = Board.runOnGpu(
                cuda.to_device(self),
                cuda.to_device(self.new_board),
                self.shape,
                Board.updateGpu
            )
        else:
            self.updateCPU()
        self.refresh()

    @staticmethod
    @cuda.jit
    def grayscale(board, gray, width: int, height: int, transparent: bool = False, bg_color: int = 0):
        """
        Converts the board to a grayscale image.
        """
        x, y = cuda.grid(2)
        if 0 < x < width - 1 and 0 < y < height - 1:
            value = 255 if board[x, y] else 33
            for i in range(3):
                gray[x-1, y-1, i] = value
            if transparent:
                gray[x-1, y-1, 3] = 255 if board[x, y] else 0

    def getImage(self, is_transparent: bool = False) -> Image:
        """
        Converts the board to an image.
        can be transparent or not.
        """
        if self.image is not None:
            return self.image

        # first convert the board to a grayscale image
        if self.use_gpu:
            # compute the image values on the GPU
            img_data = Board.runOnGpu(
                cuda.to_device(self),
                cuda.device_array((*self.getSize(), 4 if is_transparent else 3), dtype=np.uint8),
                self.shape,
                Board.grayscale,
                is_transparent,
                self.background_color
            )
            mode = 'RGBA' if is_transparent else 'RGB'
            self.image = Image.fromarray(img_data, mode=mode)
        else:
            img_data = self.astype(np.uint8) * 255
            # set custom background color
            if not is_transparent and self.background_color != 0:
                img_data[img_data == 0] = self.background_color
            # create the grayscale image and crop the borders
            image = Image.fromarray(img_data, mode='L').crop((1, 1, self.shape[0] - 1, self.shape[1] - 1))
            self.image = image.convert('RGB')
            # add alpha channel if needed just by using the same image as alpha
            if is_transparent:
                self.image.putalpha(image)

        # return the image
        return self.image

    @staticmethod
    def runOnGpu(src, dest, shape: tuple[int, ...], func: Callable, *args) -> np.ndarray:
        """
        Runs a function on the GPU.
        """
        threads_per_blocks = (16, 16)
        blocks_per_grid = (
            (shape[0] + threads_per_blocks[0] - 1) // threads_per_blocks[0],
            (shape[1] + threads_per_blocks[1] - 1) // threads_per_blocks[1]
        )
        func[blocks_per_grid, threads_per_blocks](src, dest, *shape, *args)
        return dest.copy_to_host()

    def getSize(self) -> tuple[int, int]:
        """
        Get the size of the board.
        """
        return self.shape[1] - 2, self.shape[0] - 2

    def getAliveCount(self) -> int:
        """
        Get the amount of alive cells in the board.
        """
        return self.sum()

    def refresh(self):
        """
        empty the image cache
        """
        self.image = None


class Preset(Board):
    """
    Stores a preset for the Game of Life. Which is a smaller board with a specific pattern.
    """
    name: str

    def __new__(cls, src: Path | Board, _: str):
        """
        Create a new preset from a file or a board.
        :param src: path to the file or the board to crop
        :param _: name of the preset
        """
        # Load the preset from a file.
        if isinstance(src, Path):
            return np.loadtxt(src, dtype=bool).view(cls)
        # Crop the given board to fit its content that is alive.
        else:
            x, y = np.where(src)
            cropped = src[max(min(x) - 1, 0):max(x) + 2, max(min(y) - 1, 0):max(y) + 2]
            return cropped.view(cls)

    def __init__(self, _: Path | Board, name: str):
        super().__init__(False)
        self.name = name
        self.getImage(True)

    def save(self, path: Path):
        """
        Save the preset to a file.
        """
        if not path.exists():
            path.mkdir()
        path = path / f'{self.name}.preset'
        print(f'Saving preset to {path}')
        np.savetxt(path, self, fmt='%d')
