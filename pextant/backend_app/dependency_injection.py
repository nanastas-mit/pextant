import os
import pextant.backend_app.events.event_definitions as event_definitions
from os import path as path
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.EnvironmentalModel import load_legacy, GDALMesh, load_obstacle_map
from pextant.explorers import Astronaut
from pextant.lib.geoshapely import GeoPoint
from pextant.solvers.astarMesh import ExplorerCost
from pextant_cpp import PathFinder


class FeatureBroker:
    """class for pairing up functionality with constructs"""

    '''=======================================
    SINGLETON INTERFACE
    ======================================='''
    @staticmethod
    def instance():
        if not FeatureBroker._instance:
            FeatureBroker()
        return FeatureBroker._instance
    _instance = None

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, allow_replace=False):

        # singleton check/initialization
        if FeatureBroker._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            FeatureBroker._instance = self

        self.providers = {}
        self.allow_replace = allow_replace

    def provide(self, feature, provider, *args, **kwargs):
        if not self.allow_replace:
            assert feature not in self.providers, "Duplicate feature: %r" % feature
        if callable(provider):
            def call():
                return provider(*args, **kwargs)
        else:
            def call():
                return provider
        self.providers[feature] = call

    def __getitem__(self, feature):
        try:
            provider = self.providers[feature]
        except KeyError:
            raise KeyError("Unknown feature named %r" % feature)
        return provider()


#
# Some basic assertions to test the suitability of injected features
#

def no_assertion(obj): return True


def is_instance_of(*classes):
    def test(obj): return isinstance(obj, classes)
    return test


def has_attributes(*attributes):
    def test(obj):
        for each in attributes:
            if not hasattr(obj, each):
                return False
        return True
    return test


def has_methods(*methods):
    def test(obj):
        for each in methods:
            try:
                attr = getattr(obj, each)
            except AttributeError:
                return False
            if not callable(attr):
                return False
        return True
    return test


class RequiredFeature(object):
    """An attribute descriptor to "declare" required features"""

    def __init__(self, feature, assertion=no_assertion):
        self.feature = feature
        self.assertion = assertion

    def __get__(self, obj, T):
        return self.result  # <-- will request the feature upon first call

    def __getattr__(self, name):
        assert name == 'result', "Unexpected attribute request other then 'result'"
        self.result = self.request()
        return self.result

    def request(self):
        obj = FeatureBroker.instance()[self.feature]
        assert self.assertion(obj), \
            "The value %r of %r does not match the specified criteria" \
            % (obj, self.feature)
        return obj

