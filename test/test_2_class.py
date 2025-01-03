""" Test suite for the openvpn_client_connect class """
import unittest
import os
import test.context  # pylint: disable=unused-import
import configparser
import mock
import netaddr
import openvpn_client_connect.client_connect
import openvpn_client_connect.per_user_configs


class TestClass(unittest.TestCase):
    """ Class of tests """

    def setUp(self):
        """ Preparing test rig """
        self.test_office_ip = '127.0.0.2'
        ccmod = openvpn_client_connect.client_connect
        noconf = ccmod.ClientConnect('test_configs/nosuchfile.conf')
        empty = ccmod.ClientConnect('test_configs/empty.conf')
        superempty = ccmod.ClientConnect('test_configs/superempty.conf')
        # wrongvals is an awful file that ends up falling back to defaults.
        # Thus, while it looks like it's dynamic and static, it's wrong enough
        # to be falling back to failsafes, and thus it's only minimally tested,
        # since it ends up doing close to nothing right.
        wrongvals = ccmod.ClientConnect('test_configs/wrongvals.conf')
        udp_dyn = ccmod.ClientConnect('test_configs/udp_dynamic.conf')
        tcp_dyn = ccmod.ClientConnect('test_configs/tcp_dynamic.conf')
        udp_stat = ccmod.ClientConnect('test_configs/udp_static.conf')
        tcp_stat = ccmod.ClientConnect('test_configs/tcp_static.conf')
        doubleup = ccmod.ClientConnect('test_configs/doubleup.conf')
        singlenat = ccmod.ClientConnect('test_configs/singlenat.conf')
        multinat = ccmod.ClientConnect('test_configs/multinat.conf')
        min_version = ccmod.ClientConnect('test_configs/min_version.conf')
        min_version_old = ccmod.ClientConnect('test_configs/min_version_old.conf')
        min_version_dict = ccmod.ClientConnect('test_configs/min_version_dict.conf')
        self.configs = {
            'dynamics': [udp_dyn, tcp_dyn,
                         doubleup,
                         singlenat, multinat],
            'dynamiconly': [udp_dyn, tcp_dyn],
            'statics': [udp_stat, tcp_stat, doubleup],
            'staticonly': [udp_stat, tcp_stat],
            'udps': [udp_dyn, udp_stat, doubleup, wrongvals, min_version],
            'tcps': [tcp_dyn, tcp_stat],
            'invalid': [noconf, empty],
            'min_version': [min_version, min_version_old, min_version_dict],
            'min_version_empty': [superempty],
            'valid': [udp_dyn, tcp_dyn,
                      udp_stat, tcp_stat,
                      doubleup,
                      singlenat, multinat],
            'all': [noconf, empty,
                    udp_dyn, tcp_dyn,
                    udp_stat, tcp_stat,
                    min_version,
                    doubleup, wrongvals],
            }
        self.users = empty._ingest_config_from_file('test_configs/testing_users.conf')

    def test_03_ingest_no_config_files(self):
        """ With no config files, get an empty ConfigParser """
        for obj in self.configs['all']:
            result = obj._ingest_config_from_file([])
            self.assertIsInstance(result, configparser.ConfigParser,
                                  'Did not create a config object')
            self.assertEqual(result.sections(), [], 'Empty configs must have no parsed config')

    def test_04_ingest_no_config_file(self):
        """ With all missing config files, get an empty ConfigParser """
        for obj in self.configs['all']:
            _not_a_real_file = '/tmp/no-such-file.txt'  # nosec hardcoded_tmp_directory
            result = obj._ingest_config_from_file([_not_a_real_file])
            self.assertIsInstance(result, configparser.ConfigParser,
                                  'Did not create a config object')
            self.assertEqual(result.sections(), [], 'Empty configs must have no parsed config')

    def test_05_ingest_bad_config_file(self):
        """ With a bad config file, get an empty ConfigParser """
        for obj in self.configs['all']:
            result = obj._ingest_config_from_file(['test/context.py'])
            self.assertIsInstance(result, configparser.ConfigParser,
                                  'Did not create a config object')
            self.assertEqual(result.sections(), [], 'Empty configs must have no parsed config')

    def test_06_ingest_config_from_file(self):
        """ With an actual config file, get a populated ConfigParser """
        test_reading_file = '/tmp/test-reader.txt'  # nosec hardcoded_tmp_directory
        with open(test_reading_file, 'w', encoding='utf-8') as filepointer:
            filepointer.write('[aa]\nbb = cc\n')
        filepointer.close()
        for obj in self.configs['all']:
            result = obj._ingest_config_from_file([test_reading_file])
            self.assertIsInstance(result, configparser.ConfigParser,
                                  'Did not create a config object')
            self.assertEqual(result.sections(), ['aa'],
                             'Should have found one configfile section.')
            self.assertEqual(result.options('aa'), ['bb'],
                             'Should have found one option.')
            self.assertEqual(result.get('aa', 'bb'), 'cc',
                             'Should have read a correct value.')
        os.remove(test_reading_file)

    def test_init_00_object(self):
        """ Verify that init returns good objects """
        for obj in self.configs['all']:
            self.assertIsInstance(obj, openvpn_client_connect.client_connect.ClientConnect)

    def test_init_01_protocol(self):
        """ Verify that init returns good protocols """
        for obj in self.configs['invalid']:
            self.assertIsNone(obj.proto,
                              'proto should be None on an empty config')
            self.assertIsNone(obj.min_version,
                              'min_version should be None on an empty config')
        for obj in self.configs['udps']:
            self.assertIsInstance(obj.proto, str,
                                  'proto must be a string')
            self.assertEqual(obj.proto, 'udp',
                             'proto must be udp')
        for obj in self.configs['tcps']:
            self.assertIsInstance(obj.proto, str,
                                  'proto must be a string')
            self.assertEqual(obj.proto, 'tcp',
                             'proto must be tcp')

    def test_init_02_dns(self):
        """ Verify that init returns good dns_servers """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.dns_servers, list,
                                  'dns_servers must be a list')
        for obj in self.configs['invalid']:
            self.assertIs(len(obj.dns_servers), 0,
                          'dns_servers should be [] on an empty config')
        for obj in self.configs['valid']:
            self.assertGreater(len(obj.dns_servers), 0,
                               'dns_servers must be a non-empty list')
            for addr in obj.dns_servers:
                try:
                    netaddr.IPNetwork(addr)
                except netaddr.core.AddrFormatError:  # pragma: no cover
                    self.fail('non-IP address in dns_servers')

    def test_init_03_domain(self):
        """ Verify that init returns good search_domains """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.search_domains, list,
                                  'search_domains must be a list')
        for obj in self.configs['invalid']:
            self.assertIs(len(obj.search_domains), 0,
                          'search_domains should be [] on an empty config')
        for obj in self.configs['valid']:
            # You do not have to provide any search_domains
            #self.assertGreater(len(obj.search_domains), 0,
            #    'search_domains must be a non-empty list')
            for addr in obj.search_domains:
                self.assertIsInstance(addr, str,
                                      'search_domains must contain strings')

    def test_init_04_officeipmapping(self):
        """ Verify that init returns good office_ip_mapping """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.office_ip_mapping, dict,
                                  'static office_ip_mapping must be a dict')

        for obj in self.configs['invalid']:
            self.assertEqual(len(obj.office_ip_mapping), 0,
                             ('static office_ip_mapping should be '
                              'empty on null config'))

        for obj in self.configs['dynamics']:
            self.assertGreater(len(obj.office_ip_mapping), 0,
                               ('office_ip_mapping should not be '
                                'empty on a dynamic test'))
            for _key, val in obj.office_ip_mapping.items():
                self.assertIsInstance(val, (list, str),
                                      ('office_ip_mapping values '
                                       'must be lists or strings'))

        for obj in self.configs['staticonly']:
            self.assertEqual(len(obj.office_ip_mapping), 0,
                             ('office_ip_mapping should be '
                              'empty on a static test'))

    def test_init_05_routes(self):
        """ Verify that init returns good routes """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.routes, list,
                                  'static routes must be a list')

        for obj in self.configs['invalid']:
            self.assertEqual(len(obj.routes), 0,
                             'static routes must be empty on null config')

        for obj in self.configs['dynamiconly']:
            self.assertEqual(len(obj.routes), 0,
                             'static routes must be empty on a dynamic test')

        for obj in self.configs['statics']:
            self.assertGreater(len(obj.routes), 0,
                               ('static routes should not be '
                                'empty on a static test'))
            self.assertIsInstance(obj.routes[0], str,
                                  'static routes should be strings')

    def test_init_06_minversion(self):
        """ Verify that min_version is set. """
        for obj in self.configs['min_version_empty']:
            self.assertIsInstance(obj.min_version, (str, type(None)),
                                  'min_version must be None when absent')
        for obj in self.configs['min_version']:
            self.assertIsInstance(obj.min_version, (str, dict),
                                  'min_version must be a string or dict when present')

    def test_cliversion(self):
        """ Verify that client_version_allowed does the right things. """
        # It doesn't really matter who we grab, we're going to hack the
        # library ourselves for this test:
        library = self.configs['min_version'][0]
        _orig = library.min_version
        for minver in (None, {}):
            library.min_version = minver
            self.assertTrue(library.client_version_allowed(''))
            self.assertTrue(library.client_version_allowed('2.3.10'))
            self.assertTrue(library.client_version_allowed('2.4.6'))
        for minver in ('2.3', {'2': '2.3'}):
            library.min_version = minver
            self.assertFalse(library.client_version_allowed(''))
            self.assertTrue(library.client_version_allowed('2.3.10'))
            self.assertTrue(library.client_version_allowed('2.4.6'))
        for minver in ('2.4', {'2': '2.4'}):
            library.min_version = minver
            self.assertFalse(library.client_version_allowed(''))
            self.assertFalse(library.client_version_allowed('2.3.10'))
            self.assertTrue(library.client_version_allowed('2.4.6'))
        for minver in ('2.4.4', {'2': '2.4.4'}):
            library.min_version = minver
            self.assertFalse(library.client_version_allowed(''))
            self.assertFalse(library.client_version_allowed('2.3.10'))
            self.assertTrue(library.client_version_allowed('2.4.10'))
            # Someone experimented with rolling their own
            self.assertFalse(library.client_version_allowed('2.4_beta1'))
            self.assertTrue(library.client_version_allowed('2.5_beta3'))
            # ics-openvpn.blinkt.de follows master:
            self.assertFalse(library.client_version_allowed('2.3_master'))
            self.assertTrue(library.client_version_allowed('2.4_master'))
            self.assertTrue(library.client_version_allowed('2.5_master'))
            # Deny something unparseable-but-close
            self.assertFalse(library.client_version_allowed('2.5_m@ster'))

        # Debian started _git in 2022
        # Debian shipped _rc2 in 2023 as part of bookworm/12 and bullseye backports.
        for minver in ('2.5', {'2': '2.5'}):
            library.min_version = minver
            self.assertTrue(library.client_version_allowed('2.6_rc2'))
            self.assertTrue(library.client_version_allowed('2.6_git'))
        for minver in ('2.6', {'2': '2.6'}):
            library.min_version = minver
            self.assertTrue(library.client_version_allowed('2.6_rc2'))
            self.assertTrue(library.client_version_allowed('2.6_git'))
        for minver in ('2.6.1', {'2': '2.6.1'}):
            library.min_version = minver
            self.assertFalse(library.client_version_allowed('2.6_rc2'))
            self.assertTrue(library.client_version_allowed('2.6_git'))

        # This test suite will be a little funky.
        # 3 is greater than 2, so allow it...
        library.min_version = '2.4.4'
        self.assertTrue(library.client_version_allowed('3.git::58b92569'))
        self.assertTrue(library.client_version_allowed('3.git::728733ae:Release'))
        self.assertTrue(library.client_version_allowed('3.8.3connect1'))
        # 3 is explicitly missing, don't allow it...
        library.min_version = {'2': '2.4.4'}
        self.assertFalse(library.client_version_allowed('3.git::58b92569'))
        self.assertFalse(library.client_version_allowed('3.git::728733ae:Release'))
        self.assertFalse(library.client_version_allowed('3.8.3connect1'))
        # 3 is included, allow it.
        library.min_version = {'3': '3.8'}
        self.assertTrue(library.client_version_allowed('3.git::58b92569'))
        self.assertTrue(library.client_version_allowed('3.git::728733ae:Release'))
        self.assertTrue(library.client_version_allowed('3.8.3connect1'))

        # Make sure garbage values on the server fail closed:
        for minver in ('urfburf', {'q': 'urfburf'}):
            library.min_version = minver
            self.assertFalse(library.client_version_allowed(''))
            self.assertFalse(library.client_version_allowed('2.3.10'))
            self.assertFalse(library.client_version_allowed('2.4.10'))

        library.min_version = _orig

    def test_userid_allowed(self):
        """ Verify that userid_allowed calls outward """
        for obj in self.configs['all']:
            with mock.patch.object(openvpn_client_connect.per_user_configs,
                                   'user_may_vpn') as mock_usermay:
                obj.userid_allowed('someguy')
            mock_usermay.assert_called_once_with('someguy')

    def test_get_dns(self):
        """ Verify that get_dns_server_lines returns good lines """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.get_dns_server_lines(), list,
                                  'get_dns_server_lines must be a list')
        for obj in self.configs['invalid']:
            self.assertEqual(len(obj.get_dns_server_lines()), 0,
                             ('get_dns_server_lines must be '
                              'empty on null config'))
        for obj in self.configs['valid']:
            self.assertGreater(len(obj.get_dns_server_lines()), 0,
                               'get_dns_server_lines must be a populated list')
            for line in obj.get_dns_server_lines():
                self.assertIsInstance(line, str,
                                      ('get_dns_server_lines values '
                                       'should be strings'))
                self.assertRegex(line, 'push "dhcp-option DNS .*"',
                                 'must push a dhcp-option for DNS')

    def test_get_domains(self):
        """ Verify that get_search_domains_lines returns good lines """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.get_search_domains_lines(), list,
                                  'get_search_domains_lines must be a list')
            with mock.patch('iamvpnlibrary.IAMVPNLibrary', side_effect=RuntimeError):
                self.assertEqual(obj.get_search_domains_lines(), [],
                                 ('get_search_domains_lines must be '
                                  'empty on failed IAM'))
        for obj in self.configs['invalid']:
            self.assertEqual(len(obj.get_search_domains_lines()), 0,
                             ('get_search_domains_lines must be '
                              'empty on null config'))
            with mock.patch('iamvpnlibrary.IAMVPNLibrary', side_effect=RuntimeError):
                self.assertEqual(obj.get_search_domains_lines(), [],
                                 ('get_search_domains_lines must be '
                                  'empty on failed IAM'))
        for obj in self.configs['valid']:
            # You do not have to provide any search_domains
            #self.assertGreater(len(obj.get_search_domains_lines()), 0,
            #    'get_search_domains_lines must be a populated list')
            for line in obj.get_search_domains_lines():
                self.assertIsInstance(line, str,
                                      ('get_search_domains_lines values '
                                       'should be strings'))
                self.assertRegex(line, 'push "dhcp-option DOMAIN .*"',
                                 'must push a dhcp-option for DOMAIN')
            with mock.patch('iamvpnlibrary.IAMVPNLibrary', side_effect=RuntimeError):
                self.assertEqual(obj.get_search_domains_lines(), [],
                                 ('get_search_domains_lines must be '
                                  'empty on failed IAM'))

    def test_get_staticroutelines(self):
        """ Verify that get_static_route_lines returns good lines """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.get_static_route_lines(), list,
                                  'get_static_route_lines must be a list')
        for obj in self.configs['invalid']:
            self.assertEqual(len(obj.get_static_route_lines()), 0,
                             ('get_static_route_lines must be '
                              'empty on null config'))
        for obj in self.configs['dynamiconly']:
            self.assertEqual(len(obj.get_static_route_lines()), 0,
                             ('get_static_route_lines must be '
                              'empty on dynamic config'))
        for obj in self.configs['statics']:
            self.assertGreater(len(obj.get_static_route_lines()), 0,
                               ('get_static_route_lines must be '
                                'a populated list'))
            for line in obj.get_static_route_lines():
                self.assertIsInstance(line, str,
                                      ('get_static_route_lines values '
                                       'should be strings'))
                self.assertRegex(line, 'push "route .*"',
                                 'must push a route')

    def test_get_dynamicroutelines(self):
        """ Verify that get_dynamic_route_lines returns good lines """
        # IMPROVEME - at some point in the future, we will need to provide
        # a real user here.  However, we presently don't care about the user
        # name, so we have static argument fillers.
        if not self.users.has_section('testing'):  # pragma: no cover
            raise self.skipTest('No testing section defined')
        if not self.users.has_option('testing', 'normal_user'):  # pragma: no cover
            raise self.skipTest('No testing/normal_user defined')
        normal_user = self.users.get('testing', 'normal_user')
        for obj in self.configs['all']:
            result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                 client_ip=self.test_office_ip)
            self.assertIsInstance(result, list,
                                  'get_dynamic_route_lines must be a list')
            with mock.patch('iamvpnlibrary.IAMVPNLibrary', side_effect=RuntimeError):
                result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                     client_ip=self.test_office_ip)
                self.assertEqual(result, [],
                                 'get_dynamic_route_lines must be empty on failed IAM')
        for obj in self.configs['invalid']:
            result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                 client_ip=self.test_office_ip)
            self.assertEqual(len(result), 0,
                             ('get_dynamic_route_lines must be empty on null config'))
            with mock.patch('iamvpnlibrary.IAMVPNLibrary', side_effect=RuntimeError):
                result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                     client_ip=self.test_office_ip)
                self.assertEqual(result, [],
                                 'get_dynamic_route_lines must be empty on failed IAM')
        for obj in self.configs['staticonly']:
            result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                 client_ip=self.test_office_ip)
            self.assertEqual(len(result), 0,
                             ('get_dynamic_route_lines must be empty on static config'))
            with mock.patch('iamvpnlibrary.IAMVPNLibrary', side_effect=RuntimeError):
                result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                     client_ip=self.test_office_ip)
                self.assertEqual(result, [],
                                 'get_dynamic_route_lines must be empty on failed IAM')
        for obj in self.configs['dynamics']:
            result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                 client_ip=self.test_office_ip)
            self.assertGreater(len(result), 0,
                               'get_dynamic_route_lines must be a populated list')
            for line in result:
                self.assertIsInstance(line, str,
                                      'get_dynamic_route_lines values should be strings')
                self.assertRegex(line, 'push "route .*"',
                                 'must push a route')
            with mock.patch('iamvpnlibrary.IAMVPNLibrary', side_effect=RuntimeError):
                result = obj.get_dynamic_route_lines(username_is=normal_user,
                                                     client_ip=self.test_office_ip)
                self.assertEqual(result, [],
                                 'get_dynamic_route_lines must be empty on failed IAM')

    def test_get_protocol(self):
        """ Verify that init returns good protocols """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.get_protocol_lines(), list,
                                  'get_protocol_lines must be a list')
        for obj in self.configs['invalid']:
            self.assertEqual(len(obj.get_protocol_lines()), 0,
                             ('get_protocol_lines must be empty '
                              'on a null config'))
        for obj in self.configs['tcps']:
            self.assertEqual(len(obj.get_protocol_lines()), 0,
                             ('get_protocol_lines must be empty '
                              'on a non-udp config'))
        for obj in self.configs['udps']:
            self.assertEqual(len(obj.get_protocol_lines()), 1,
                             'get_protocol_lines must exist on udp config')
            for line in obj.get_protocol_lines():
                self.assertIsInstance(line, str,
                                      ('get_protocol_lines values must be strings'))
                self.assertRegex(line, 'push "explicit-exit-notify .*"',
                                 'must push an exit-notify')
