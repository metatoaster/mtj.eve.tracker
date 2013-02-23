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

        # id is automatically assigned
        self.assertEqual(tower.id, 1)

        self.assertEqual(self.backend.getTowerIds(), [1])
        self.assertEqual(self.backend.getTower(1), tower)

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

        self.assertEqual(tower.getTimeRemaining(1326850000), 9200)

    def test_2000_reinstantiate(self):
        self.backend._conn.execute('insert into tower values '
            '(1, 1000001, 12235, 30004608, 40291202, 4, 1325376000, '
            '1306886400, 498125261)')
        self.backend._conn.execute('insert into fuel values '
            '(1, 1, 16275, 300, 1325376000, 7200)')
        self.backend._conn.execute('insert into fuel values '
            '(2, 1, 4247, 30, 1325376000, 12345)')

        self.backend.reinstantiate()

        # no new entries are created
        session = self.backend.session()
        towerq = session.query(sql.Tower)
        fuelq = session.query(sql.Fuel)
        self.assertEqual(towerq.count(), 1)
        self.assertEqual(fuelq.count(), 2)

        # tower properly acquired
        tower = self.backend.getTower(1)
        self.assertEqual(tower.id, 1)
        self.assertEqual(tower.itemID, 1000001)

        # Derived values still assigned.
        self.assertEqual(tower.capacity, 140000)
        self.assertEqual(tower.strontCapacity, 50000)

        # Fuel values assigned
        self.assertEqual(tower.getTimeRemaining(1326850000), 9200)

    def test_2001_reinstantiate(self):
        self.backend._conn.execute('insert into tower values '
            '(1, 1000001, 12235, 30004608, 40291202, 4, 1325376000, '
            '1306886400, 498125261)')
        self.backend._conn.execute('insert into tower values '
            '(2, 1000002, 20066, 30004268, 40270415, 4, 1325376000, '
            '1306942573, 498125261)')

        self.backend._conn.execute('insert into fuel values '
            '(1, 1, 16275, 300, 1325366000, 7200)')
        self.backend._conn.execute('insert into fuel values '
            '(2, 1, 4247, 30, 1325366000, 22340)')

        self.backend._conn.execute('insert into fuel values '
            '(3, 2, 4246, 10, 1325376000, 360)')
        self.backend._conn.execute('insert into fuel values '
            '(4, 2, 16275, 100, 1325376000, 2200)')
        self.backend._conn.execute('insert into fuel values '
            '(5, 2, 24592, 1, 1325376000, 34)')

        self.backend._conn.execute('insert into fuel values '
            '(6, 1, 16275, 300, 1325376000, 7200)')
        self.backend._conn.execute('insert into fuel values '
            '(7, 1, 4247, 30, 1325376000, 12345)')

        self.backend.reinstantiate()

        # Fuel values correctly reassigned for both towers.
        tower1 = self.backend.getTower(1)
        self.assertEqual(tower1.getResources(1325376000), {
            4247: 12345,
            16275: 7200,
        })
        tower2 = self.backend.getTower(2)
        self.assertEqual(tower2.getResources(1325376000), {
            4246: 360,
            16275: 2200,
            24592: 34,
        })

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(SqlBackendTestCase))
    return suite
