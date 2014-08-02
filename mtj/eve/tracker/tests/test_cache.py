from unittest import TestCase, TestSuite, makeSuite

import time
import zope.component
from zope.component.hooks import getSiteManager

from evelink.api import APICache

from mtj.eve.tracker.interfaces import IEvelinkCache
from mtj.eve.tracker.evelink import Helper, API, EvelinkSqliteCache

from mtj.evedb.tests.base import init_test_db
from .base import installTestSite, tearDown


_error_xml = r"""
<?xml version="1.0"?>
<eveapi version="2">
  <currentTime>2009-09-09 12:34:56</currentTime>
  <error code="221">
    Invalid page error
  </error>
  <cachedUntil>2038-12-31 23:59:59</cachedUntil>
</eveapi>
""".strip()

class CacheTestCase(TestCase):
    """
    Test for the additional cache supports.
    """

    def setUp(self):
        installTestSite()
        init_test_db()

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


class EvelinkSqliteCacheTestCase(TestCase):

    def test_0000_standard_cache(self):
        cache = EvelinkSqliteCache(':memory:')
        key = 'dummy'
        duration = 86400000
        cache.put(key, 'test_value', duration)
        cursor = cache.connection.cursor()
        cursor.execute('select value, expiration from cache where "key"=?',
            (key,))
        cache_until = time.time() + duration
        value, expiration = cursor.fetchone()
        self.assertTrue(cache_until > expiration)

        # not actually limited to this.
        cache_until = time.time() + EvelinkSqliteCache.max_error_cache_duration
        self.assertFalse(cache_until > expiration)

    def test_0001_limited_error_duration(self):
        cache = EvelinkSqliteCache(':memory:')
        key = 'dummy'
        duration = 86400000
        cache.put(key, _error_xml, duration)
        cursor = cache.connection.cursor()
        cursor.execute('select value, expiration from cache where "key"=?',
            (key,))
        # the duration is forcibly
        cache_until = time.time() + EvelinkSqliteCache.max_error_cache_duration
        value, expiration = cursor.fetchone()
        self.assertTrue(cache_until > expiration)

        self.assertFalse(cache_until > time.time() + duration)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(CacheTestCase))
    suite.addTest(makeSuite(EvelinkSqliteCacheTestCase))
    return suite
