""" Test suite for the openvpn_client_connect non-class methods """
import unittest
import test.context  # pylint: disable=unused-import
from openvpn_client_connect.client_connect import versioncompare


class TestUtilities(unittest.TestCase):
    """ Class of tests """

    def test_versioncompare(self):
        """ Verify that the versioncompare returns good answers """
        # Exact-match strings should all be zero:
        self.assertEqual(versioncompare('1.0', '1.0'), 0)
        self.assertEqual(versioncompare('2.0', '2.0'), 0)
        self.assertEqual(versioncompare('10.0', '10.0'), 0)
        self.assertEqual(versioncompare('10.10', '10.10'), 0)
        self.assertEqual(versioncompare('10.10.10.10.10',
                                        '10.10.10.10.10'), 0)

        # Throw in some non-strings.
        # This is less about the value returned.. this is somewhat of a
        # garbage test since we don't do very smart things about non-numbers
        # AND openvpn so far isn't using non-numbers.
        self.assertEqual(versioncompare('1.1', '1.x'), 1)
        self.assertEqual(versioncompare('2.x', '2.4'), 2)

        # Normal boring comparisons, for sanity checking:
        self.assertEqual(versioncompare('1.1', '1.0'), 1)
        self.assertEqual(versioncompare('1.0', '1.1'), 2)
        self.assertEqual(versioncompare('10.1', '10.0'), 1)
        self.assertEqual(versioncompare('10.0', '10.1'), 2)
        self.assertEqual(versioncompare('10.10', '10.4'), 1)
        self.assertEqual(versioncompare('10.4', '10.10'), 2)
        self.assertEqual(versioncompare('10.11', '10.10'), 1)
        self.assertEqual(versioncompare('10.10', '10.11'), 2)
        self.assertEqual(versioncompare('10.10.10.10.20',
                                        '10.10.10.10.10'), 1)
        self.assertEqual(versioncompare('10.10.10.10.10',
                                        '10.10.10.10.20'), 2)

        # This one looks weird, I know.  You could argue this is generally
        # wrong, but it is what we want for openvpn:
        self.assertEqual(versioncompare('1.0', '1.0.0'), 2)
        self.assertEqual(versioncompare('1.0.0', '1.0'), 1)
        # This is, "the dot-zero release is greater than 1.0", or, the way
        # we use it, "it's part of the 1.0 family."
