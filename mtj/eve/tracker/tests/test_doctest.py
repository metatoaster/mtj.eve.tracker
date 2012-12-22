import unittest
import doctest


def test_suite():
    return unittest.TestSuite([

        # Base
        doctest.DocFileSuite(
            'README.rst', package='mtj.eve.tracker',
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
        ),

    ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
