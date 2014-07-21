from unittest import TestCase, TestSuite, makeSuite

import zope.component

from mtj.eve.tracker.interfaces import IAPIHelper, ITrackerBackend
from mtj.eve.tracker.pos import Tower
from mtj.eve.tracker.manager import APIKeyManager, DefaultTowerManager

from .base import setUp, tearDown
from .dummyevelink import DummyCorp


class APIKeyManagerTestCase(TestCase):
    """
    Unit tests for the key manager.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_0000_base(self):
        keyman = APIKeyManager()
        keyman.api_keys = {
            '1': 'test1',
            '2': 'test2',
            '3': 'test3',
        }

        results = keyman.getAllWith(DummyCorp)
        self.assertEqual(len(results), 3)
        self.assertTrue(isinstance(results[0], DummyCorp))
        self.assertEqual(results[0].api.api_key, ('1', 'test1'))
        self.assertEqual(results[2].api.api_key, ('2', 'test2'))


class DefaultManagerTestCase(TestCase):
    """
    Unit tests for default tower manager
    """

    def setUp(self):
        setUp(self)
        self.backend = zope.component.getUtility(ITrackerBackend)
        self.manager = DefaultTowerManager()
        self.helper = zope.component.getUtility(IAPIHelper)

    def tearDown(self):
        tearDown(self)

    def test_0000_base_tower_manager(self):
        corp = DummyCorp()
        self.manager.importWithCorp(corp)
        self.assertEqual(len(self.backend.getTowerIds()), 1)
        tower = self.backend.getTower(1)

        self.assertEqual(tower.celestialName, u'6VDT-H III - Moon 1')
        self.assertEqual(tower.itemID, 507862)

        tower_apis = self.backend.getTowerApis()
        self.assertEqual(len(tower_apis), 1)
        self.assertEqual(tower_apis[0].api_key, 1)
        self.assertEqual(tower_apis[0].currentTime, 1362792986)

    def test_0010_missing_details(self):
        corp = DummyCorp()
        corp.starbases_index = 1
        self.manager.importWithCorp(corp)
        self.assertEqual(len(self.backend.getTowerIds()), 2)

        # Still imported anyway.
        tower = self.backend.getTower(2)
        self.assertEqual(tower.celestialName, u'VFK-IV II - Moon 1')
        self.assertEqual(tower.itemID, 507863)
        # but not receiving fuel values.
        self.assertEqual(len(tower.fuels), 0)

        tower_apis = self.backend.getTowerApis()
        # Only details are counted.
        self.assertEqual(len(tower_apis), 1)
        self.assertEqual(tower_apis[0].currentTime, 1362792986)

    def test_0100_states(self):
        corp = DummyCorp()
        self.manager.importWithCorp(corp)

        corp.starbase_details_index = 1
        self.manager.importWithCorp(corp)

        # no updates
        self.assertEqual(len(self.backend.getTowerLog(1)), 0)

        tower_apis = self.backend.getTowerApis()
        self.assertEqual(tower_apis[0].currentTime, 1362829863)

        corp.starbases_index = 2
        corp.starbase_details_index = 2
        self.manager.importWithCorp(corp)

        # two updates (currently, until state + stateTimestamp is fully
        # unified)
        tower_log_1 = self.backend.getTowerLog(1)
        self.assertEqual(len(tower_log_1), 1)
        self.assertEqual(tower_log_1[0].stateTimestamp, 1362901009)
        self.assertEqual(tower_log_1[0].state, 3)

        fuel_log_1 = sorted([(f.timestamp, f.fuelTypeID, f.value, f.delta)
            for f in self.backend.getFuelLog(1)])
        self.assertEqual(fuel_log_1, [
            (1362793009, 4312, 4027, 8),
            (1362793009, 16275, 2250, 75),
            (1362901009, 4312, 3939, 8),
            (1362901009, 16275, 0, 75),
        ])

        tower_apis = self.backend.getTowerApis()
        self.assertEqual(len(tower_apis), 2)
        self.assertEqual(tower_apis[0].currentTime, 1362865863)
        self.assertEqual(tower_apis[1].currentTime, 1362865863)

    def test_1000_time_keeping_fuel_details(self):
        corp = DummyCorp()
        self.manager.importWithCorp(corp)
        tower = self.backend.getTower(1)
        # derived from test data.
        current_time = 1362792986
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
        self.manager.importWithCorp(corp)

        # As everything is consistent with previous fuel values, raw
        # value is unchanged.
        self.assertEqual(tower.fuels[4312].value, 4027)
        # Likewise with the stateTimestamp, no updated fuel values, no
        # changes.
        self.assertEqual(tower.stateTimestamp, 1362793009)

    def test_1001_time_keeping_fuel_details(self):
        corp = DummyCorp()
        corp.starbase_details_index = 1
        self.manager.importWithCorp(corp)
        tower = self.backend.getTower(1)
        # derived from test data.
        current_time = 1362792986

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
        self.assertEqual(self.backend.getTower(1).stateTimestamp, 1362829009)

    def test_1100_sov_change(self):
        corp = DummyCorp()
        self.manager.importWithCorp(corp)
        tower = self.backend.getTower(1)
        self.assertEqual(tower.fuels[4312].delta, 8)
        self.assertEqual(tower.fuels[16275].delta, 75)

        # didn't want that sov anyway.
        self.helper.sov_index = 1
        self.manager.importWithCorp(corp)
        # This normally would have deviated from calculated value, so
        # this updated normally before.
        self.assertEqual(tower.fuels[4312].delta, 10)
        # However, strontium, being static, nope.
        self.assertEqual(tower.fuels[16275].delta, 100)

    def test_1500_resolve_multi_location(self):
        # when towers once anchored at a location then unanchored, then
        # reanchored at new location without being repackaged.

        corp = DummyCorp()
        corp.starbases_index = 2
        corp.starbase_details_index = 2
        self.manager.importWithCorp(corp)
        self.assertEqual(len(self.backend.getTowerIds()), 2)

        corp.starbases_index = 3
        corp.starbase_details_index = 3
        self.manager.importWithCorp(corp)
        self.assertEqual(len(self.backend.getTowerIds()), 3)

        tower2 = self.backend.getTower(2)
        self.assertEqual(tower2.fuels[16275].value, 1000)
        self.assertEqual(tower2.fuels[4051].value, 3939)

        tower3 = self.backend.getTower(3)
        self.assertEqual(tower3.fuels[16275].value, 1000)
        self.assertEqual(tower3.fuels[4051].value, 6000)

    def test_1501_unanchored(self):
        # when tower becomes unanchored.

        corp = DummyCorp()
        corp.starbases_index = 3
        corp.starbase_details_index = 3
        self.manager.importWithCorp(corp)
        tower_apis = self.backend.getTowerApis()
        self.assertEqual(tower_apis[0].currentTime, 1363225863)
        self.assertEqual(tower_apis[1].currentTime, 1363225863)

        corp.starbases_index = 4
        corp.starbase_details_index = 4
        self.manager.importWithCorp(corp)
        tower_apis = self.backend.getTowerApis()
        self.assertEqual(tower_apis[0].currentTime, 1363260409)
        # This has failed to update.
        self.assertEqual(tower_apis[1].currentTime, 1363225863)

    # XXX create test case for fudge factor, where API fuel values did
    # not decrement as expected.


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(APIKeyManagerTestCase))
    suite.addTest(makeSuite(DefaultManagerTestCase))
    return suite
