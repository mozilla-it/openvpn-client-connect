""" Test suite for the openvpn_client_connect class """
import unittest
import sys
import test.context  # pylint: disable=unused-import
from netaddr import IPNetwork
import mock
import openvpn_client_connect.vpn_user_routes
if sys.version_info.major >= 3:
    from io import StringIO  # pragma: no cover
else:
    from io import BytesIO as StringIO  # pragma: no cover


class TestMainScript(unittest.TestCase):
    """ Class of tests """

    def setUp(self):
        """ Create the library """
        self.script = openvpn_client_connect.vpn_user_routes

    def test_20_main_main(self):
        ''' Test the main() interface '''
        with self.assertRaises(SystemExit) as exiting, \
                mock.patch.object(self.script, 'main_work',
                                  return_value=True):
            self.script.main()
        self.assertEqual(exiting.exception.code, 0)

    def test_20_main_blank(self):
        ''' With no conf file provided, bomb out '''
        with self.assertRaises(SystemExit) as exiting, \
                mock.patch('sys.stderr', new=StringIO()):
            self.script.main_work([])
        self.assertEqual(exiting.exception.code, 2)

    def test_30_main_genericoffice(self):
        ''' test with --office '''
        retval = [IPNetwork('1.1.1.1/22')]  # Note the deliberate weird CIDR
        with mock.patch.object(self.script, 'GetUserRoutes') as gur, \
                mock.patch('sys.stdout', new=StringIO()) as fake_out:
            instance = gur.return_value
            instance.build_user_routes.return_value = retval
            self.script.main_work(['script', '--office', '--conf', 'path1', 'user1'])
        instance.build_user_routes.assert_called_once_with('user1', True)
        self.assertEqual('1.1.0.0 255.255.252.0\n', fake_out.getvalue())

    def test_31_main_officeid(self):
        ''' test with --office-id '''
        retval = [IPNetwork('2.2.2.130/16')]  # Note the deliberate weird CIDR
        with mock.patch.object(self.script, 'GetUserRoutes') as gur, \
                mock.patch('sys.stdout', new=StringIO()) as fake_out:
            instance = gur.return_value
            instance.build_user_routes.return_value = retval
            self.script.main_work(['script', '--office-id', 'lhr1', '--conf', 'path2', 'user2'])
        instance.build_user_routes.assert_called_once_with('user2', 'lhr1')
        self.assertEqual('2.2.0.0 255.255.0.0\n', fake_out.getvalue())

    def test_32_main_remote(self):
        ''' test without an office flag '''
        retval = [IPNetwork('3.3.3.3/24')]  # Note the deliberate weird CIDR
        with mock.patch.object(self.script, 'GetUserRoutes') as gur, \
                mock.patch('sys.stdout', new=StringIO()) as fake_out:
            instance = gur.return_value
            instance.build_user_routes.return_value = retval
            self.script.main_work(['script', '--conf', 'path3', 'user3'])
        instance.build_user_routes.assert_called_once_with('user3', None)
        self.assertEqual('3.3.3.0 255.255.255.0\n', fake_out.getvalue())
