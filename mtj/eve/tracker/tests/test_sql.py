from unittest import TestCase, TestSuite, makeSuite

import zope.component

from mtj.eve.tracker.backend import sql
from mtj.eve.tracker.interfaces import ITrackerBackend

from .base import setUp, tearDown

FUEL_NORMAL = 1
FUEL_REINFORCE = 4

STATE_UNANCHORED = 0
STATE_ANCHORED = 1
STATE_ONLINING = 2
STATE_REINFORCE = 3
STATE_ONLINE = 4


class SqlBackendTestCase(TestCase):
    """
    Testing the SQL backend.
    """

    def setUp(self):
        setUp(self)
        self.backend = zope.component.getUtility(ITrackerBackend)

    def tearDown(self):
        tearDown(self)

    def test_0000_tower(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)

        # derived values correctly set.
        self.assertEqual(tower.capacity, 140000)
        self.assertEqual(tower.strontCapacity, 50000)

        result = list(self.backend._conn.execute('select * from tower'))
        self.assertEqual(result, [(1, 1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)])

    def test_0100_fuel(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        fuel = {4247: 12345, 16275: 7200,}
        tower.updateResources(fuel, 1325376000)

        result = list(self.backend._conn.execute('select * from fuel'))
        self.assertEqual(result, [
            (1, 1, 16275, 300, 1325376000, 7200),
            (2, 1, 4247, 30, 1325376000, 12345),
        ])


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(SqlBackendTestCase))
    return suite
