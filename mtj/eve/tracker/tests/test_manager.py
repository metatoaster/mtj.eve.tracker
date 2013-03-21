from unittest import TestCase, TestSuite, makeSuite

import zope.component

from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.pos import Tower
from mtj.eve.tracker.manager import DefaultTowerManager

from .base import setUp, tearDown
from .dummyevelink import DummyCorp


class DefaultManagerTestCase(TestCase):
    """
    Unit tests for structures
    """

    def setUp(self):
        setUp(self)
        self.backend = zope.component.getUtility(ITrackerBackend)
        self.manager = DefaultTowerManager()

    def tearDown(self):
        tearDown(self)

    def test_0000_base_tower_manager(self):
        corp = DummyCorp()
        self.manager.importWithApi(corp)
        self.assertEqual(len(self.backend.towers.items()), 1)
        tower = self.backend.towers[1]

        self.assertEqual(tower.celestialName, u'6VDT-H III - Moon 1')
        self.assertEqual(tower.itemID, 507862)

    def test_0010_missing_details(self):
        corp = DummyCorp()
        corp.starbases_index = 1
        self.manager.importWithApi(corp)
        self.assertEqual(len(self.backend.towers.items()), 2)

        # Still imported anyway.
        tower = self.backend.towers[2]
        self.assertEqual(tower.celestialName, u'VFK-IV II - Moon 1')
        self.assertEqual(tower.itemID, 507863)
        # but not receiving fuel values.
        self.assertEqual(len(tower.fuels), 0)

    def test_1000_time_keeping_fuel_details(self):
        corp = DummyCorp()
        self.manager.importWithApi(corp)
        tower = self.backend.towers[1]
        current_time = corp.api.last_timestamps['current_time']
        fuel_ts = tower.fuels[4312].timestamp

        # fuel timestamp and stateTimestamps are in the future.
        self.assertEqual(fuel_ts, 1362793009)
        self.assertEqual(tower.stateTimestamp, 1362793009)

        self.assertEqual(tower.fuels[4312].value, 4027)
        self.assertEqual(tower.getResources(current_time)[4312], 4027)
        self.assertEqual(tower.getResources(fuel_ts)[4312], 4027)
        self.assertEqual(tower.getResources(fuel_ts + 1)[4312], 4019)
        self.assertEqual(tower.getOfflineTimestamp(), 1364603809)

        corp.starbase_details_index = 1
        self.manager.importWithApi(corp)

        # As everything is consistent with previous fuel values, raw
        # value is unchanged.
        self.assertEqual(tower.fuels[4312].value, 4027)
        # Likewise with the stateTimestamp, no updated fuel values, no
        # changes.
        self.assertEqual(tower.stateTimestamp, 1362793009)

    def test_1001_time_keeping_fuel_details(self):
        corp = DummyCorp()
        corp.starbase_details_index = 1
        self.manager.importWithApi(corp)
        tower = self.backend.towers[1]
        current_time = corp.api.last_timestamps['current_time']

        fuel_ts = tower.fuels[4312].timestamp

        # the stateTimestamp is bumped as it's a new one.
        self.assertEqual(tower.stateTimestamp, 1362829009)
        self.assertEqual(tower.fuels[4312].value, 3939)
        # it's accurate for the current_time.
        self.assertEqual(tower.getResources(current_time)[4312], 3939)
        self.assertEqual(tower.getResources(fuel_ts)[4312], 3939)
        self.assertEqual(tower.getResources(fuel_ts + 1)[4312], 3931)

        # verify persistence by reinstantiating all objects.
        self.backend.reinstantiate()
        self.assertEqual(self.backend.towers[1].stateTimestamp, 1362829009)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(DefaultManagerTestCase))
    return suite
