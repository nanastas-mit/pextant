import csv
import json
import logging
import re
from pextant.solvers.astarMesh import astarSolver
from pextant.analysis.loadWaypoints import JSONloader
import matplotlib.pyplot as plt
logger = logging.getLogger()

class Pathfinder:
    """
    This class performs the A* path finding algorithm and contains the Cost Functions. Also includes
    capabilities for analysis of a path.

    This class still needs performance testing for maps of larger sizes. I don't believe that
    we will be doing anything extremely computationally intensive though.

    Current cost functions are Time, Distance, and (Metabolic) Energy. It would be useful to be able to
    optimize on other resources like battery power or water sublimated, but those are significantly more
    difficult because they depend on shadowing and was not implemented by Aaron.
    """
    def __init__(self, explorer_model, environmental_model):
        cheating = 1
        self.solver = astarSolver(environmental_model, explorer_model,
                                  optimize_on = 'Energy', heuristic_accelerate = cheating)

    def aStarCompletePath(self, optimize_on, waypoints, returnType="JSON", dh=None, fileName=None ):
        pass

    def completeSearch(self, optimize_on, waypoints, filepath=None ):
        """
        Returns a tuple representing the path and the total cost of the path.
        The path will be a list. All activity points will be duplicated in
        the returned path.

        waypoints is a list of activityPoint objects, in the correct order. fileName is
        used when we would like to write stuff to a file and is currently necessary
        for csv return types.
        """
        segmentsout, rawpoints, items = self.solver.solvemultipoint(waypoints)

        if filepath:
            extension = re.search('^(.+\/[^/]+)\.(\w+)$', filepath).group(2)
        else:
            extension = None

        if extension == "json":
            json.dump(segmentsout.tojson(), filepath)
        elif extension == "csv":
            header = [['isStation', 'x', 'y', 'z', 'distanceMeters', 'energyJoules', 'timeSeconds']]
            rows = header + segmentsout.tocsv()
            with open(filepath, 'wb') as csvfile:
                writer = csv.writer(csvfile)
                for row in rows:
                    writer.writerow(row)
            return rows
        return segmentsout, rawpoints, items

    def completeSearchFromJSON(self, optimize_on, jsonInput, filepath=None, algorithm="A*",
                               numTestPoints=0):
        jloader = JSONloader.from_string(jsonInput)
        waypoints = jloader.get_waypoints()

        #if algorithm == "A*":
        segmentsout,_,_ = self.completeSearch(optimize_on, waypoints, filepath)
        updatedjson = jloader.add_search_sol(segmentsout.list)

        return updatedjson

if __name__ == '__main__':
    from pextant.analysis.loadWaypoints import loadPoints
    from .explorers import Astronaut
    from .EnvironmentalModel import GDALMesh

    hi_low = GDALMesh('maps/HI_lowqual_DEM.tif')
    waypoints = loadPoints('waypoints/HI_13Nov16_MD7_A.json')
    env_model = hi_low.loadSubSection(waypoints.geoEnvelope())
    astronaut = Astronaut(80)
    pathfinder = Pathfinder(astronaut, env_model)
    out = pathfinder.aStarCompletePath('Energy', waypoints)
    print(out)