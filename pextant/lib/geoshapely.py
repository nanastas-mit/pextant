import pyproj
import numpy as np
from shapely.geometry import Point, LineString
import shapely.coords


class GeoType(object):
    def __init__(self, name, values, proj_param, proj_transform_order):
        self.name = name
        self.values = values
        self.proj_param = proj_param
        self.proj_transform_order = [values.index(parameter) for parameter in proj_transform_order]

    def get_proj(self):
        # add additional parameters here
        proj_param = self.proj_param
        proj_param["datum"] = "WGS84"
        return pyproj.Proj(**proj_param)

    # baseline is identity
    def to_utm(self, geo_point):
        return self

    def transform(self, geo_point, to_geo_type, conversion_type=None):
        args = self.getargs(geo_point)
        if self.proj_param == to_geo_type.proj_param:
            out = args
        else:
            p_from = self.get_proj()
            p_to = to_geo_type.get_proj()
            out = pyproj.transform(p_from, p_to, args[0], args[1])
        array_out = np.array(out)  # just in case its not a numpy already, and will simplify calcs later
        post_array = to_geo_type.post_process(array_out)
        if conversion_type is not None:
            return conversion_type(post_array)
        else:
            return post_array

    def post_process(self, transformed_points):
        return self.reorder(transformed_points)

    def reorder(self, elements):
        array_elements = np.array(elements)
        if len(array_elements.shape) <= 1:
            post_out = array_elements[self.proj_transform_order]
        else:
            post_out = array_elements[self.proj_transform_order, :]
        return post_out

    def getargs(self, geo_point):
        parameters = self.reorder(self.values)
        return geo_point[parameters[0]], geo_point[parameters[1]]


class UTM(GeoType):

    SYSTEM_NAME = 'utm'

    def __init__(self, zone_inter):
        zone = zone_inter if not isinstance(zone_inter, GeoPoint) else zone_inter.utm_reference.proj_param["zone"]
        super(UTM, self).__init__(UTM.SYSTEM_NAME, ["easting", "northing"], {"proj": "utm", "zone": zone},
                                  ["easting", "northing"])


class LatLon(GeoType):

    SYSTEM_NAME = 'latlon'

    def __init__(self, reverse=False):
        if reverse:
            order = ["longitude", "latitude"]
        else:
            order = ["latitude", "longitude"]

        super(LatLon, self).__init__(LatLon.SYSTEM_NAME, order, {"proj": "latlong"},
                                     ["longitude", "latitude"])

    def to_utm(self, geo_point):
        np_longitude = np.array(geo_point["longitude"])
        zones = (((np_longitude + 180).round() / 6.0) % 60 + 1).astype(int)
        # TODO: check if this is needed:
        #UTMzdlChars = "CDEFGHJKLMNPQRSTUVWXX"
        #if -80 <= lat and lat <= 84:
        #    zone_letter = UTMzdlChars[((np_latitude + 80) / 8).astype(int)]
        zone = zones[0] if isinstance(zones, np.ndarray) else zones
        return UTM(zone)

# doesn't round of
class XY(GeoType):
    def __init__(self, origin, resolution, reverse=False):
        if reverse:
            order = ["y", "x"]
        else:
            order = ["x", "y"]

        self.zone = origin.utm_reference.proj_param["zone"]
        super(XY, self).__init__("coord", order, {"proj": "utm", "zone": self.zone}, ["x", "y"])
        # doing conversion early on will save use from redoing it later, we don't expect our origin to change too much
        self.origin_easting, self.origin_northing = origin.x, origin.y
        self.resolution = resolution

        self.origin = origin # needed for reversal
        self.reversed = reverse # needed for reversal too

    def reverse(self):
        return Cartesian(self.origin, self.resolution, not self.reversed)

    def to_utm(self, geo_point):
        return UTM(self.zone)

    def getargs(self, geo_points):
        # next line should ideally be super.getargs, but we overwrite the fx so not sure if possible
        x, y = geo_points["x"], geo_points["y"]
        delta_easting, delta_northing = np.array([x, y]) * self.resolution
        return self.origin_easting + delta_easting, self.origin_northing - delta_northing

    def post_process(self, transformed_points):
        points_easting, points_northing = transformed_points
        delta_easting, delta_northing = points_easting - self.origin_easting, self.origin_northing - points_northing
        coords = np.array([delta_easting, delta_northing]) / self.resolution
        return self.reorder(coords)

class Cartesian(GeoType):

    SYSTEM_NAME = 'coord'

    def __init__(self, origin, resolution, reverse=False):
        if reverse:
            order = ["y", "x"]
        else:
            order = ["x", "y"]

        self.zone = origin.utm_reference.proj_param["zone"]
        super(Cartesian, self).__init__(Cartesian.SYSTEM_NAME, order, {"proj": "utm", "zone": self.zone}, ["x", "y"])
        # doing conversion early on will save use from redoing it later, we don't expect our origin to change too much
        self.origin_easting, self.origin_northing = origin.x, origin.y
        self.resolution = resolution
        self.origin = origin # needed for reversal
        self.reversed = reverse # needed for reversal too

    def reverse(self):
        return Cartesian(self.origin, self.resolution, not self.reversed)

    def to_utm(self, geo_point):
        return UTM(self.zone)

    def getargs(self, geo_points):
        # next line should ideally be super.getargs, but we overwrite the fx so not sure if possible
        x, y = geo_points["x"], geo_points["y"]
        delta_easting, delta_northing = np.array([x, y]) * self.resolution
        return self.origin_easting + delta_easting, self.origin_northing - delta_northing

    def post_process(self, transformed_points):
        points_easting, points_northing = transformed_points
        delta_easting, delta_northing = points_easting - self.origin_easting, self.origin_northing - points_northing
        coords = np.array([np.round(delta_easting / self.resolution,6),
                           np.round(delta_northing / self.resolution,6)]).astype(int)
        return self.reorder(coords)

class Cartesian2(object):
    def __init__(self, origin=None, resolution=1, reverse=False, integer=True):
        if reverse:
            order = ["y", "x"]
        else:
            order = ["x", "y"]

        self.name = "nongeocoord"
        self.values = order
        proj_transform_order = ["x", "y"]
        self.proj_transform_order = [order.index(parameter) for parameter in proj_transform_order]
        # doing conversion early on will save use from redoing it later, we don't expect our origin to change too much
        self.origin_easting, self.origin_northing = (origin.x, origin.y) if origin != None else (0, 0)
        self.resolution = resolution
        self.origin = origin # needed for reversal
        self.reversed = reverse # needed for reversal too
        self.integer = integer

    def reverse(self):
        return Cartesian(self.origin, self.resolution, not self.reversed)

    def reorder(self, elements):
        array_elements = np.array(elements)
        if len(array_elements.shape) <= 1:
            post_out = array_elements[self.proj_transform_order]
        else:
            post_out = array_elements[self.proj_transform_order, :]
        return post_out

    def to_utm(self, geo_point):
        return  Cartesian2()

    def getargs(self, geo_points):
        # next line should ideally be super.getargs, but we overwrite the fx so not sure if possible
        x, y = geo_points["x"], geo_points["y"]
        delta_easting, delta_northing = np.array([x, y]) * self.resolution
        return self.origin_easting + delta_easting, self.origin_northing + delta_northing

    def transform(self, geo_point, to_geo_type, conversion_type=None):
        args = self.getargs(geo_point)
        if self.name == to_geo_type.name:
            array_out = args
            post_array = to_geo_type.post_process(array_out)
            if conversion_type is not None:
                return conversion_type(post_array)
            else:
                return post_array
        else:
            return None

    def post_process(self, transformed_points):
        points_easting, points_northing = transformed_points
        delta_easting, delta_northing = points_easting - self.origin_easting, points_northing-self.origin_northing
        coords = np.array([np.round(delta_easting / self.resolution,6),
                           np.round(delta_northing / self.resolution,6)])
        if self.integer:
            coords = coords.astype(int)
        return self.reorder(coords)

class GeoObject(object):
    def __init__(self, geo_type, x, y):
        self.original_reference = geo_type
        self.data = dict((geo_type.values[idx], val) for idx, val in enumerate([x, y]))

        if geo_type.name == "utm":
            self.easting = x
            self.northing = y
            self.utm_reference = geo_type
        else:
            self.utm_reference = geo_type.to_utm(self.data)
            self.easting, self.northing = geo_type.transform(self.data, self.utm_reference)

    def to(self, other_reference, conversion_type=None):
        # assuming other_reference is not of type utm
        if isinstance(other_reference, UTM):
            return np.array([self.easting, self.northing])
        else:
            return self.original_reference.transform(self.data, other_reference, conversion_type)

    def eastingnorthing(self):
        return self.easting, self.northing


class GeoPoint(GeoObject, Point):
    def __init__(self, geo_type, x, y):
        GeoObject.__init__(self, geo_type, x, y)
        Point.__init__(self, self.easting, self.northing)


class GeoPolygon(GeoObject, LineString):
    def __init__(self, firstarg, *args):
        # TODO: not sure if np.array is needed, check
        if isinstance(firstarg, list):
            x = [p.x for p in firstarg]
            y = [p.y for p in firstarg]
            geo_type = firstarg[0].utm_reference
        elif isinstance(args[0], shapely.coords.CoordinateSequence):
            # TODO: check that there is indeed an optional argument supplied
            x, y = np.array(args[0]).transpose()
            geo_type = firstarg
        else:
            x, y = args
            geo_type = firstarg
        GeoObject.__init__(self, geo_type, x, y)
        xytuple = list(map(tuple, np.array([self.easting, self.northing]).transpose()))
        # print xytuple
        LineString.__init__(self, xytuple)

    def geoEnvelope(self):
        env_easting, env_northing = np.array(self.envelope.bounds).reshape((2, 2)).transpose()
        upper_left = GeoPoint(self.utm_reference, env_easting[0], env_northing[1])
        lower_right = GeoPoint(self.utm_reference, env_easting[1], env_northing[0])
        return GeoEnvelope(upper_left, lower_right)

    def __getitem__(self, index):
        return GeoPoint(self.utm_reference, self.easting[index], self.northing[index])

    def __len__(self):
        return len(self.coords)

class GeoEnvelope(GeoPolygon):
    def __init__(self, upper_left, lower_right):
        # assum both coordinates are in the same quadrant, choose upper_left by default
        self.upper_left = upper_left
        self.lower_right = lower_right
        GeoPolygon.__init__(self, [upper_left, lower_right])

    def addMargin(self, resolution, margin):
        # margin is in "units" of cartesian_geo_type, aka if 1m resolution, the one unit of margin
        # corresponds to one meter of margin
        upper_left_easting = self.upper_left.easting - margin*resolution
        upper_left_northing = self.upper_left.northing + margin*resolution
        lower_right_easting = self.lower_right.easting + margin * resolution
        lower_right_northing = self.lower_right.northing - margin * resolution
        new_upper_left = GeoPoint(self.utm_reference, upper_left_easting, upper_left_northing)
        new_lower_right =GeoPoint(self.utm_reference, lower_right_easting, lower_right_northing)
        return GeoEnvelope(new_upper_left, new_lower_right)

    def getBounds(self):
        return self.upper_left, self.lower_right


LAT_LONG = LatLon()
LONG_LAT = LatLon(True)
