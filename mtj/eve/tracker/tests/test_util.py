from datetime import timedelta
from unittest import TestCase, TestSuite, makeSuite

from mtj.eve.tracker.frontend import util


class FrontendUtilTestCase(TestCase):
    """
    Unit tests for the basic structures.
    """

    def test_0000_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=180000)),
            '2 days, 2 hours')

    def test_0001_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=172800)),
            '2 days')

    def test_0002_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=111600)),
            '1 day, 7 hours')

    def test_0003_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=90000)),
            '1 day, 1 hour')

    def test_0004_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=89999)),
            '1 day')

    def test_0005_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=86401)),
            '1 day')

    def test_0006_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=86400)),
            '1 day')

    def test_0007_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=86399)),
            '23 hours')

    def test_0008_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=3600)),
            '1 hour')

    def test_0009_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=0)),
            '0 hours')

    def test_0010_format_timedelta(self):
        self.assertEqual(util.format_timedelta(timedelta(seconds=1)),
            '0 hours')

        # negative values of all types very undefined (:aaaaa:)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(FrontendUtilTestCase))
    return suite
