#!/usr/bin/python
""" Test suite for the openvpn_client_connect class """
import unittest
import sys
import netaddr
sys.path.insert(1, 'iamvpnlibrary')
from openvpn_client_connect import ClientConnect  # pylint: disable=wrong-import-position
sys.dont_write_bytecode = True


class TestClass(unittest.TestCase):
    """ Class of tests """

    def setUp(self):
        """ Preparing test rig """
        self.test_office_ip = '127.0.0.2'
        noconf = ClientConnect('test_configs/nosuchfile.conf')
        empty = ClientConnect('test_configs/empty.conf')
        udp_dyn = ClientConnect('test_configs/udp_dynamic.conf')
        tcp_dyn = ClientConnect('test_configs/tcp_dynamic.conf')
        udp_stat = ClientConnect('test_configs/udp_static.conf')
        tcp_stat = ClientConnect('test_configs/tcp_static.conf')
        doubleup = ClientConnect('test_configs/doubleup.conf')
        self.configs = {
            'dynamics': [udp_dyn, tcp_dyn, doubleup],
            'dynamiconly': [udp_dyn, tcp_dyn],
            'statics': [udp_stat, tcp_stat, doubleup],
            'staticonly': [udp_stat, tcp_stat],
            'udps': [udp_dyn, udp_stat, doubleup],
            'tcps': [tcp_dyn, tcp_stat],
            'invalid': [noconf, empty],
            'valid': [udp_dyn, tcp_dyn,
                      udp_stat, tcp_stat,
                      doubleup, ],
            'all': [noconf, empty,
                    udp_dyn, tcp_dyn,
                    udp_stat, tcp_stat,
                    doubleup, ],
            }
        # pylint: disable=protected-access
        self.users = empty._ingest_config_from_file('test_configs/testing_users.conf')

    def test_init_0_object(self):
        """ Verify that init returns good objects """
        for obj in self.configs['all']:
            self.assertIsInstance(obj, ClientConnect)

    def test_init_1_protocol(self):
        """ Verify that init returns good protocols """
        for obj in self.configs['invalid']:
            self.assertIsNone(obj.proto,
                              'proto should be None on an empty config')
        for obj in self.configs['udps']:
            self.assertIsInstance(obj.proto, basestring,
                                  'proto must be a string')
            self.assertEqual(obj.proto, 'udp',
                             'proto must be udp')
        for obj in self.configs['tcps']:
            self.assertIsInstance(obj.proto, basestring,
                                  'proto must be a string')
            self.assertEqual(obj.proto, 'tcp',
                             'proto must be tcp')

    def test_init_2_dns(self):
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

    def test_init_3_domain(self):
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
                self.assertIsInstance(addr, basestring,
                                      'search_domains must contain strings')

    def test_init_4_officeipmapping(self):
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
            for _key, val in obj.office_ip_mapping.iteritems():
                self.assertIsInstance(val, basestring,
                                      ('office_ip_mapping values '
                                       'should be strings'))

        for obj in self.configs['staticonly']:
            self.assertEqual(len(obj.office_ip_mapping), 0,
                             ('office_ip_mapping should be '
                              'empty on a static test'))

    def test_init_5_routes(self):
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
            self.assertIsInstance(obj.routes[0], basestring,
                                  'static routes should be strings')

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
                self.assertIsInstance(line, basestring,
                                      ('get_dns_server_lines values '
                                       'should be strings'))
                self.assertRegexpMatches(line, 'push "dhcp-option DNS .*"',
                                         'must push a dhcp-option for DNS')

    def test_get_domains(self):
        """ Verify that get_search_domains_lines returns good lines """
        for obj in self.configs['all']:
            self.assertIsInstance(obj.get_search_domains_lines(), list,
                                  'get_search_domains_lines must be a list')
        for obj in self.configs['invalid']:
            self.assertEqual(len(obj.get_search_domains_lines()), 0,
                             ('get_search_domains_lines must be '
                              'empty on null config'))
        for obj in self.configs['valid']:
            # You do not have to provide any search_domains
            #self.assertGreater(len(obj.get_search_domains_lines()), 0,
            #    'get_search_domains_lines must be a populated list')
            for line in obj.get_search_domains_lines():
                self.assertIsInstance(line, basestring,
                                      ('get_search_domains_lines values '
                                       'should be strings'))
                self.assertRegexpMatches(line, 'push "dhcp-option DOMAIN .*"',
                                         'must push a dhcp-option for DOMAIN')

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
                self.assertIsInstance(line, basestring,
                                      ('get_static_route_lines values '
                                       'should be strings'))
                self.assertRegexpMatches(line, 'push "route .*"',
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
            result = obj.get_dynamic_route_lines(normal_user, self.test_office_ip)
            self.assertIsInstance(result, list,
                                  'get_dynamic_route_lines must be a list')
        for obj in self.configs['all']:
            result = obj.get_dynamic_route_lines(normal_user, self.test_office_ip)
            self.assertIsInstance(result, list,
                                  'get_dynamic_route_lines must be a list')
        for obj in self.configs['invalid']:
            result = obj.get_dynamic_route_lines(normal_user, self.test_office_ip)
            self.assertEqual(len(result), 0,
                             ('get_dynamic_route_lines must '
                              'be empty on null config'))
        for obj in self.configs['staticonly']:
            result = obj.get_dynamic_route_lines(normal_user, self.test_office_ip)
            self.assertEqual(len(result), 0,
                             ('get_dynamic_route_lines must '
                              'be empty on static config'))
        for obj in self.configs['dynamics']:
            result = obj.get_dynamic_route_lines(normal_user, self.test_office_ip)
            self.assertGreater(len(result), 0,
                               ('get_dynamic_route_lines must be '
                                'a populated list'))
            for line in result:
                self.assertIsInstance(line, basestring,
                                      ('get_dynamic_route_lines values '
                                       'should be strings'))
                self.assertRegexpMatches(line, 'push "route .*"',
                                         'must push a route')

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
                self.assertIsInstance(line, basestring,
                                      ('get_protocol_lines values '
                                       'must be strings'))
                self.assertRegexpMatches(line,
                                         'push "explicit-exit-notify .*"',
                                         'must push an exit-notify')
