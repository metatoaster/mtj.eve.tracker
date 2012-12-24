from unittest import TestCase, TestSuite, makeSuite

from evelink.api import APICache

from mtj.eve.tracker import cache
from mtj.eve.tracker.evelink import Map, EVE, Server, API


class CacheTestCase(TestCase):
    """
    Unit tests for the basic structures.
    """

    def setUp(self):
        pass

    def test_0000_cache_patched(self):
        cache.set_evelink_cache(':memory:')
        self.assertEqual(Map.api, cache.EvelinkCache._api)
        self.assertEqual(EVE.api, cache.EvelinkCache._api)
        self.assertEqual(Server.api, cache.EvelinkCache._api)

    def test_0001_cache_api(self):
        cache.set_evelink_cache(':memory:')
        api = API()
        self.assertEqual(api.cache, cache.EvelinkCache._cache)

    def test_0100_uncache_patched(self):
        cache.unset_evelink_cache()
        self.assertNotEqual(Map.api, cache.EvelinkCache._api)
        self.assertNotEqual(EVE.api, cache.EvelinkCache._api)
        self.assertNotEqual(Server.api, cache.EvelinkCache._api)

    def test_0101_uncache_api(self):
        cache.unset_evelink_cache()
        api = API()
        self.assertNotEqual(api.cache, cache.EvelinkCache._cache)
        self.assertTrue(isinstance(api.cache, APICache))


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(CacheTestCase))
    return suite
