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

    def test_0102_update_apikey(self):
        options = Options()
        options.update({'api': {'api_keys': {'1': '2'}}})
        self.assertEqual(options.config['api'].get('api_keys'), {'1': '2'})

    def test_0103_update_choice(self):
        options = Options()
        options.update({'api': {'source': 'backend'}})
        self.assertEqual(options.config['api']['source'], 'backend')
        options.update({'api': {'source': 'fake'}})
        self.assertEqual(options.config['api']['source'], 'backend')
        options.update({'api': {'source': 'config'}})
        self.assertEqual(options.config['api']['source'], 'config')


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(OptionsTestCase))
    return suite
