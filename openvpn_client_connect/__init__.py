#!/usr/bin/python
"""
    Script to give VPN clients their runtime config.
    Mostly focused on routes, dns, and search domains.
"""
import os
import sys
import ast
from openvpn_client_connect.per_user_configs \
    import GetUserRoutes, GetUserSearchDomains
sys.dont_write_bytecode = True

try:
    # 2.7's module:
    from ConfigParser import SafeConfigParser as ConfigParser
except ImportError:  # pragma: no cover
    # 3's module:
    from configparser import ConfigParser


def versioncompare(arg1, arg2):
    """
        compare version-string numbers
        0 = they're identical
        1 = arg1 is greater
        2 = arg2 is greater
        example: 1.3.4 and 1.4 would return 2.
    """
    verstr1 = arg1.split('.')
    verstr2 = arg2.split('.')
    if len(verstr1) > len(verstr2):
        maxlength = len(verstr1)
    else:
        maxlength = len(verstr2)

    for i in range(maxlength):
        try:
            item1 = verstr1[i]
        except IndexError:
            item1 = 0
        try:
            item2 = verstr2[i]
        except IndexError:
            item2 = 0

        if item1 > item2:
            return 1
        elif item1 < item2:
            return 2
    return 0


def max_route_lines(versionstring):
    """
        Determine if the client connecting needs to be told about
        route limits.
    """
    return_lines = []
    if not versionstring:
        # This is either a 2.2 client, or a 2.3 server that isn't told
        # anything.  Assume the former.
        return_lines.append('push "max-routes 200"')
    elif versioncompare('2.4', versionstring) == 1:
        # 1 means A>B :  2.4 is greater than the client's version
        #
        # clients before 2.4 (2.2 and before don't send IV_VER, 2.3 does):
        #     allow for up to 200 routes client-side (note that the server
        #     will allow max 256 routes per client by default)
        return_lines.append('push "max-routes 200"')
    else:
        # clients 2.4 and after:
        #     max-routes has gone away: don't push this at all.
        pass
    return return_lines


class ClientConnect(object):
    """
        This is mainly implemented as a class because it's an easier way to
        keep track of our config-file based configuration.  For the most part
        this class acts as a utility that you query for information about a
        user.  In that sense, it's pretty close to a straightforward script.
    """

    def __init__(self, conf_file):
        """
            ingest the config file so other methods can use it
        """
        self.configfile = conf_file
        _config = self._ingest_config_from_file(conf_file)

        self.dns_servers = []
        self.search_domains = []
        self.proto = None
        if _config.has_section('client-connect'):
            if _config.has_option('client-connect', 'protocol'):
                self.proto = _config.get('client-connect', 'protocol')

            try:
                self.dns_servers = ast.literal_eval(
                    _config.get('client-connect', 'GLOBAL_DNS_SERVERS'))
            except:  # pylint: disable=bare-except
                # This bare-except is due to 2.7 limitations in configparser.
                pass
            if not isinstance(self.dns_servers, list):  # pragma: no cover
                self.dns_servers = []

            try:
                self.search_domains = ast.literal_eval(
                    _config.get('client-connect', 'GLOBAL_SEARCH_DOMAINS'))
            except:  # pylint: disable=bare-except
                # This bare-except is due to 2.7 limitations in configparser.
                pass
            if not isinstance(self.search_domains, list):  # pragma: no cover
                self.search_domains = []

        self.office_ip_mapping = {}
        if _config.has_section('dynamic-mapping'):
            try:
                self.office_ip_mapping = ast.literal_eval(
                    _config.get('dynamic-mapping', 'OFFICE_IP_MAPPING'))
            except:  # pylint: disable=bare-except
                # This bare-except is due to 2.7 limitations in configparser.
                pass
            if not isinstance(self.office_ip_mapping, dict):  # pragma: no cover
                self.office_ip_mapping = {}

        self.routes = []
        if _config.has_section('static-mapping'):
            try:
                self.routes = ast.literal_eval(
                    _config.get('static-mapping', 'ROUTES'))
            except:  # pylint: disable=bare-except
                # This bare-except is due to 2.7 limitations in configparser.
                pass
            if not isinstance(self.routes, list):  # pragma: no cover
                self.routes = []

    @staticmethod
    def _ingest_config_from_file(conf_file):
        """
            pull in config variables from a system file
        """
        if isinstance(conf_file, basestring):
            conf_file = [conf_file]
        config = ConfigParser()
        for filename in conf_file:
            if os.path.isfile(filename):
                try:
                    config.read(filename)
                    break
                except:  # pragma: no cover  pylint: disable=bare-except
                    # This bare-except is due to 2.7
                    # limitations in configparser.
                    pass
        # Note that there's no 'else' here.  You could have no config file.
        # The init will assume default values where there's no config.
        return config

    def get_dns_server_lines(self):
        """
            Return the push lines for a user to have DNS servers.
        """
        return_lines = []
        for server in self.dns_servers:
            _line = 'push "dhcp-option DNS {}"'.format(server)
            return_lines.append(_line)
        return return_lines

    def get_search_domains_lines(self, username=None):
        """
            Return the push lines for a user to have DNS search domains.
            We will do extra domains for certain users.
            ... someday.
        """
        gusd = GetUserSearchDomains(self.configfile)
        domains = gusd.get_search_domains(username)
        return_lines = []
        for server in domains:
            _line = 'push "dhcp-option DOMAIN {}"'.format(server)
            return_lines.append(_line)
        return return_lines

    def get_static_route_lines(self):
        """
            Return the push lines for all static-defined routes.
        """
        return_lines = []
        for route_line in self.routes:
            _line = 'push "route {}"'.format(route_line)
            return_lines.append(_line)
        return return_lines

    def get_dynamic_route_lines(self, client_username, client_ip):
        """
            Return the push lines for dynamic/per-user routes.
        """
        return_lines = []
        if self.office_ip_mapping:
            # Is this an office connection?
            for site, site_ip in self.office_ip_mapping.items():
                if isinstance(site_ip, list):
                    # site_ip is a list of possible IPs for the office
                    if client_ip in site_ip:
                        user_at_office = site
                        break
                else:
                    # site_ip is not a list, and thus is (assumed)
                    # a string of the office IP
                    if client_ip == site_ip:
                        user_at_office = site
                        break
            else:
                user_at_office = None

            gur = GetUserRoutes(self.configfile)
            user_routes = gur.build_user_routes(client_username,
                                                user_at_office)

            for net_obj in user_routes:
                # For one entry per line, remove the trailing comma
                _base = 'push "route {network} {netmask}"'
                _line = _base.format(network=net_obj.network,
                                     netmask=net_obj.netmask)
                return_lines.append(_line)
        return return_lines

    def get_protocol_lines(self):
        """
            Return the push lines depending upon what openvpn protocol
            this instance is using.
        """
        return_lines = []
        if self.proto == 'udp':
            # UDP does not send an explicit exit notification on
            # client shutdown, which is just STUPID.
            return_lines.append('push "explicit-exit-notify 2"')
        return return_lines
