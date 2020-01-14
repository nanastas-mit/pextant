from pextant.lib.geoshapely import GeoPolygon, LONG_LAT
import numpy as np
import csv

class SEXTANTSolver(object):
    def __init__(self, environmental_model, cost_function, viz):
        self.env_model = environmental_model
        self.cost_function = cost_function
        self.viz = viz
        self.searches = []

    def solve(self, start_point, end_point):
        pass

    def solvemultipoint(self, waypoints):
        search_list = sextantSearchList(waypoints)
        for i in range(len(waypoints) - 1):
            search_result = self.solve(waypoints[i], waypoints[i + 1])
            search_list.append(search_result)
        return search_list, search_list.raw(), search_list.itemssrchd()

class sextantSearchList(object):
    def __init__(self, points):
        self.startpoint = points[0]
        self.endpoint = points[-1]
        self.waypoints = points
        self.list = []
        self.rawpoints = []

    def addresult(self, raw, nodes, coordinates, expanded_items):
        self.list.append(sextantSearch(raw, nodes, coordinates, expanded_items))

    def append(self, sextantsearch):
        self.list.append(sextantsearch)

    def raw(self):
        result = []
        for search in self.list:
            if search == False:
                return None
            result += search.raw
        return np.array(result)

    def coordinates(self):
        result = []
        for search in self.list:
            if type(search) == bool:
                return None
            result += search.coordinates.to(LONG_LAT).transpose().tolist()
        return GeoPolygon(LONG_LAT, *np.array(result).transpose())

    def itemssrchd(self):
        result = []
        for search in self.list:
            if type(search) == bool:
                return None
            result += search.expanded_items
        return np.array(result)

    def tojson(self, save=False):
        return [elt.tojson() for elt in self.list]

    def tocsv(self, filepath=None):
        csvlist = [elt.tocsv() for elt in self.list]
        rows = [['isStation', 'x', 'y', 'z', 'distanceMeters', 'energyJoules', 'timeSeconds']]
        for row in csvlist:
            rows += row
        if filepath:
            with open(filepath, 'wb') as csvfile:
                writer = csv.writer(csvfile)
                for row in rows:
                    writer.writerow(row)
        return csvlist


class sextantSearch(object):
    def __init__(self, raw, nodes, coordinates, expanded_items):
        self.namemap = {
            'time': ['timeList','totalTime'],
            'pathlength': ['distanceList','totalDistance'],
            'energy': ['energyList','totalEnergy']
        }
        #self.searches = []
        self.nodes = nodes
        self.raw = raw
        self.npraw = np.array(raw).transpose()
        self.coordinates = coordinates
        self.expanded_items = expanded_items

    def tojson(self):
        out = {}
        coordinates = self.coordinates.to(LONG_LAT).transpose().tolist()
        out["geometry"] = {
            'type': 'LineString',
            'coordinates': coordinates
        }
        results = {}
        for k, v in list(self.namemap.items()):
            results.update({v[0]:[],v[1]:0})
        for i, mesh_srch_elt in enumerate(self.nodes):
            derived = mesh_srch_elt.derived
            for k, v in list(derived.items()):
                results[self.namemap[k][0]].append(v)
        for k, v in list(self.namemap.items()):
            results[v[1]] = sum(results[v[0]])
        out["derivedInfo"] = results
        return out

    def tocsv(self, coordstype=LONG_LAT):
        sequence = []
        coords = self.coordinates.to(coordstype).transpose().tolist()
        for i, mesh_srch_elt in enumerate(self.nodes):
            if i != 0:
                row_entry = [i==1 or i==len(coords)-1] #True if it's the first or last entry
                row_entry += coords[i] + [mesh_srch_elt.mesh_element.z]
                derived = mesh_srch_elt.derived
                row_entry += [derived['pathlength'], derived['time'], derived['energy']]
                sequence += [row_entry]
        return sequence
