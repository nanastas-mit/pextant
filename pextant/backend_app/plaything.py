import numpy as np

def main():

    y: np.ndarray = np.arange(35).reshape(5, 7)
    mask = np.zeros(y.shape)
    coords = [[0, 0], [2, 1], [4, 2]]
    for coord in coords:
        mask[coord[0], coord[1]] = 1
    y[mask] = 5
    #b = y[np.array([0,2,4]), np.array([0,1,2])]
    print("yay")

if __name__ == '__main__':

    main()