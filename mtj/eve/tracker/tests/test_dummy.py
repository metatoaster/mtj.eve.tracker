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
        self.assertEqual(len(corp.starbases().result), 1)
        corp.starbases_index = 1
        self.assertEqual(len(corp.starbases().result), 2)

    def test_0001_starbase_details(self):
        corp = DummyCorp()
        result = corp.starbase_details(507862)
        self.assertEqual(result.result['state_ts'], 1362793009)
        self.assertEqual(result.timestamp, 1362792986)
        self.assertEqual(result.expires, 1362793351)

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
        self.assertEqual(sorted(json_corp.starbases().result.keys()),
            [507862, 507863])
        self.assertEqual(dummy_corp.starbase_details(507862),
            json_corp.starbase_details(507862))
        self.assertRaises(APIError, dummy_corp.starbase_details, 507863)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(DummyCorpTestCase))
    suite.addTest(makeSuite(JsonDummyCorpTestCase))
    return suite
