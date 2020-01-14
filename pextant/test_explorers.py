import unittest
import numpy as np
import matplotlib.pyplot as plt
from .explorers import Astronaut

class TestEnergyCostFunctions(unittest.TestCase):
    def _generate_slopes(self):
        slopes = np.radians(np.linspace(-25,25,101))
        return slopes

    def test_slope_energy_cost(self):
        slopes_rad = self._generate_slopes()
        slopes_deg = np.degrees(slopes_rad)
        explorer = Astronaut(80)
        dl = 1 # path length
        g = 9.81 # gravity

        total_cost_quick, v = explorer.energy_expenditure(dl, slopes_rad, g)
        plt.plot(slopes_deg, total_cost_quick)
        plt.show()
        print('hi')


if __name__ == '__main__':
    unittest.main()