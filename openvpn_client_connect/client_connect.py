"""
    Script to give VPN clients their runtime config.
    Mostly focused on routes, dns, and search domains.
"""
import os
import sys
import ast
import re
import configparser
import netaddr
import openvpn_client_connect.per_user_configs
from openvpn_client_connect.per_user_configs \
    import GetUserRoutes, GetUserSearchDomains
sys.dont_write_bytecode = True


def versioncompare(arg1, arg2):
    """
        compare version-string numbers
        0 = they're identical
        1 = arg1 is greater
        2 = arg2 is greater
        example: 1.3.4 and 1.4 would return 2.

        There is opportunity to improve this using modules like semver
        but that introduces extra dependencies.  OpenVPN doesn't currently
        use prerelease coding (that we care about?) so we're coding our own
        version here.
    """
    verstr1 = arg1.split('.')
    verstr2 = arg2.split('.')
    if len(verstr1) > len(verstr2):
        maxlength = len(verstr1)
    else:
        maxlength = len(verstr2)

    for i in range(maxlength):
        try:
            match1 = re.match(r'^(\d+)', verstr1[i])
        except IndexError:
            return 2
        try:
            match2 = re.match(r'^(\d+)', verstr2[i])
        except IndexError:
            return 1

        try:
            item1 = int(match1.group(1))
        except AttributeError:
            item1 = 0
        try:
            item2 = int(match2.group(1))
        except AttributeError:
            item2 = 0

        if item1 > item2:
            return 1
        if item1 < item2:
            return 2
    return 0


class ClientConnect:
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
        self.min_version = None
        if _config.has_section('client-connect'):
            if _config.has_option('client-connect', 'protocol'):
                self.proto = _config.get('client-connect', 'protocol')

            try:
                self.min_version = ast.literal_eval(
                    _config.get('client-connect', 'minimum-version'))
            except configparser.NoOptionError:
                pass
            except SyntaxError:
                # It's possible to have a 2.x.y string in a config file with no quotes.
                # If that runs through eval, you'll explode because it looks like a broken
                # float instead of a string.
                # If that's the case, give another try:
                self.min_version = _config.get('client-connect', 'minimum-version')
            if not isinstance(self.min_version, (str, dict)):
                self.min_version = None

            try:
                self.dns_servers = ast.literal_eval(
                    _config.get('client-connect', 'GLOBAL_DNS_SERVERS'))
            except configparser.NoOptionError:
                pass
            if not isinstance(self.dns_servers, list):
                self.dns_servers = []

            try:
                self.search_domains = ast.literal_eval(
                    _config.get('client-connect', 'GLOBAL_SEARCH_DOMAINS'))
            except configparser.NoOptionError:
                pass
            if not isinstance(self.search_domains, list):
                self.search_domains = []

        self.office_ip_mapping = {}
        if _config.has_section('dynamic-mapping'):
            try:
                self.office_ip_mapping = ast.literal_eval(
                    _config.get('dynamic-mapping', 'OFFICE_IP_MAPPING'))
            except configparser.NoOptionError:
                pass
            if not isinstance(self.office_ip_mapping, dict):
                self.office_ip_mapping = {}

        self.routes = []
        if _config.has_section('static-mapping'):
            try:
                self.routes = ast.literal_eval(
                    _config.get('static-mapping', 'ROUTES'))
            except configparser.NoOptionError:
                pass
            if not isinstance(self.routes, list):
                self.routes = []

    @staticmethod
    def _ingest_config_from_file(conf_file):
        """
            pull in config variables from a system file
        """
        if not isinstance(conf_file, list):
            conf_file = [conf_file]
        config = configparser.ConfigParser()
        for filename in conf_file:
            if os.path.isfile(filename):
                try:
                    config.read(filename)
                    break
                except configparser.Error:
                    pass
        # Note that there's no 'else' here.  You could have no config file.
        # The init will assume default values where there's no config.
        return config

    def client_version_allowed(self, client_version):
        """
            Check if the client has a version above our minimum requirements.
        """
        if self.min_version is None:
            # We have no minimums, so any client is good.
            return True
        if not self.min_version:
            # We have no minimums, so any client is good.
            return True
        family_match = re.match(r'^(\d+)', client_version)
        if family_match is None:
            # We have a server minimum version but no client version:
            # The client didn't tell us what version they are.  That's either
            # an error, or a pre-2.3 client. (2.3 is when IV_VER was added)
            #
            # We are going to assume that anyone who cares about doing version
            # match/filtering cares enough to say "before-2.3 is too old."
            return False
        family_number = family_match.group(1)
        server_min_version = None
        if isinstance(self.min_version, str):
            server_min_version = self.min_version
        elif isinstance(self.min_version, dict):
            server_min_version = self.min_version.get(family_number)
        if server_min_version is None:
            # The client version came in as 3 and you only had keys for 2, or something
            # like that.  As such, we fail you out.
            return False
        if re.match(r'^\d+\.\d+(?:\.\d+)?$', server_min_version) is None:
            # Someone has put in a wacky minimum version on some option.
            # There's no way we can know what to do here.  We're going to
            # fail-closed, because that's safer and anyone using a dict
            # here should know better.
            return False
        if re.match(r'^\d+\.\d+(?:\.\d+)?$', client_version) is None:
            # We have a poorly-formed client version.  This section is basically
            # going to handle the edge cases we've found over time.
            beta_match = re.match(r'^(\d+\.\d+)_(?:beta\d+|rc\d+)$', client_version)
            if beta_match:
                # beta is pre-release, but round up to .0
                return self.client_version_allowed(beta_match.group(1))
            gitmaster_match = re.match(r'^(\d+\.\d+)_(?:master|git)$', client_version)
            if gitmaster_match:
                # _master is going to be considered the latest version in a family.
                version_before_master = gitmaster_match.group(1)
                fake_version = f'{version_before_master}.999999'
                return self.client_version_allowed(fake_version)
            gitcolon_match = re.match(r'^(\d+)\.git::', client_version)
            if gitcolon_match:
                # git is going to be considered the latest version in a family.
                version_before_colon = gitcolon_match.group(1)
                fake_version = f'{version_before_colon}.999999'
                return self.client_version_allowed(fake_version)
            connect_match = re.match(r'^(\d+\.\d+(?:\.\d+)?)connect\d+$', client_version)
                # OpenVPN Connect is a family of apps (usually for mobile) which has
                # a completely different numbering scheme.  OpenVPN Connect is based on
                # openvpn3, so if you do a version comparison here on the 2 family of
                # the server, that's naive and going to be "yeah, 3 is bigger than 2".
                # You want to do some minimum-versioning on the 3 family, by making
                # minimum-version be set in your config file.
            if connect_match:
                return self.client_version_allowed(connect_match.group(1))
            # At this point, we have a weird client version we've never seen
            # and haven't defined a way to handle.  Gotta say no.
            return False
        # We have a well-formed client version,
        # We have a server minimum version, and a client reported version.
        if versioncompare(server_min_version, client_version) == 1:
            # Our min_version is greater than your client version.  Sorry.
            return False
        return True

    @staticmethod
    def userid_allowed(userid):
        """
            Check if a user is allowed to VPN.
            This is a somewhat-early authorization check.
        """
        return openvpn_client_connect.per_user_configs.user_may_vpn(userid)

    def get_dns_server_lines(self):
        """
            Return the push lines for a user to have DNS servers.
        """
        return_lines = []
        for server in self.dns_servers:
            _line = f'push "dhcp-option DNS {server}"'
            return_lines.append(_line)
        return return_lines

    def get_search_domains_lines(self, username_is=None, username_as=None):
        """
            Return the push lines for a user to have DNS search domains.
            We will do extra domains for certain users.
            ... someday.
        """
        gusd = GetUserSearchDomains(self.configfile)
        if gusd.iam_searcher:
            effective_username = gusd.iam_searcher.verify_sudo_user(username_is, username_as)
            domains = gusd.get_search_domains(effective_username)
        else:
            domains = []
        return_lines = []
        for server in domains:
            _line = f'push "dhcp-option DOMAIN {server}"'
            return_lines.append(_line)
        return return_lines

    def get_static_route_lines(self):
        """
            Return the push lines for all static-defined routes.
        """
        return_lines = []
        for route_line in self.routes:
            _line = f'push "route {route_line}"'
            return_lines.append(_line)
        return return_lines

    def get_dynamic_route_lines(self, username_is, username_as=None, client_ip=None):
        """
            Return the push lines for dynamic/per-user routes.
        """
        return_lines = []
        if self.office_ip_mapping:
            user_at_office = None
            # Is this an office connection?
            if client_ip is not None:
                client_ip_cidr = netaddr.IPNetwork(client_ip)
                for site, site_ip in self.office_ip_mapping.items():
                    if isinstance(site_ip, list):
                        # site_ip is a list of possible IPs for the office
                        site_list = site_ip
                    else:
                        # site_ip is not a list, and thus is (assumed)
                        # a string of the office IP
                        site_list = [site_ip]
                    for addr in site_list:
                        cidr = netaddr.IPNetwork(addr)
                        if client_ip_cidr in cidr:
                            user_at_office = site
                            break

            gur = GetUserRoutes(self.configfile)
            if gur.iam_searcher:
                effective_username = gur.iam_searcher.verify_sudo_user(username_is, username_as)
                user_routes = gur.build_user_routes(effective_username,
                                                    user_at_office,
                                                    client_ip)
            else:
                user_routes = []

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
