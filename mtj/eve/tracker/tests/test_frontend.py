from unittest import TestCase, TestSuite, makeSuite

import time
from contextlib import contextmanager
from json import loads
import zope.component
from zope.component.hooks import getSiteManager

# While it will be best if we have a dummy of some kind, we need to
# ensure the integration is done with our only backend for the mean time
# so just straight up use the sql version.
from mtj.eve.tracker.backend import sql
from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.interfaces import IAPIKeyManager

# Cannot use the BaseTowerManager as it does not cache API time usage.
from mtj.eve.tracker.manager import TowerManager

import mtj.eve.tracker.frontend.json
from mtj.eve.tracker.frontend.json import Json

from mtj.evedb.tests.base import init_test_db
from .base import setUp, tearDown
from .dummyevelink import DummyKeyManager


@contextmanager
def at_time(mod, ts):
    faketime = lambda: ts
    try:
        realtime, mod.time = mod.time, faketime
        yield
    finally:
        mod.time = realtime


class JsonTestCase(TestCase):
    """
    Testing the JSON frontend with the SQL backend for now.
    """

    def setUp(self):
        setUp(self)  # specify backend here with backend arg when done
        init_test_db()
        self.backend = zope.component.getUtility(ITrackerBackend)
        self.manager = TowerManager()
        self.frontend = Json(self.backend)

        sm = getSiteManager()
        self.dk = DummyKeyManager()
        sm.registerUtility(self.dk, IAPIKeyManager)

    def tearDown(self):
        tearDown(self)

    def test_empty(self):
        self.frontend.set_timestamp(1400000000)
        overview = loads(self.frontend.overview())
        self.assertEqual(overview, {
            u'offlined': [], u'timestamp': 1400000000, u'online': [],
            u'api_usage': [], u'reinforced': []
        })

    def test_one_import(self):
        # can't just import by corp, have to import all
        with at_time(sql, 1362794809):
            self.manager.importAll()

        self.frontend.set_timestamp(1364175409)
        overview = loads(self.frontend.overview())
        self.assertEqual(overview['online'], [{
            u'apiErrorCount': 0,
            u'apiTimestamp': 1362792986,
            u'apiTimestampFormatted': u'2013-03-09 01:36',
            u'auditLabel': u'',
            u'celestialName': u'6VDT-H III - Moon 1',
            u'id': 1,
            u'offlineAt': 1364603809,
            u'offlineAtFormatted': u'2013-03-30 00:36',
            u'regionName': u'Fountain',
            u'state': 4,
            u'stateName': u'online',
            u'stateTimestamp': 1362793009,
            u'stateTimestampDeltaFormatted': u'-16 days, 0:00:00',
            u'stateTimestampFormatted': u'2013-03-09 01:36',
            u'timeRemaining': 428400,
            u'timeRemainingFormatted': u'4 days, 23:00:00',
            u'typeID': 20064,
            u'typeName': u'Gallente Control Tower Small'
        }])

        self.assertEqual(overview['api_usage'], [{
            u'start_ts_delta': u'15 days, 23 hours, 30 minutes',
            u'end_ts_delta': u'15 days, 23 hours, 30 minutes',
            u'end_ts': 1362794809,
            u'start_ts': 1362794809,
            u'state': u'completed',
            u'end_ts_formatted': u'2013-03-09 02:06',
            u'start_ts_formatted': u'2013-03-09 02:06',
        }])
