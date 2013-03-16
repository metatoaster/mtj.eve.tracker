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

    def test_0000_base_tower(self):
        corp = DummyCorp()
        self.manager.importWithApi(corp)

        self.assertEqual(len(self.backend.towers.items()), 1)

        tower = self.backend.towers[1]
        self.assertEqual(tower.celestialName, u'6VDT-H III - Moon 1')
        self.assertEqual(tower.itemID, 507862)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(DefaultManagerTestCase))
    return suite
