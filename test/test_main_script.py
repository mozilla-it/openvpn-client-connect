""" Test suite for the openvpn_client_connect class """
import unittest
import os
import sys
import test.context  # pylint: disable=unused-import
import mock
import openvpn_client_connect.openvpn_script
if sys.version_info.major >= 3:
    from io import StringIO  # pragma: no cover
else:
    from io import BytesIO as StringIO  # pragma: no cover


class TestMainScript(unittest.TestCase):
    """ Class of tests """

    def setUp(self):
        """ Create the library """
        self.script = openvpn_client_connect.openvpn_script

    def tearDown(self):
        """ Clear the env so we don't impact other tests """
        for varname in ['common_name', 'IV_VER', 'trusted_ip',
                        'something1', 'something2', 'username']:
            if varname in os.environ:
                del os.environ[varname]

    def test_client_version_allowed(self):
        ''' Verify client_version_allowed does what we expect '''
        with mock.patch('openvpn_client_connect.client_connect.ClientConnect') as mock_connector:
            instance = mock_connector.return_value
            with mock.patch.object(instance, 'client_version_allowed') as mock_cva:
                self.script.client_version_allowed(instance, '2.x')
        mock_cva.assert_called_once_with('2.x')

    def test_build_lines(self):
        ''' Verify build_lines does what we expect '''
        with mock.patch('openvpn_client_connect.client_connect.ClientConnect') as mock_connector:
            instance = mock_connector.return_value
            with mock.patch.object(instance, 'get_dns_server_lines') as mock_lines_dns, \
                    mock.patch.object(instance, 'get_search_domains_lines') as mock_lines_search, \
                    mock.patch.object(instance, 'get_dynamic_route_lines') as mock_lines_dynroute, \
                    mock.patch.object(instance, 'get_static_route_lines') as mock_lines_statroute, \
                    mock.patch.object(instance, 'get_protocol_lines') as mock_lines_proto:
                self.script.build_lines(instance, 'username_is', 'username_as', 'client_ip')
        mock_lines_dns.assert_called_once_with()
        mock_lines_search.assert_called_once_with(username_is='username_is',
                                                  username_as='username_as')
        mock_lines_dynroute.assert_called_once_with(username_is='username_is',
                                                    username_as='username_as',
                                                    client_ip='client_ip')
        mock_lines_statroute.assert_called_once_with()
        mock_lines_proto.assert_called_once_with()

    def test_20_main_main(self):
        ''' Test the main() interface '''
        with self.assertRaises(SystemExit) as exiting, \
                mock.patch.object(self.script, 'main_work',
                                  return_value=True):
            self.script.main()
        self.assertEqual(exiting.exception.code, 0)
        with self.assertRaises(SystemExit) as exiting, \
                mock.patch.object(self.script, 'main_work',
                                  return_value=False):
            self.script.main()
        self.assertEqual(exiting.exception.code, 1)

    def test_20_main_blank(self):
        ''' With no conf file provided, bomb out '''
        with self.assertRaises(SystemExit) as exiting, \
                mock.patch('sys.stderr', new=StringIO()):
            self.script.main_work([])
        self.assertEqual(exiting.exception.code, 2)

    # There is no test here for "I gave you a bad conf file"
    # The conf file is passed as a name and not looked at within
    # this wrapper script.

    def test_22_main_blank(self):
        ''' With envvars provided, bomb out '''
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            result = self.script.main_work(['script', '--conf', 'test/context.py', 'outfile'])
        self.assertFalse(result, 'With no environmental variables, main_work must fail')
        self.assertIn('No common_name or username environment variable provided.',
                      fake_out.getvalue())

    def test_23_incomplete_vars(self):
        ''' With just one envvar provided, bomb out '''
        os.environ['common_name'] = 'bob-device'
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            result = self.script.main_work(['script', '--conf', 'test/context.py', 'outfile'])
        self.assertFalse(result, 'With not-all environmental variables, main_work must fail')
        self.assertIn('No trusted_ip environment variable provided.', fake_out.getvalue())

    def test_23_bad_version(self):
        ''' Run but have a minimum version failure. '''
        os.environ['common_name'] = 'bob-device'
        os.environ['username'] = 'bobby.tables'
        os.environ['trusted_ip'] = '10.20.30.40'
        os.environ['IV_VER'] = '2.3'
        with mock.patch.object(self.script, 'client_version_allowed', return_value=False):
            result = self.script.main_work(['script', '--conf', 'test/context.py', 'outfile'])
        self.assertFalse(result, 'When versions are too low, main_work must be False')

    def test_23_cant_write(self):
        ''' Run but be unable to write a file. '''
        os.environ['common_name'] = 'bob-device'
        os.environ['username'] = 'bobby.tables'
        os.environ['trusted_ip'] = '10.20.30.40'
        os.environ['IV_VER'] = '2.4.6'
        with mock.patch.object(self.script, 'build_lines'):
            with mock.patch('six.moves.builtins.open', side_effect=IOError):
                result = self.script.main_work(['script', '--conf', 'test/context.py', 'outfile'])
        self.assertFalse(result, 'When unable to write an output file, main_work must fail')

    def test_24_complete_vars(self):
        ''' Run correctly. '''
        os.environ['common_name'] = 'bob-device'
        os.environ['username'] = 'bobby.tables'
        os.environ['trusted_ip'] = '10.20.30.40'
        os.environ['IV_VER'] = '2.4.6'
        with mock.patch.object(self.script, 'build_lines') as mock_buildlines, \
                mock.patch('openvpn_client_connect.client_connect.ClientConnect') as mock_connector, \
                mock.patch.object(self.script, 'client_version_allowed', return_value=True):
            mock_cc = mock_connector.return_value
            with mock.patch('six.moves.builtins.open', create=True,
                            return_value=mock.MagicMock(spec=StringIO())) as mock_open:
                result = self.script.main_work(['script', '--conf', 'test/context.py', 'outfile'])
        mock_buildlines.assert_called_once_with(config_object=mock_cc,
                                                username_is='bob-device',
                                                username_as='bobby.tables',
                                                client_ip='10.20.30.40')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_once()
        self.assertTrue(result, 'With all environmental variables, main_work must work')
