from unittest import TestCase, TestSuite, makeSuite

import zope.component
from zope.component.hooks import getSiteManager

from evelink.api import APICache

from mtj.eve.tracker.interfaces import IEvelinkCache
from mtj.eve.tracker.evelink import Helper, API, EvelinkSqliteCache

from .base import installTestSite, tearDown


class CacheTestCase(TestCase):
    """
    Test for the additional cache supports.
    """

    def setUp(self):
        installTestSite()

    def tearDown(self):
        tearDown(self)

    def test_0000_cache_no_register(self):
        """
        No cache registed.
        """

        api = API()
        # Default cache has this attribute.
        self.assertTrue(isinstance(api.cache.cache, dict))
        self.assertFalse(hasattr(api.cache, 'connection'))

        helper = Helper()
        # By default these are equal.
        self.assertEqual(helper.eve.api, helper.map.api)
        self.assertEqual(helper.eve.api.cache, helper.map.api.cache)

        # Just to demonstrate expected default behavior.
        helper.eve.api.cache.put('dummy', 'test_value', 100)
        self.assertEqual(helper.eve.api.cache.cache['dummy'][0], 'test_value')

    def test_0001_cache_post_register(self):
        """
        Cache registered after helper.
        """

        helper = Helper()

        cache = EvelinkSqliteCache(':memory:')
        getSiteManager().registerUtility(cache, IEvelinkCache)

        # The API cache in the instances for the helper is still same.
        self.assertNotEqual(helper.eve.api.cache, cache)

        # Try this again.
        helper.eve.api.cache.put('dummy', 'test_value', 100)

        # As the cache utility is registered, data would not be here.
        self.assertEqual(helper.eve.api.cache.cache, {})

        # the cached data will however be present here.
        self.assertEqual(cache.get('dummy'), 'test_value')

        api = API()
        self.assertEqual(api.cache, cache)
        self.assertTrue(hasattr(api.cache, 'connection'))

    def test_0002_cache_pre_register(self):
        """
        Cache registered before helper.
        """

        cache = EvelinkSqliteCache(':memory:')
        getSiteManager().registerUtility(cache, IEvelinkCache)

        helper = Helper()

        # Now the cache is right away an instance of the sqlite cache
        # rather than the dynamic class.  This may or may not be
        # desirable
        self.assertEqual(helper.eve.api.cache, cache)

        api = API()
        self.assertEqual(api.cache, cache)
        self.assertTrue(hasattr(api.cache, 'connection'))


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(CacheTestCase))
    return suite
