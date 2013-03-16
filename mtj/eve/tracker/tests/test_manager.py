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

    def test_1000_time_keeping_fuel_details(self):
        corp = DummyCorp()
        self.manager.importWithApi(corp)
        tower = self.backend.towers[1]
        server_ts, expire_ts = corp.api.last_timestamps
        state_ts = tower.fuels[4312].timestamp

        # state_ts is in the future.
        self.assertEqual(state_ts, 1362793009)
        self.assertEqual(tower.fuels[4312].value, 4027)
        self.assertEqual(tower.getResources(server_ts)[4312], 4027)
        self.assertEqual(tower.getResources(state_ts)[4312], 4027)
        self.assertEqual(tower.getResources(state_ts + 1)[4312], 4019)
        self.assertEqual(tower.getOfflineTimestamp(), 1364603809)

        corp.starbase_details_index = 1
        self.manager.importWithApi(corp)
        server_ts, expire_ts = corp.api.last_timestamps
        state_ts = tower.stateTimestamp

        # As everything is consistent with previous fuel values, raw
        # value is unchanged.
        self.assertEqual(tower.fuels[4312].value, 4027)

    def test_1001_time_keeping_fuel_details(self):
        corp = DummyCorp()
        corp.starbase_details_index = 1
        self.manager.importWithApi(corp)
        tower = self.backend.towers[1]
        server_ts, expire_ts = corp.api.last_timestamps
        state_ts = tower.fuels[4312].timestamp

        # state_ts in the past.
        self.assertEqual(state_ts, 1362829009)
        self.assertEqual(tower.fuels[4312].value, 3939)
        # TODO verify the uncertainty with regards to stateTimestamp
        # that live in the past, whether it really is the current value
        # as it is now or otherwise.
        self.assertEqual(tower.getResources(server_ts)[4312], 3931)
        self.assertEqual(tower.getResources(state_ts)[4312], 3939)
        self.assertEqual(tower.getResources(state_ts + 1)[4312], 3931)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(DefaultManagerTestCase))
    return suite
