from __future__ import unicode_literals

from unittest import TestCase, TestSuite, makeSuite

from mtj.eve.tracker.ctrl import Options


class OptionsTestCase(TestCase):
    """
    Unit tests for the key manager.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_0100_update(self):
        options = Options()
        options.update({'logging': {'level': 'DEBUG'}})
        self.assertEqual(options.config['logging']['level'], 'DEBUG')

    def test_0100_update(self):
        options = Options()
        options.update({'logging': {'level': 1}})
        self.assertNotEqual(options.config['logging']['level'], 1)

    def test_0102_update(self):
        options = Options()
        options.update({'logging': {'no_value': 'no_value'}})
        self.assertEqual(options.config['logging'].get('no_value'), None)

    def test_0200_update_apikey(self):
        options = Options()
        options.update({'implementations': {'IAPIKeyManager': {
            'class': 'mtj.eve.tracker.manager.APIKeyManager',
            'args': [],
            'kwargs': {'api_keys': {'1': '2'}},
        }}})
        self.assertEqual(options.config['implementations']['IAPIKeyManager'
            ].get('args'), [])
        self.assertEqual(options.config['implementations']['IAPIKeyManager'
            ].get('kwargs'), {'api_keys': {'1': '2'},})

    def test_0300_update_backend(self):
        options = Options()
        options.update({'implementations': {'ITrackerBackend': {
            'class': 'mtj.eve.tracker.backend.sql.SQLAlchemyBackend',
            'kwargs': {'src': 'sqlite:///backend.db'},
        }}})
        self.assertEqual(options.config['implementations']['ITrackerBackend'
            ].get('args'), [])
        self.assertEqual(options.config['implementations']['ITrackerBackend'
            ].get('kwargs'), {'src': 'sqlite:///backend.db',})

    def test_0400_update_cache(self):
        options = Options()
        # missing kwargs
        options.update({'implementations': {'IEvelinkCache': {
            'class': 'mtj.eve.tracker.evelink.EveCache',
            'args': ['/tmp/file'],
        }}})
        self.assertEqual(options.config['implementations']['IEvelinkCache'
            ].get('kwargs'), {})
        self.assertEqual(options.config['implementations']['IEvelinkCache'
            ].get('args'), ['/tmp/file'])


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(OptionsTestCase))
    return suite
