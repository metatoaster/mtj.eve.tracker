import unittest
import doctest

from mtj.eve.tracker.tests import base

def test_suite():
    return unittest.TestSuite([

        # Base
        doctest.DocFileSuite(
            'README.rst', package='mtj.eve.tracker',
            setUp=base.setUp, tearDown=base.tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
        ),

        # inline
        doctest.DocTestSuite(
            module='mtj.eve.tracker.backend.sql',
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
        ),

    ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
