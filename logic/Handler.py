import threading
from logic.Board import Board
import pygame


class LogicHandler(threading.Thread):
    board: Board | None
    running: bool
    tick_rate: int
    current_tps: float
    paused: threading.Lock

    def __init__(self, tick_rate: int = 10):
        super().__init__()
        self.board = None
        self.running = True
        self.tick_rate = tick_rate
        self.current_tps = 0
        self.paused = threading.Lock()

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            if self.board is None:
                self.pause()
            else:
                self.board.tick()
                clock.tick(self.tick_rate)
                self.current_tps = clock.get_fps()

            # if paused, wait for the release rather than busy waiting
            if self.paused.locked():
                self.current_tps = 0
                self.paused.acquire()
                self.paused.release()

    def setBoard(self, board: Board):
        """
        Set the board to be used by the logic handler.
        """
        if not self.isPaused():
            self.pause()
            self.board = board
            self.resume()
        else:
            resume = self.isPaused() and self.board is None
            self.board = board
            if resume:
                self.resume()

    def resume(self):
        """
        Resume the game by releasing the pause lock.
        """
        self.paused.release()

    def pause(self):
        """
        Pause the game by acquiring the pause lock.
        """
        self.paused.acquire()

    def isPaused(self) -> bool:
        """
        Returns true if lock is blocking runner
        """
        return self.paused.locked()
