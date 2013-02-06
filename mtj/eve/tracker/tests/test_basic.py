from unittest import TestCase, TestSuite, makeSuite

from mtj.eve.tracker.pos import TowerResourceBuffer


class TowerResourceBufferTestCase(TestCase):
    """
    Unit tests for the basic structures.
    """

    def setUp(self):
        self.fuelbay = TowerResourceBuffer(None,
            delta=40, timestamp=0, purpose=1, value=28000)

    def test_0000_base(self):
        self.assertEqual(self.fuelbay.value, 28000)
        self.assertEqual(self.fuelbay.delta, 40)

    def test_0001_nexthour(self):
        fuelbay = self.fuelbay.getCurrent(timestamp=3600)
        self.assertEqual(fuelbay.value, 27960)


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
    suite.addTest(makeSuite(TowerResourceBufferTestCase))
    suite.addTest(makeSuite(StructureTestCase))
    return suite
