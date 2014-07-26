from unittest import TestCase, TestSuite, makeSuite

import zope.interface

from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.backend import monitor

from .base import setUp, tearDown


@zope.interface.implementer(ITrackerBackend)
class DummyBackend(object):

    def __init__(self):
        self.towers = []

    def updateTower(self, tower):
        self.towers.append([(k, v) for k, v in sorted(tower.__dict__.items())
            if '_' not in k])


class DummyTower(object):

    def __init__(self):
        self.a = 0
        self.b = 'b'

    def unloggedIncrement(self):
        self.a = self.a + 1

    @monitor.towerUpdates('a')
    def loggedIncrement(self):
        self.a = self.a + 1

    @monitor.towerUpdates('missing')
    def setMissing(self, value):
        self.missing = value

    @monitor.towerUpdates('a', 'b')
    def setAB(self, a, b):
        self.a, self.b = a, b

    @monitor.towerUpdates('b')
    def setABnologA(self, a, b):
        self.a, self.b = a, b

    @monitor.towerUpdates('a', 'b', 'missing')
    def setAll(self, a, b, missing):
        self.a, self.b, self.missing = a, b, missing


class MonitorTestCase(TestCase):
    """
    Unit tests for structures
    """

    def setUp(self):
        self.backend = DummyBackend()
        setUp(self, backend=self.backend)

    def tearDown(self):
        tearDown(self)

    def test_0000_tower_updates_none(self):
        tower = DummyTower()
        tower.unloggedIncrement()
        self.assertEqual(self.backend.towers, [])

    def test_0001_tower_updates_monitored(self):
        tower = DummyTower()
        tower.unloggedIncrement()
        tower.loggedIncrement()
        self.assertEqual(self.backend.towers, [
            [('a', 2), ('b', 'b')],
        ])

    def test_0002_tower_updates_multiple(self):
        tower = DummyTower()
        tower.loggedIncrement()
        tower.loggedIncrement()
        self.assertEqual(self.backend.towers, [
            [('a', 1), ('b', 'b')],
            [('a', 2), ('b', 'b')],
        ])

    def test_0003_tower_updates_sneaky(self):
        tower = DummyTower()
        tower.unloggedIncrement()
        tower.unloggedIncrement()
        tower.setAB(2, 'b')
        self.assertEqual(self.backend.towers, [])

    def test_0004_tower_updates_multiple(self):
        tower = DummyTower()
        tower.unloggedIncrement()
        tower.unloggedIncrement()
        tower.setAB(2, 'c')
        self.assertEqual(self.backend.towers, [
            [('a', 2), ('b', 'c')],
        ])

    def test_0005_tower_updates_only_monitored(self):
        tower = DummyTower()
        tower.unloggedIncrement()
        tower.unloggedIncrement()
        tower.setABnologA(2, 'b')
        self.assertEqual(self.backend.towers, [])
        tower.setABnologA(3, 'b')
        self.assertEqual(self.backend.towers, [])
        tower.setABnologA(2, 'c')
        self.assertEqual(self.backend.towers, [
            [('a', 2), ('b', 'c')],
        ])

    def test_0100_tower_updates_missing(self):
        tower = DummyTower()
        tower.setMissing('Not missing')
        self.assertEqual(self.backend.towers, [
            [('a', 0), ('b', 'b'), ('missing', 'Not missing')],
        ])

    def test_0101_tower_updates_missing_assumed_none(self):
        tower = DummyTower()
        tower.setMissing(None)
        self.assertEqual(self.backend.towers, [])


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(MonitorTestCase))
    return suite
