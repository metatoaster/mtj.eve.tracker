from unittest import TestCase, TestSuite, makeSuite
import json

from evelink.api import APIError

from .dummyevelink import DummyCorp, JsonDummyCorp


class DummyCorpTestCase(TestCase):
    """
    Test cases for the JsonDummyCorp
    """

    def test_0000_starbases(self):
        corp = DummyCorp()
        self.assertEqual(len(corp.starbases()), 1)
        corp.starbases_index = 1
        self.assertEqual(len(corp.starbases()), 2)

    def test_0001_starbase_details(self):
        corp = DummyCorp()
        result = corp.starbase_details(507862)
        self.assertEqual(result['state_ts'], 1362793009)

    def test_0002_starbase_details_error(self):
        corp = DummyCorp()
        self.assertRaises(APIError, corp.starbase_details, 507863)


class JsonDummyCorpTestCase(TestCase):
    """
    Test cases for the JsonDummyCorp
    """

    def test_0000_base(self):
        dummy_corp = DummyCorp()
        result = JsonDummyCorp.dumps(dummy_corp)
        json_corp = JsonDummyCorp()
        json_corp.loads(result)
        self.assertEqual(dummy_corp.starbases(), json_corp.starbases())
        self.assertEqual(dummy_corp.starbase_details(507862),
            json_corp.starbase_details(507862))

    def test_0000_base(self):
        dummy_corp = DummyCorp()
        dummy_corp.starbases_index = 1
        result = JsonDummyCorp.dumps(dummy_corp)
        json_corp = JsonDummyCorp()
        json_corp.loads(result)
        self.assertEqual(dummy_corp.starbases(), json_corp.starbases())
        self.assertEqual(sorted(json_corp.starbases().keys()),
            [507862, 507863])
        self.assertEqual(dummy_corp.starbase_details(507862),
            json_corp.starbase_details(507862))
        self.assertRaises(APIError, dummy_corp.starbase_details, 507863)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(DummyCorpTestCase))
    suite.addTest(makeSuite(JsonDummyCorpTestCase))
    return suite
