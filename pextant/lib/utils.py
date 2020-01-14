import numpy as np
import pandas as pd
from .geoshapely import GeoPolygon, LONG_LAT

def gridpoints_list(array):
    X, Y = np.mgrid[0:array.shape[0], 0:array.shape[1]]
    positions = np.column_stack((X.flatten(), Y.flatten()))
    return positions

def loadcsv(name, wp):
    test = pd.read_csv(name)
    return GeoPolygon(LONG_LAT, *np.vstack([wp[0].to(LONG_LAT), test[['x','y']].values]).transpose())