import time
import numpy as np
from numba import cuda
from PIL import Image, ImageOps
from typing import Callable
from pathlib import Path
from threading import Lock
from render.Components import Graph


class DataTracker:
    """
    DataTracker is a class that tracks the data of the board.
    """
    dataset: Graph.DataSet | None
    value: int | float

    def __init__(self):
        self.dataset = None
        self.value = 0

    def update(self, val: int | float):
        """
        Update the value of the tracker.
        """
        self.value = val
        if self.dataset is not None:
            self.dataset.push(self.value)

    def increase(self, val: int | float):
        """
        Increase the value of the tracker.
        """
        self.update(self.value + val)

    def setDataSet(self, ds: Graph.DataSet):
        """
        Set the dataset of the tracker.
        """
        self.dataset = ds


class Board(np.ndarray):
    """
    Implements the storage and logic of the Game of Life board.
    """
    use_gpu: bool
    image: Image
    new_board: np.ndarray
    background_color: int = 0
    tick_lock: Lock
    trackers: dict[str, DataTracker]

    def __new__(cls, _: bool, random: bool, height: int, width: int):
        width, height = width + 2, height + 2
        if random:
            return np.random.choice([False, True], (height, width), p=[0.5, 0.5]).view(cls)
        else:
            return np.zeros((height, width), dtype=bool).view(cls)

    def __init__(self, try_cuda: bool = True, *args, **kwargs):
        # Create second array to store the next state and be space efficient
        self.new_board = np.zeros_like(self, dtype=bool)
        # Create a lock to make sure the board is not updated while ticking
        self.tick_lock = Lock()

        self.trackers = {k: DataTracker() for k in ['generation', 'time', 'alive', 'births', 'deaths']}

        self.image = None
        self.use_gpu = try_cuda and cuda.is_available()
        if try_cuda and not self.use_gpu:
            print("CUDA is not available, defaulting to CPU instead.")

    def setTrackers(self, **kwargs: Graph.DataSet):
        """
        defines specific the trackers for the board.
        """
        for k, v in kwargs.items():
            if k in self.trackers:
                self.trackers[k].setDataSet(v)
            else:
                print(f'Tracker {k} not found')

    def updateCPU(self):
        """
        Ticks the board to compute next state using cpu (slower but works everywhere).
        """
        for i, j in np.ndindex(self.shape):
            alive_count = self.countAlive(i, j)
            self.new_board[i, j] = alive_count in [2, 3] if self[i, j] else alive_count == 3

        self.trackers['births'].update(int((self.new_board & ~self).sum()))
        self.trackers['deaths'].update(int((~self.new_board & self).sum()))
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
        self.tick_lock.acquire()
        start = time.time()
        if self.use_gpu:  # use cuda if available (determined at init)
            self.new_board[...] = Board.runOnGpu(
                cuda.to_device(self),
                cuda.to_device(self.new_board),
                self.shape,
                Board.updateGpu
            )
            # destroys optimisation on huge grids :(
            self.trackers['births'].update(int((self.new_board & ~self).sum()))
            self.trackers['deaths'].update(int((~self.new_board & self).sum()))
            self[...] = self.new_board
        else:
            self.updateCPU()

        # update the trackers
        self.trackers['alive'].update(self.getAliveCount())
        self.trackers['time'].update(time.time() - start)
        self.trackers['generation'].increase(1)

        self.refresh()
        self.tick_lock.release()

    @staticmethod
    @cuda.jit
    def image(board, gray, width: int, height: int, transparent: bool, bg_r, bg_g, bg_b):
        """
        Converts the board to an Image.
        """
        x, y = cuda.grid(2)
        if 0 < x < width - 1 and 0 < y < height - 1:
            gray[x-1, y-1, 0] = 255 if board[x, y] else bg_r
            gray[x-1, y-1, 1] = 255 if board[x, y] else bg_g
            gray[x-1, y-1, 2] = 255 if board[x, y] else bg_b
            if transparent:
                gray[x-1, y-1, 3] = 255 if board[x, y] else 0

    def getImage(self, is_transparent: bool = False) -> Image:
        """
        Converts the board to an image.
        can be transparent or not.
        """
        if self.image is not None:
            return self.image
        bg = self.background_color

        # first convert the board to a grayscale image
        if self.use_gpu:
            # compute the image values on the GPU
            img_data = Board.runOnGpu(
                cuda.to_device(self),
                cuda.device_array((self.getSize()[1], self.getSize()[0], 4 if is_transparent else 3), dtype=np.uint8),
                self.shape,
                Board.image,
                is_transparent,
                *(bg if isinstance(bg, tuple) else (bg, bg, bg))
            )
            mode = 'RGBA' if is_transparent else 'RGB'
            self.image = Image.fromarray(img_data, mode=mode)
        else:
            img_data = self.astype(np.uint8) * 255
            # set custom background color if single grayscale value
            if not is_transparent and isinstance(bg, int) and bg != 0:
                img_data[img_data == 0] = self.background_color
            # create the grayscale image and crop the borders
            image = Image.fromarray(img_data, mode='L').crop((1, 1, self.shape[1] - 1, self.shape[0] - 1))
            # colorize the image if background is a color
            if not is_transparent and isinstance(bg, tuple):
                self.image = ImageOps.colorize(image, black=bg, white=(255, 255, 255))
            else:
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

    def paste(self, other: 'Board', y: int, x: int):
        """
        Paste another board on top of this one.
        """
        self.tick_lock.acquire()
        self[x + 1:x + other.shape[0] - 1, y + 1:y + other.shape[1] - 1] = other[1:-1, 1:-1]
        self.refresh()
        self.tick_lock.release()

    def getSize(self) -> tuple[int, int]:
        """
        Get the size of the board.
        """
        return self.shape[1] - 2, self.shape[0] - 2

    def getAliveCount(self) -> int:
        """
        Get the amount of alive cells in the board.
        """
        return int(self.sum())

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
    saved_location: Path

    def __new__(cls, src: Path | np.ndarray, _: str, crop: bool = False, __: bool = False):
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
            if crop and len(x) > 0 and len(y) > 0:
                cropped = src[max(min(x) - 1, 0):max(x) + 2, max(min(y) - 1, 0):max(y) + 2]
            else:
                cropped = src
            return cropped.view(cls)

    def __init__(self, src: Path | np.ndarray, name: str, _: bool = False, try_cuda: bool = False):
        super().__init__(try_cuda)
        self.name = name
        self.getImage(True)
        if isinstance(src, Path):
            self.saved_location = src

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Preset):
            return False
        return self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def save(self, path: Path, name: str = None, make_preset: bool = True):
        """
        Save the preset to a file.
        """
        if not path.exists():
            path.mkdir()
        name = name if name is not None else self.name
        ext = '.preset' if make_preset else '.board'
        path = path / f'{name}{ext}'
        print(f'Saving preset to {path}')
        self.tick_lock.acquire()
        np.savetxt(path, self, fmt='%d')
        self.tick_lock.release()

    def delete(self):
        """
        Delete the preset file.
        """
        self.saved_location.unlink()
        del self.saved_location
        print(f'Deleted preset {self.name}')

    def rotate(self):
        """
        Rotate the preset by 90 degrees.
        """
        return Preset(np.rot90(self, k=-1), self.name)

