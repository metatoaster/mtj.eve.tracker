from unittest import TestCase, TestSuite, makeSuite
import json

from .dummyevelink import DummyCorp, JsonDummyCorp


class JsonDummyCorpTestCase(TestCase):
    """
    Test cases for the JsonDummyCorp
    """

    def setUp(self):
        self.dummy_corp = DummyCorp()

    def tearDown(self):
        pass

    def test_0000_base(self):
        result = JsonDummyCorp.dumps(self.dummy_corp)
        json_corp = JsonDummyCorp()
        json_corp.loads(result)
        self.assertEqual(self.dummy_corp.starbases(), json_corp.starbases())
        self.assertEqual(self.dummy_corp.starbase_details(507862),
            json_corp.starbase_details(507862))


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(JsonDummyCorpTestCase))
    return suite
