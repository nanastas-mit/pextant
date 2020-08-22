import math
import numpy as np
import numpy.matlib as matlib
from scipy.interpolate import NearestNDInterpolator, RegularGridInterpolator
from scipy.ndimage.interpolation import zoom
from skimage.draw import circle
from pextant.explorers import Astronaut

class GeoMesh(object):

    def __init__(self, nw_geo_point, dataset, planet='Earth',
                 parent_mesh=None, xoff=0, yoff=0):
        self.dataset = dataset
        self.data = dataset.data_container
        self.x_size = dataset.x_size
        self.y_size = dataset.y_size
        self.shape = dataset.shape
        self.size = dataset.size
        self.resolution = dataset.resolution

        self.local_coordinates = XY(nw_geo_point, self.resolution)
        self.nw_geo_point = nw_geo_point
        self.se_geo_point = GeoPoint(Cartesian(nw_geo_point, self.resolution), self.x_size, self.y_size)
        self.planet = planet if parent_mesh == None else parent_mesh.planet

        # data points that make it relative to a parent mesh, but not really currently in use
        self.parent_mesh = parent_mesh
        self.xoff = xoff
        self.yoff = yoff

    @classmethod
    def from_parent(cls, parent, **kwargs):
        return cls(parent.nw_geo_point, parent.dataset, parent_mesh=parent.parent_mesh,
                   xoff=parent.xoff, yoff=parent.yoff, **kwargs)

    def localpoint(self, geopoint):
        return geopoint.to(self.local_coordinates)

    def __str__(self):
        return 'height: %s \nwidth: %s \nresolution: %s \nnw corner: %s' % \
              (self.y_size, self.x_size, self.resolution, str(self.nw_geo_point))

class Dataset(object):
    '''
    This is a wrapper that gives gdal datasets a shape property, similar to numpy arrays
    '''
    def __init__(self, data, row_size, col_size, resolution):
        self.y_size = row_size
        self.x_size = col_size
        self.shape = (row_size, col_size)
        self.size = row_size*col_size
        self.data_container = data
        self.resolution = resolution

    def __str__(self):
        return 'height: %s \nwidth: %s ' % \
              (self.y_size, self.x_size)

class InterpolatingDataset(Dataset):
    def __init__(self, data, row_size, col_size, resolution=1.):
        super(InterpolatingDataset, self).__init__(data, row_size, col_size, resolution)
        self.interpolator = self._grid_interpolator_initializer()

    @classmethod
    def from_np(cls, numpy_array, resolution=1.):
        y_size, x_size = numpy_array.shape
        return cls(numpy_array, y_size, x_size, resolution=resolution)

    # should be overwritten if needed, which is why it's its own function outside of __init__
    def _grid_interpolator_initializer(self):
        x_axis = np.arange(self.x_size)
        y_axis = np.arange(self.y_size)
        return RegularGridInterpolator((y_axis, x_axis), self.data_container)

    def downsample(self, resolution):
        return InterpolatingDataset.from_np(zoom(self.data_container, self.resolution/resolution), resolution=resolution)

    # interpolation should be defined by children classes
    def get_datapoint(self, localpoint):
        return self.interpolator(localpoint)


class NpDataset(np.ndarray):
    # Wraps around Interpolating Dataset aswell
    def __new__(cls, input_array, resolution=1.0):
        # Input array is an already formed ndarray instance
        # We first cast to be our class type
        obj = np.asarray(input_array).view(cls)
        # add the new attribute to the created instance
        obj.resolution = resolution
        row_size,col_size = obj.shape
        obj.y_size = row_size
        obj.x_size = col_size
        obj.data_container = input_array
        # Finally, we must return the newly created object:
        return obj

    def downsample(self, resolution):
        factor = self.resolution / float(resolution)
        downsampled =zoom(self.data_container, factor)
        return NpDataset(downsampled, resolution)

    def subsection(self, xoff, yoff, xsize, ysize, resolution=None):
        res = 1.0 if resolution == None else resolution/self.resolution
        #print(xoff, yoff, xsize, ysize, res)
        x2, y2 = int((xoff + xsize) / res), int((yoff + ysize) / res)
        xoff, yoff = int(xoff/res), int(yoff/res)
        #print(xoff,yoff,x2,y2)
        npdataset = self.downsample(resolution) if resolution != None else self
        sub = npdataset[yoff:y2, xoff:x2]
        return sub

    def interpolator(self):
        x_axis = np.arange(self.x_size)
        y_axis = np.arange(self.y_size)
        return RegularGridInterpolator((y_axis, x_axis), self.data_container)

    # interpolation should be defined by children classes
    def get_datapoint(self, localpoint):
        return self.interpolator()(localpoint)

    def __array_finalize__(self, obj):
        # see InfoArray.__array_finalize__ for comments
        self.resolution =  getattr(obj, "resolution", None)
        self.y_size, self.x_size = self.shape
        self.data_container = self.view(np.ndarray)

    def __repr__(self):
        return self.data_container.__repr__()

    def __str__(self):
        return self.data_container.__str__()

class NearestInterpolatorDataset(InterpolatingDataset):
    def __init__(self, *arg, **kwargs):
        super(NearestInterpolatorDataset, self).__init__(*arg, **kwargs)

    def _grid_interpolator_initializer(self):
        x_axis = np.arange(self.x_size)
        y_axis = np.arange(self.y_size)
        return NearestNDInterpolator((y_axis, x_axis), self.data_container)

def coordinate_transform(func):
    def decorated(self, point):
        return func(self, self.convert_coordinates(point))
    return decorated

class EnvironmentalModel(GeoMesh):
    """
    This class ultimately represents an elevation map + all of the traversable spots on it.
    """
    def __init__(self, nw_geo_point, dataset, planet='Earth',
                 parent_mesh=None, xoff=0, yoff=0, maxSlope=35, kernel_size=3, kernel_type="square",
                 cached=False):
        super(EnvironmentalModel, self).__init__(nw_geo_point, dataset, planet,
                 parent_mesh, xoff, yoff)
        self.maxSlope = maxSlope
        self.cached = cached
        self.kernel_type = kernel_type
        self.kernel_size = kernel_size
        self.slopes = []
        self.obstacles = []  # obstacles is a list with boolean values for non-passable squares
        self.passable = []
        self.special_obstacles = set()  # a list of coordinates of obstacles are not identified by the slope
        self.setSlopes()
        #TODO: make max slope a once only argument (right now it gets passed along several times)
        self.maxSlopeObstacle(self.maxSlope)

    def obstacle_mask(self, maxslope = None):
        if maxslope is None:
            obstacles = self.obstacles
        else:
            obstacles = self.slopes > maxslope
        return np.ma.masked_array(np.ones_like(self.data), np.logical_not(obstacles))

    def set_obstacle_map(self, obstacle_map, state=True):

        self.obstacles[obstacle_map] = state
        self.passable = np.logical_not(self.obstacles)

    def set_circular_obstacle(self, center, radius, state=True):

        euclidean_dist_sq = self.get_euclidean_distance_sq_to_point(center)
        added_mask = euclidean_dist_sq < radius * radius
        self.set_obstacle_map(added_mask, state)

    def set_obstacle_list(self, geo_point_list, state=True):

        obstacle_map = np.full((self.y_size, self.x_size), False, dtype=bool)

        # go through all obstacle coordinate
        for geo_point in geo_point_list:

            # convert to appropriate coordinates
            elt = self.getMeshElement(geo_point)
            mesh_coordinate = elt.mesh_coordinate
            coordinate_row = mesh_coordinate[0]
            coordinate_col = mesh_coordinate[1]
            obstacle_map[coordinate_row, coordinate_col] = True

        self.set_obstacle_map(obstacle_map, state)

    def get_xy_distance_grids_to_point(self, point):

        point_x = point[0]
        point_y = point[1]

        # value of cell in grid 'x' is x-coord, value of cell in grid 'y' is y-coord
        r = self.resolution
        y, x = r*np.mgrid[0:self.y_size, 0:self.x_size]

        # x and y *offsets from goal* of every point in grid
        return np.abs(y - point_y), np.abs(x - point_x)

    def get_euclidean_distance_sq_to_point(self, point):

        # x and y *offsets from goal* of every point in grid
        delta_y, delta_x = self.get_xy_distance_grids_to_point(point)

        # return the squared distance (no sqrt)
        return np.square(delta_x) + np.square(delta_y)

    def get_euclidean_distance_to_point(self, point):

        return np.sqrt(self.get_euclidean_distance_sq_to_point(point))

    def get_oct_grid_distance_to_point(self, point):

        # x and y *offsets from goal* of every point in grid
        delta_y, delta_x = self.get_xy_distance_grids_to_point(point)

        # number of (resolution-scaled) diagonal steps you are able to take to reach goal
        h_diagonal = np.minimum(delta_y, delta_x)

        # with no diagonal walking, number of x-axis or y-axis steps (resolution-scaled) needed to take to reach goal
        h_straight = delta_y + delta_x

        # total distance to goal if you can only travel left-right, up-down, or along diagonals
        #   Patel 2010. See page 49 of Aaron's thesis
        return (np.sqrt(2)-2) * h_diagonal + h_straight

    def convert_coordinates(self, geo_coordinates): pass

    def setSlopes(self): pass

    def getSlope(self, mesh_coordinates):
        return self.slopes[mesh_coordinates]

    def getElevations(self, mesh_coordinates): pass

    def getGravity(self):
        if self.planet == 'Earth':
            return 9.81
        elif self.planet == 'Moon':
            return 1.622

    def maxSlopeObstacle(self, maxSlope):
        self.obstacles.extend(np.where(self.slopes > maxSlope)[0])

    @coordinate_transform
    def getMeshElement(self, geo_coordinates):
        return self._getMeshElement(geo_coordinates)

    def _getMeshElement(self, mesh_coordinates): pass

    def getMeshEltNeighbours(self, mesh_element):
        return self._getNeighbours(mesh_element.state)

    @coordinate_transform
    def get_neighbours(self, geo_coordinates):
        return self._getNeighbours(geo_coordinates)

    def _getNeighbours(self, mesh_coordinates): pass

    # obstacle functions
    @coordinate_transform
    def eraseObstacle(self, geo_coordinates):
        self.obstacles.remove(geo_coordinates)

    @coordinate_transform
    def setObstacle(self, geo_coordinates):
        self.obstacles.append(geo_coordinates)

    def setRadialKeepOutZone(self, center, radius): pass

    @coordinate_transform
    def in_bounds(self, geo_coordinates):
        return self._inBounds(geo_coordinates)

    def _inBounds(self, mesh_coordinates): pass

    @coordinate_transform
    def has_data(self, geo_coordinates):
        return self._hasdata(geo_coordinates)

    def _hasdata(self, mesh_coordinates): pass

    @coordinate_transform
    def isPassable(self, geo_coordinates):
        # determines if coordinates can be passed through
        return self._isPassable(geo_coordinates)

    def _isPassable(self, mesh_coordinates):
        return self._hasdata(mesh_coordinates) and mesh_coordinates not in self.obstacles

class SearchKernel(object):
    def __init__(self, kernelrange = 3, type="square"):
        searchvector = list(range(-math.floor(kernelrange / 2), math.floor(kernelrange / 2) + 1))
        col_off = matlib.repmat(searchvector, len(searchvector), 1)
        row_off = np.transpose(col_off)
        col_off_clean = np.delete(col_off.flatten(), (kernelrange**2 - 1)/2)
        row_off_clean = np.delete(row_off.flatten(), (kernelrange**2 - 1) / 2)
        self.length = kernelrange**2
        self.col_off = col_off_clean
        self.row_off = row_off_clean
        self.kernelrange = kernelrange
        self.type = type
        self.typemap = dict(square=self.get_square_kernel, circular=self.get_circular_kernel)
        self.kernel = np.array([row_off_clean, col_off_clean]).transpose()

    def getKernel(self):
        return self.typemap[self.type]()

    def get_square_kernel(self):
        return self.kernel

    def get_circular_kernel(self):
        kernel = np.array(circle(0, 0, int((self.kernelrange-1)/2+1))).transpose()
        center_removed = np.delete(kernel, np.where(np.logical_and(kernel[:, 0] == 0, kernel[:, 1] == 0))[0][0], 0)
        return center_removed

if __name__ == '__main__':
    from pextant.settings import *
    from scipy.stats import multivariate_normal
    from pextant.lib.geoshapely import *
    nrows = 40
    ncols = 40
    rows, cols = np.mgrid[0:nrows, 0:ncols]
    rv = multivariate_normal([nrows / 2, ncols / 2], [[nrows, 0], [0, ncols]])
    pos = np.empty(rows.shape + (2,))
    pos[:, :, 0] = rows
    pos[:, :, 1] = cols
    raster = 1800 * rv.pdf(pos)
    nw_geo_point = GeoPoint(LAT_LONG, 0, 0)
    from pextant.EnvironmentalModel import GridMeshModel
    from pextant.mesh.triangularmesh import grid_to_tri, TriMeshModel

    environment = GridMeshModel(nw_geo_point, NpDataset(raster), cached=True)
    explorer = Astronaut(80)
    solver = astarSolver(environment, explorer)
    sol = solver.solve((0, 0), (20, 20))