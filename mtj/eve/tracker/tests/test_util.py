from datetime import timedelta
from unittest import TestCase, TestSuite, makeSuite

from mtj.eve.tracker.frontend import util


class FrontendUtilTestCase(TestCase):
    """
    Unit tests for the basic structures.
    """

    def test_format_reinforcement(self):
        self.assertEqual(util.format_reinforcement(timedelta(seconds=180000)),
            '2 days, 2 hours')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=172800)),
            '2 days')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=111600)),
            '1 day, 7 hours')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=90000)),
            '1 day, 1 hour')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=89999)),
            '1 day')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=86401)),
            '1 day')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=86400)),
            '1 day')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=86399)),
            '23 hours')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=3600)),
            '1 hour')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=0)),
            '0 hours')
        self.assertEqual(util.format_reinforcement(timedelta(seconds=1)),
            '0 hours')

        # negative values of all types very undefined (:aaaaa:)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(FrontendUtilTestCase))
    return suite
