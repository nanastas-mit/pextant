from .geoshapely import GeoPolygon, GeoPoint, UTM, LAT_LONG, Cartesian
import numpy as np
from skimage.draw import circle

# TODO: use skimage.draw.circle instead
def filled_grid_circle(radius):
    rr, cc = circle(radius-1, radius-1, radius)
    return np.array([rr.flatten(), cc.flatten()])

def filled_circle_old(ROW_COL, center, radius):
    """

    :param ROW_COL:
    :type ROW_COL: Cartesian
    :param center:
    :param radius:
    :return:
    """
    XY = ROW_COL.reverse()
    resolution = ROW_COL.resolution
    keepout = center.buffer(radius*resolution)
    bounds = GeoPolygon(UTM(center), *np.array(keepout.bounds).reshape([2, 2]).transpose()).to(XY)

    # generate bounding box mesh
    range1 = lambda start, end: list(range(start, end + 1))
    xrang, yrang = range1(*bounds[0]), range1(*bounds[1][::-1])
    xx, yy = np.meshgrid(xrang, yrang)

    boxelts = GeoPolygon(XY, xx.flatten(), yy.flatten()) #we need a shapely object to use the contains function
    elts_in_circle = [elt.to(ROW_COL) for elt in boxelts if keepout.contains(elt) or keepout.touches(elt)]
    elts_in_circle_clean = np.array(elts_in_circle).transpose()
    return elts_in_circle_clean

if __name__ == '__main__':
    origin = GeoPoint(LAT_LONG, 43.461621, -113.572019)
    ROW_COL = Cartesian(origin, 0.5, reverse=True)
    center = GeoPoint(ROW_COL, 10, 20)
    filled_circle(ROW_COL, center, 5)