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
        self.assertEqual(len(result), 5)

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

        result = list(self.backend._conn.execute('select * from fuel'))
        self.assertEqual(result[0].timestamp, 1325376000)
        self.assertEqual(result[2].timestamp, 1325484000)
        self.assertEqual(result[2].value, 25000)
        self.assertEqual(result[2].fuelTypeID, 4247)

        fuel_log = self.backend.getFuelLog(1)
        self.assertEqual(len(fuel_log), 3)

        fuel_log = self.backend.getFuelLog(1, 1)
        self.assertEqual(len(fuel_log), 1)
        self.assertEqual(fuel_log[0].timestamp, 1325484000)

    def test_0200_double_add(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        fuel = {4247: 12345, 16275: 7200,}
        tower.updateResources(fuel, 1325376000)

        # only the itemID and moonID are checked
        dupe = self.backend.addTower(1000001, 12235, 0, 40291202, 3, 0, 0, 0)
        # if another attempt to add a second tower with the same itemID,
        # ignore the new and return the previously added.
        self.assertEqual(tower, dupe)

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
        log = self.backend.getTowerLog(1)
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0].stateTimestamp, 1325379602)
        self.assertEqual(log[1].stateTimestamp, 1325379601)

        log = self.backend.getTowerLog(1, 1)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0].stateTimestamp, 1325379602)

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
            '(1, 1000001, 12235, 30004608, 40291202, 1, 1325376661, '
            'null, 498125261)')
        self.backend._conn.execute('insert into tower values '
            '(2, 1000002, 20066, 30004268, 40270415, 1, null, '
            'null, 498125261)')

        self.backend._conn.execute('insert into fuel values '
            '(1, 1, 16275, 300, 1325376000, 7200)')
        self.backend._conn.execute('insert into fuel values '
            '(2, 1, 4247, 30, 1325376000, 12345)')

        self.backend.reinstantiate()

        tower1 = self.backend.getTower(1)
        self.assertEqual(tower1.stateTimestamp, 1325376661)
        self.assertEqual(tower1.resourcePulse, 661)
        tower2 = self.backend.getTower(2)
        self.assertEqual(tower2.stateTimestamp, None)
        self.assertEqual(tower2.resourcePulse, 0)

        tower1 = self.backend.getTower(1)
        self.assertEqual(tower1.getResources(1325376000), {
            4247: 12345,
            16275: 7200,
        })
        self.assertEqual(tower1.getResources(1325376662), {
            4247: 12345,
            16275: 7200,
        })

    def test_3000_add_audit(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        self.backend.addAudit(tower, "DJ's personal tech moon", 'label', 'DJ',
            1364479379)

        result = list(self.backend._conn.execute('select * from audit'))
        self.assertEqual(result[0], (1, u'tower', 1,
            u"DJ's personal tech moon", u'label', u'DJ', 1364479379))

    def test_3001_get_auditable(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        auditable = self.backend.getAuditable('tower', 1)
        self.assertEqual(tower.id, auditable.id)
        self.assertEqual(tower.locationID, auditable.locationID)

    def test_3002_add_audit_get_auditable(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        self.backend.addAudit(('tower', '2'), "DJ's personal tech moon",
            'label', 'DJ', 1364479379)

        result = list(self.backend._conn.execute('select * from audit'))
        self.assertEqual(len(result), 0)

        self.backend.addAudit(('tower', '1'), "DJ's personal tech moon",
            'label', 'DJ', 1364479379)
        result = list(self.backend._conn.execute('select * from audit'))
        self.assertEqual(result[0], (1, u'tower', 1,
            u"DJ's personal tech moon", u'label', u'DJ', 1364479379))

    def test_3003_get_audit_entries(self):
        tower = self.backend.addTower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)
        tower = self.backend.addTower(1000001, 12235, 30004268, 40270415, 4,
            1325376000, 1306886400, 498125261)
        tower = self.backend.addTower(1000001, 12235, 30004268, 40270327, 4,
            1325376000, 1306886400, 498125261)
        self.backend.addAudit(('tower', '1'), "DJ's personal tech moon",
            'DJ', 'label', 1369479379)
        self.backend.addAudit(('tower', '1'), "This should be nationalized.",
            'admin', 'notice', 1369479472)
        self.backend.addAudit(('tower', '1'), "Maybe in a month?",
            'DJ', 'notice', 1369479476)
        self.backend.addAudit(('tower', '1'), "No.",
            'admin', 'notice', 1369479482)
        self.backend.addAudit(('tower', '2'), "DJ's personal tech moon",
            'DJ', 'label', 1369479449)
        self.backend.addAudit(('tower', '2'), "DJ's personal neo moon",
            'DJ', 'label', 1369479596)
        self.backend.addAudit(('tower', '3'), "Thrice is a charm.",
            'DJ', 'notice', 1369479476)

        audits = self.backend.getAuditForTable('tower')
        self.assertEqual(audits[1][0].reason, "DJ's personal tech moon")
        self.assertEqual(audits[1][0].category_name, 'label')
        self.assertEqual(audits[1][1].reason, "No.")
        self.assertEqual(audits[1][1].category_name, 'notice')
        self.assertEqual(audits[2][0].reason, "DJ's personal neo moon")
        self.assertEqual(audits[2][0].category_name, 'label')

        audits = self.backend.getAuditForTable('tower', category='label')
        self.assertEqual(audits[1][0].reason, "DJ's personal tech moon")
        self.assertEqual(audits[2][0].reason, "DJ's personal neo moon")

        audits = self.backend.getAuditForTable('tower', category='notice')
        self.assertEqual(len(audits), 2)
        self.assertEqual(len(audits[1]), 1)
        self.assertEqual(audits[1][0].reason, "No.")
        self.assertEqual(audits[3][0].reason, "Thrice is a charm.")

        audits = self.backend.getAuditEntry('tower', 1)
        self.assertEqual(audits['label'][0].reason, "DJ's personal tech moon")
        self.assertEqual(audits['notice'][0].reason, "No.")
        self.assertEqual(audits['notice'][1].reason, "Maybe in a month?")
        self.assertEqual(audits['notice'][2].user, "admin")

        self.backend.addAudit(('tower', '2'), "DJ :getout:",
            'admin', 'label', 1369479597)
        audits = self.backend.getAuditForTable('tower')
        self.assertEqual(audits[2][0].reason, "DJ :getout:")

    def test_3100_get_audit_categories_default(self):
        categories = self.backend.getAuditCategories('tower')
        names = [c.name for c in categories]
        self.assertEqual(names, [u'comment', u'label', u'notice'])

    def test_3000_api_usage_audit(self):
        self.assertEqual(self.backend.currentApiUsage(), {})
        self.assertEqual(self.backend.completedApiUsage(), {})

        m = self.backend.beginApiUsage(123456, 1000000)
        self.assertEqual(self.backend.currentApiUsage(), {
            123456: (1000000, None, -1),
        })
        self.assertEqual(self.backend.completedApiUsage(), {})

        self.backend.endApiUsage(m, 0, 1000020)
        self.assertEqual(self.backend.currentApiUsage(), {
            123456: (1000000, 1000020, 0),
        })

        m = self.backend.beginApiUsage(123456, 2000000)
        self.assertEqual(self.backend.currentApiUsage(), {
            123456: (2000000, None, -1),
        })
        # completed usage still unchanged.
        self.assertEqual(self.backend.completedApiUsage(), {
            123456: (1000000, 1000020, 0),
        })

        n = self.backend.beginApiUsage(123457, 1000000)
        self.assertEqual(self.backend.completedApiUsage(), {
            123456: (1000000, 1000020, 0),
        })
        self.backend.endApiUsage(n, 1, 1000041)
        self.assertEqual(self.backend.currentApiUsage(), {
            123456: (2000000, None, -1),
            123457: (1000000, 1000041, 1),
        })
        self.assertEqual(self.backend.completedApiUsage(), {
            123456: (1000000, 1000020, 0),
        })

        self.backend.endApiUsage(m, 3, 3000041)
        usage = self.backend.currentApiUsage()
        self.assertEqual(usage, {
            123456: (2000000, 3000041, 3),
            123457: (1000000, 1000041, 1),
        })

        n = self.backend.beginApiUsage(123457, 1000000)
        self.backend.endApiUsage(n, 0, 1000081)
        self.assertEqual(self.backend.completedApiUsage(), {
            123456: (1000000, 1000020, 0),
            123457: (1000000, 1000081, 0),
        })

        # getting the earliest entry will always return the minimum
        # entry.
        self.assertEqual(self.backend.currentApiUsage(timestamp=100000), {
            123456: (1000000, 1000020, 0),
            123457: (1000000, 1000041, 1),
        })
        self.assertEqual(self.backend.currentApiUsage(timestamp=1000000), {
            123456: (1000000, 1000020, 0),
            123457: (1000000, 1000041, 1),
        })

        # minimum entry always returned.
        self.assertEqual(self.backend.completedApiUsage(timestamp=100000), {
            123456: (1000000, 1000020, 0),
            123457: (1000000, 1000081, 0),
        })
        self.assertEqual(self.backend.completedApiUsage(timestamp=1000000), {
            123456: (1000000, 1000020, 0),
            123457: (1000000, 1000081, 0),
        })

    def test_3001_api_usage_alt(self):
        m = self.backend.beginApiUsage(123458, 1000000)
        self.backend.endApiUsage(m, None, 1000001)
        m = self.backend.beginApiUsage(123458, 2000000)
        self.backend.endApiUsage(m, 0, 1000001)
        m = self.backend.beginApiUsage(123458, 3000000)
        self.assertEqual(self.backend.currentApiUsage(), {
            123458: (3000000, None, -1),
        })
        # heh backwards in time, but that's expected due to GIGO
        self.assertEqual(self.backend.completedApiUsage(), {
            123458: (2000000, 1000001, 0),
        })

    def test_3002_api_usage_opens(self):
        self.backend.beginApiUsage(123458, 1000000)
        self.backend.beginApiUsage(123458, 2000000)
        self.backend.beginApiUsage(123458, 3000000)
        self.assertEqual(self.backend.currentApiUsage(), {
            123458: (3000000, None, -1),
        })

    def test_3003_api_usage_orphan_close(self):
        # Not really, but the data is mangled in an unexpected way.
        m = self.backend.beginApiUsage(123459, 3000000)
        m.start_ts = None
        self.backend.endApiUsage(m, 0, 3000001)
        # Not sure if this is really empty, but apparently it is?
        # Shouldn't happen under normal circumstances anyway.
        self.assertEqual(self.backend.currentApiUsage(), {})

    def test_4000_tower_api_usage(self):
        m = self.backend.beginApiUsage(123456, 10000)
        self.backend.setTowerApi(1, 123456, 10000, 10000)
        self.backend.setTowerApi(2, 123456, 10001, 10001)
        self.backend.setTowerApi(3, 123456, 10001, 10001)
        self.backend.setTowerApi(4, 123456, 10003, 10003)
        self.backend.endApiUsage(m, 0, 10004)
        self.assertEqual(self.backend.getApiTowerIds(), {
            1: (10000, 0), 2: (10001, 0), 3: (10001, 0), 4: (10003, 0)})

        m = self.backend.beginApiUsage(123456, 20000)
        self.backend.setTowerApi(1, 123456, 20000, 20000)
        self.backend.setTowerApi(4, 123456, 20001, 20001)
        # update has not been marked as completed.
        self.assertEqual(self.backend.getApiTowerIds(), {
            1: (20000, 0), 2: (10001, 0), 3: (10001, 0), 4: (20001, 0)})
        self.backend.endApiUsage(m, 0, 20004)
        self.assertEqual(self.backend.getApiTowerIds(), {
            1: (20000, 0), 4: (20001, 0)})

        # Extra keys overlapping shouldn't cause problems.
        m = self.backend.beginApiUsage(123457, 30000)
        self.backend.setTowerApi(1, 123457, 30000, 30000)
        self.backend.setTowerApi(2, 123457, 30001, 30001)
        self.backend.setTowerApi(5, 123457, 29957, 30002)
        self.backend.endApiUsage(m, 0, 30004)
        # This is still stuck a number of seconds behind but it's of
        # a different API key...
        self.assertEqual(self.backend.getApiTowerIds(), {
            # note, API timestamp
            1: (30000, 0), 2: (30001, 0), 4: (20001, 0), 5: (29957, 0)}) 

        m = self.backend.beginApiUsage(123456, 40000)
        self.backend.setTowerApi(1, 123456, 40000, 40000)
        self.backend.endApiUsage(m, 0, 40000)
        # ... until that API key is fetched to verify that this is gone.
        self.assertEqual(self.backend.getApiTowerIds(), {
            # note, API timestamp
            1: (40000, 0), 2: (30001, 0), 5: (29957, 0)})

        m = self.backend.beginApiUsage(123457, 50000)
        self.backend.setTowerApi(1, 123457, 50000, 50000)
        self.backend.setTowerApi(2, 123457, 50001, 50001)
        # error happened as result code not 0
        self.backend.endApiUsage(m, 1, 50004)
        # the time stuck is from the previous success call.
        self.assertEqual(self.backend.getApiTowerIds(), {
            1: (50000, 0), 2: (50001, 0), 5: (29957, 0)})

        # getting specific data back in time should work.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(3, 12345),
            {3: (10001, 0)})
        # fast-forwarding to some point in future where this is gone.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(3, 54321),
            {})

    def test_4001_tower_api_usage_errors(self):
        m = self.backend.beginApiUsage(123456, 10000)
        self.backend.setTowerApi(1, 123456, 10000, 10000)
        self.backend.setTowerApi(2, 123456, 10001, 10001, api_error=True)
        self.backend.setTowerApi(3, 123456, 10001, 10001)
        self.backend.setTowerApi(4, 123456, 10003, 10003)
        self.backend.endApiUsage(m, 0, 10004)
        self.assertEqual(self.backend.getApiTowerIds(), {
            1: (10000, 0), 2: (10001, 1), 3: (10001, 0), 4: (10003, 0)})

        m = self.backend.beginApiUsage(123456, 20000)
        self.backend.setTowerApi(1, 123456, 20000, 20000)
        self.backend.setTowerApi(2, 123456, 20001, 20001, api_error=True)
        self.backend.setTowerApi(3, 123456, 20001, 20001, api_error=True)
        self.backend.setTowerApi(4, 123456, 20003, 20003)
        self.backend.endApiUsage(m, 0, 20004)
        self.assertEqual(self.backend.getApiTowerIds(), {
            1: (20000, 0), 2: (20001, 2), 3: (20001, 1), 4: (20003, 0)})

        # all is well now.
        m = self.backend.beginApiUsage(123456, 30000)
        self.backend.setTowerApi(1, 123456, 30000, 30000)
        self.backend.setTowerApi(2, 123456, 30001, 30001)
        self.backend.setTowerApi(3, 123456, 30001, 30001)
        self.backend.setTowerApi(4, 123456, 30003, 30003)
        self.backend.endApiUsage(m, 0, 30004)
        self.assertEqual(self.backend.getApiTowerIds(), {
            1: (30000, 0), 2: (30001, 0), 3: (30001, 0), 4: (30003, 0)})

        # Should all return the same result.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(3, 12345),
            {3: (30001, 0)})
        self.assertEqual(self.backend.getApiTowerIdTimestamp(3, 23456),
            {3: (30001, 0)})
        self.assertEqual(self.backend.getApiTowerIdTimestamp(3, 34567),
            {3: (30001, 0)})

    def test_4002_tower_api_usage_errors(self):
        m = self.backend.beginApiUsage(123456, 10000)
        self.backend.setTowerApi(1, 123456, 10000, 10000)
        self.backend.setTowerApi(2, 123456, 10001, 10001)
        self.backend.setTowerApi(3, 123456, 10002, 10002)
        self.backend.endApiUsage(m, 0, 10002)

        self.assertEqual(self.backend.getApiTowerIdTimestamp(1, 12345),
            {1: (10000, 0)})

        m = self.backend.beginApiUsage(123456, 20000)
        self.backend.setTowerApi(1, 123456, 20000, 20000)
        self.backend.setTowerApi(2, 123456, 20001, 20001, api_error=True)
        self.backend.setTowerApi(3, 123456, 20002, 20002)
        self.backend.endApiUsage(m, 0, 20002)

        # get this from a much later time, but we only have up to 20004.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(2, 34567),
            {2: (20001, 1)})

        m = self.backend.beginApiUsage(123456, 30000)
        self.backend.setTowerApi(1, 123456, 30000, 30000)
        self.backend.setTowerApi(3, 123456, 30001, 30001)
        self.backend.setTowerApi(4, 123456, 30001, 30001)
        self.backend.endApiUsage(m, 0, 30001)

        # Well, this got retroactively removed in relation to the same
        # run as above.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(2, 34567), {})
        # However, checking tower 3 using really early time will show
        # that as alive.  No big deal if we actually check the tower
        # from that time because it wouldn't have existed.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(4, 12345),
            {4: (30001, 0)})

        # Problem.  A director quit, keys had to be remade.
        m = self.backend.beginApiUsage(234567, 40000)
        self.backend.setTowerApi(1, 234567, 40000, 40000)
        self.backend.setTowerApi(4, 234567, 40001, 40001)
        self.backend.endApiUsage(m, 0, 40001)

        # Getting the most recent one shouldn't be a problem.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(1, 45678),
            {1: (40000, 0)})

        # Getting a historic one should be no issue
        self.assertEqual(self.backend.getApiTowerIdTimestamp(1, 12345),
            {1: (40000, 0)})
        # Again, even if this tower wasn't alive before, it will act as
        # one, but no data should exist for it.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(4, 12345),
            {4: (40001, 0)})

        # However, since the director quit at the same moment the key
        # used for its personal tower went down, this will not be
        # correctly reported.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(3, 45678),
            {3: (30001, 0)})

        # only remedy for this is to emulate an begin and end the usage
        # and have no towers reported.
        m = self.backend.beginApiUsage(123456, 40000)
        self.backend.endApiUsage(m, 0, 40001)
        # Should be reported as inactive now.
        self.assertEqual(self.backend.getApiTowerIdTimestamp(3, 45678), {})

    def test_4100_api_add(self):
        self.backend.addApiKey('1234', 'secretvcode')
        self.backend.addApiKey('2468', 'anothervcode')
        keys = self.backend.getApiKeys()
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0].key, '1234')
        self.assertEqual(keys[0].vcode, 'secretvcode')
        self.assertEqual(keys[1].key, '2468')

    def test_4101_api_del(self):
        self.backend.addApiKey('1234', 'secretvcode')
        self.backend.addApiKey('2468', 'anothervcode')

        self.backend.delApiKey('1234')
        # ignore bad ones?
        self.backend.delApiKey('4321')

        keys = self.backend.getApiKeys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0].key, '2468')
        self.assertEqual(keys[0].vcode, 'anothervcode')

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(SqlBackendTestCase))
    return suite
