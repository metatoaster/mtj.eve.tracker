from unittest import TestCase, TestSuite, makeSuite

from mtj.multimer.buffer import Buffer, TimedBuffer


class StructureTestCase(TestCase):
    """
    Unit tests for the basic structures.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_0000_base(self):
        pass


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(StructureTestCase))
    return suite
