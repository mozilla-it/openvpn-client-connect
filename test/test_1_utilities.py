""" Test suite for the openvpn_client_connect non-class methods """
import unittest
import test.context  # pylint: disable=unused-import
import six
from openvpn_client_connect.client_connect import versioncompare
from openvpn_client_connect.client_connect import max_route_lines


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

    def test_maxroutelines(self):
        """ Verify that max_route_lines returns good answers """

        retval = max_route_lines(None)
        self.assertIsInstance(retval, list,
                              'max_route_lines must be a list')
        self.assertEqual(len(retval), 1,
                         'max_route_lines must only return 1 item')
        self.assertIsInstance(retval[0], six.string_types,
                              'max_route_lines\'s item must be a string')
        six.assertRegex(self, retval[0], 'max-routes',
                        'max_route_lines must return a string containing max-routes')

        retval = max_route_lines('2.3.13')
        self.assertIsInstance(retval, list,
                              'max_route_lines must be a list')
        self.assertEqual(len(retval), 1,
                         'max_route_lines must only return 1 item')
        self.assertIsInstance(retval[0], six.string_types,
                              'max_route_lines\'s item must be a string')
        six.assertRegex(self, retval[0], 'max-routes',
                        'max_route_lines must return a string containing max-routes')

        retval = max_route_lines('2.4.4')
        self.assertIsInstance(retval, list,
                              'max_route_lines must be a list')
        self.assertEqual(len(retval), 0,
                         'max_route_lines must not return an item')

        # Make sure garbage input doesn't kill us.  All we're looking
        # for here is that this call doesn't traceback.
        retval = max_route_lines('urfburf')
        self.assertIsInstance(retval, list,
                              'max_route_lines must be a list')
