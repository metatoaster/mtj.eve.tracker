from unittest import TestCase, TestSuite, makeSuite

import zope.component

from mtj.eve.tracker.backend import sql
from mtj.eve.tracker.interfaces import ITrackerBackend

from mtj.evedb.tests.base import init_test_db
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
        init_test_db()
        self.backend = zope.component.getUtility(ITrackerBackend)

    def tearDown(self):
        tearDown(self)

    def test_init(self):
        result = list(self.backend._conn.execute('select * from category'))
        self.assertEqual(len(result), 4)

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

        marker = object()
        self.assertEqual(self.backend.getTower(1, default=marker), tower)
        self.assertEqual(self.backend.getTower(2, default=marker), marker)
        self.assertRaises(KeyError, self.backend.getTower, 2)

    def test_0100_fuel(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        fuel = {4247: 12345, 16275: 7200,}
        tower.updateResources(fuel, 1325376000)
        self.assertEqual(tower.getTimeRemaining(1326850000), 5600)

        fuel = {4247: 25000, 16275: 7200,}
        tower.updateResources(fuel, 1325484000)

        fuel_log = self.backend.getFuelLog(1)
        result = list(self.backend._conn.execute('select * from fuel'))
        self.assertEqual(result[0].timestamp, 1325376000)
        self.assertEqual(result[2].timestamp, 1325484000)
        self.assertEqual(result[2].value, 25000)
        self.assertEqual(result[2].fuelTypeID, 4247)


    def test_0200_double_add(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        fuel = {4247: 12345, 16275: 7200,}
        tower.updateResources(fuel, 1325376000)

        dupe = self.backend.addTower(1000001, 12235, 0, 0, 0, 0, 0, 0)
        # if another attempt to add a second tower with the same itemID,
        # ignore the new and return the previously added.
        self.assertEqual(tower, dupe)

        # TODO test for log entries when set is implemented.

    def test_0300_tower_update(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        tower.stateTimestamp = 1325379601
        tower.onlineTimestamp = 1325379601
        tower.state = 3
        self.backend.updateTower(tower)
        self.backend.reinstantiate()
        self.assertEqual(self.backend.getTower(1).stateTimestamp, 1325379601)
        self.assertEqual(len(self.backend.getTowerLog(1)), 1)
        self.assertEqual(self.backend.getTowerLog(1)[0].stateTimestamp,
            1325379601)
        self.assertEqual(self.backend.getTowerLog(1)[0].onlineTimestamp,
            1325379601)
        self.assertEqual(self.backend.getTowerLog(1)[0].state, 3)

    def test_0301_tower_update(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        # this will call updateTower.
        tower.setStateTimestamp(1325379601)
        self.backend.reinstantiate()
        self.assertEqual(self.backend.getTower(1).stateTimestamp, 1325379601)
        self.assertEqual(len(self.backend.getTowerLog(1)), 1)
        self.assertEqual(self.backend.getTowerLog(1)[0].stateTimestamp,
            1325379601)

    def test_0302_tower_update_state_ts_dupe(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        # this will call updateTower.
        tower.setStateTimestamp(1325379601)
        # this one is not logged, same value as previous.
        tower.setStateTimestamp(1325379601)
        # this one will be.
        tower.setStateTimestamp(1325379602)
        self.backend.reinstantiate()
        self.assertEqual(self.backend.getTower(1).stateTimestamp, 1325379602)
        self.assertEqual(len(self.backend.getTowerLog(1)), 2)
        self.assertEqual(self.backend.getTowerLog(1)[0].stateTimestamp,
            1325379601)
        self.assertEqual(self.backend.getTowerLog(1)[1].stateTimestamp,
            1325379602)

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
        tower_logq = session.query(sql.TowerLog)
        self.assertEqual(towerq.count(), 1)
        self.assertEqual(fuelq.count(), 2)
        self.assertEqual(tower_logq.count(), 0)

        # tower properly acquired
        tower = self.backend.getTower(1)
        self.assertEqual(tower.id, 1)
        self.assertEqual(tower.itemID, 1000001)

        # Derived values still assigned.
        self.assertEqual(tower.capacity, 140000)
        self.assertEqual(tower.strontCapacity, 50000)

        # Fuel values assigned
        self.assertEqual(tower.getTimeRemaining(1326850000), 5600)

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

    def test_2002_reinstantiate_null_state_ts(self):
        self.backend._conn.execute('insert into tower values '
            '(1, 1000001, 12235, 30004608, 40291202, 4, 1325376661, '
            '1306886400, 498125261)')
        self.backend._conn.execute('insert into tower values '
            '(2, 1000002, 20066, 30004268, 40270415, 1, null, '
            '1306942573, 498125261)')

        self.backend.reinstantiate()

        tower1 = self.backend.getTower(1)
        self.assertEqual(tower1.stateTimestamp, 1325376661)
        self.assertEqual(tower1.resourcePulse, 661)
        tower2 = self.backend.getTower(2)
        self.assertEqual(tower2.stateTimestamp, None)
        self.assertEqual(tower2.resourcePulse, 0)

    def test_3000_add_audit(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        self.backend.addAudit(tower, "DJ's personal tech moon", 'label', 'DJ',
            1364479379)

        result = list(self.backend._conn.execute('select * from audit'))
        self.assertEqual(result[0], (1, u'tower', 1,
            u"DJ's personal tech moon", u'label', u'DJ', 1364479379))

    def test_3000_api_usage_audit(self):
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {})

        self.backend.logApiUsage(123456, None, 1000000)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123456: (1000000, None, 1),
        })

        self.backend.logApiUsage(123456, 0, 1000020)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123456: (1000000, 1000020, 0),
        })

        self.backend.logApiUsage(123456, None, 2000000)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123456: (2000000, None, 1),
        })

        self.backend.logApiUsage(123456, 2, 2000020)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123456: (2000000, 2000020, 2),
        })

        self.backend.logApiUsage(123456, None, 3000000)
        self.backend.logApiUsage(123456, 0, 3000010)
        # Shouldn't really happen
        self.backend.logApiUsage(123456, 2, 3000011)
        self.backend.logApiUsage(123456, 1, 3000012)
        usage = self.backend.currentApiUsage()
        # Entries without a corresponding open are omitted.
        self.assertEqual(usage, {
            123456: (3000000, 3000010, 0),
        })

        self.backend.logApiUsage(123457, None, 1000000)
        self.backend.logApiUsage(123457, 1, 1000041)
        self.backend.logApiUsage(123457, 3, 1000012)
        self.backend.logApiUsage(123457, 0, 1000060)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123456: (3000000, 3000010, 0),
            123457: (1000000, 1000012, 3),
        })

    def test_3001_api_usage_opens(self):
        self.backend.logApiUsage(123458, None, 1000000)
        self.backend.logApiUsage(123458, None, 2000000)
        self.backend.logApiUsage(123458, None, 3000000)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123458: (3000000, None, 1),
        })

    def test_3002_api_usage_orphan_close(self):
        self.backend.logApiUsage(123459, 0, 3000000)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123459: [3000000, 3000000, 0],
        })

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(SqlBackendTestCase))
    return suite
