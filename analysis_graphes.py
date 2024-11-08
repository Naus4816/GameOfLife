import matplotlib.pyplot as plt
import numpy as np
import time

class GameAnalysis:
    """
    A class to analyze and visualize the progression of the Game of Life.
    """
    def __init__(self, board):
        self.board = board
        self.alive_counts = []
        self.tick_times = []

    def count_alive_cells(self):
        """
        Compte le nbres de cellules vivantes dans le board 
        """
        alive_count = np.sum(self.board)
        self.alive_counts.append(alive_count)
        return alive_count

    def track_tick_time(self, start_time, end_time):
        """
    Le temps de calcul pour chaque itération 
        """
        tick_time = end_time - start_time
        self.tick_times.append(tick_time)
        return tick_time

    def plot_alive_cells(self):
        """
       Graphes représentant le nbres de cellules vivantes  à travers le temps
        """
        plt.figure()
        plt.plot(self.alive_counts, label="Alive Cells")
        plt.xlabel("Tick")
        plt.ylabel("Number of Alive Cells")
        plt.title("Evolution of Alive Cells Over Time")
        plt.legend()
        plt.show()

    def plot_tick_times(self):
        """
        Graphes représentant le temps de calcul pour chaque itération 
        """
        plt.figure()
        plt.plot(self.tick_times, label="Tick Time (s)")
        plt.xlabel("Tick")
        plt.ylabel("Time (s)")
        plt.title("Computation Time per Tick")
        plt.legend()
        plt.show()

    def reset_tracking(self):
        """
        ResRéinitialises les listes et graphes de suivies pour une nouvelle simulation
        """
        self.alive_counts = []
        self.tick_times = []
