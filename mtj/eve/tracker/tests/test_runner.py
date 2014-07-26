from unittest import TestCase, TestSuite, makeSuite

import zope.component

from mtj.eve.tracker import interfaces
from mtj.eve.tracker.runner import BaseRunner
from mtj.eve.tracker.ctrl import Options

from mtj.evedb.tests.base import test_db_path
from .dummyevelink import DummyCorp


class RunnerTestCase(TestCase):
    """
    Unit tests for the key manager.
    """

    def setUp(self):
        self.config = Options()
        self.config.update({'data': {'evedb_url': test_db_path()}})

    def tearDown(self):
        pass

    def test_0000_base_runner(self):
        runner = BaseRunner()
        runner.configure(config=self.config.config)
        runner._preinitialize()

        manager = zope.component.queryUtility(interfaces.ITowerManager)
        self.assertTrue(interfaces.ITowerManager.providedBy(manager))

        backend = zope.component.queryUtility(interfaces.ITrackerBackend)
        self.assertTrue(interfaces.ITrackerBackend.providedBy(backend))

        keyman = zope.component.queryAdapter(backend,
            interfaces.IAPIKeyManager)

        self.assertTrue(keyman is None)

    def test_1000_sql_api(self):
        runner = BaseRunner()
        # no colliding keys.
        self.config.update({'implementations': {'IAPIKeyManager': {
            'class': 'mtj.eve.tracker.backend.sql:SQLAPIKeyManager',
            'args': [],
            'kwargs': {},
        }}})
        runner.configure(config=self.config.config)
        runner._preinitialize()

        backend = zope.component.queryUtility(interfaces.ITrackerBackend)
        backend._conn.execute('insert into api_key values '
            '("test1", "testing1_vcode2")')
        backend._conn.execute('insert into api_key values '
            '("test2", "testing2_vcode4")')

        keyman = zope.component.queryUtility(interfaces.IAPIKeyManager)
        self.assertTrue(interfaces.IAPIKeyManager.providedBy(keyman))

        results = keyman.getAllWith(DummyCorp)
        self.assertEqual(len(results), 2)
        self.assertTrue(isinstance(results[0], DummyCorp))
        self.assertEqual(results[0].api.api_key, ('test1', 'testing1_vcode2'))
        self.assertEqual(results[1].api.api_key, ('test2', 'testing2_vcode4'))

        # new API entries immediately available.
        backend._conn.execute('insert into api_key values '
            '("test3", "testing3_vcode6")')
        results = keyman.getAllWith(DummyCorp)
        self.assertEqual(results[2].api.api_key, ('test3', 'testing3_vcode6'))


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(RunnerTestCase))
    return suite
