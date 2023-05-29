"""
    This script's job is generate a list of ROUTES that a user
    is entitled to have access to, and should be pushed upon VPN connect.

    Future thoughts:
        this should ship with a client-connect script.
        this should do a much smarter job of offering per-office routes.
"""
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contributors:
# gcox@mozilla.com
# jdow@mozilla.com
#
# Requires:
# iamvpnlibrary
# netaddr

import os
import sys
import ast
import six
from six.moves import configparser
from netaddr import IPNetwork, cidr_merge, cidr_exclude
import iamvpnlibrary
sys.dont_write_bytecode = True
#try:
#    import configparser
#except ImportError:  # pragma: no cover
#    from six.moves import configparser

__all__ = ['GetUserRoutes', 'GetUserSearchDomains', 'user_may_vpn']

def user_may_vpn(userid):
    '''
        Check if a user is allowed to VPN in or not
    '''
    iam_searcher = iamvpnlibrary.IAMVPNLibrary()
    return iam_searcher.user_allowed_to_vpn(userid)

class GetUserRoutes(object):
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

        try:
            _freeroutes = ast.literal_eval(
                _config.get('dynamic-mapping', 'FREE_ROUTES'))
        except:  # pylint: disable=bare-except
            # This bare-except is due to 2.7 limitations in configparser.
            _freeroutes = []
        if not isinstance(_freeroutes, list):  # pragma: no cover
            _freeroutes = []

        try:
            _officeroutes = ast.literal_eval(
                _config.get('dynamic-mapping',
                            'COMPREHENSIVE_OFFICE_ROUTES'))
        except:  # pylint: disable=bare-except
            # This bare-except is due to 2.7 limitations in configparser.
            _officeroutes = []
        if not isinstance(_officeroutes, list):  # pragma: no cover
            _officeroutes = []

        try:
            _perofficeroutes = ast.literal_eval(
                _config.get('dynamic-mapping', 'PER_OFFICE_ROUTES'))
        except:  # pylint: disable=bare-except
            # This bare-except is due to 2.7 limitations in configparser.
            _perofficeroutes = {}
        if not isinstance(_perofficeroutes, dict):  # pragma: no cover
            _perofficeroutes = {}

        config = {}
        config['FREE_ROUTES'] = [IPNetwork(routestr)
                                 for routestr in _freeroutes]
        config['COMPREHENSIVE_OFFICE_ROUTES'] = [IPNetwork(routestr)
                                                 for routestr in _officeroutes]
        config['PER_OFFICE_ROUTES'] = {office: IPNetwork(routestr)
                                       for office, routestr in
                                       _perofficeroutes.items()}
        self.config = config
        try:
            self.iam_searcher = iamvpnlibrary.IAMVPNLibrary()
        except RuntimeError:
            # Couldn't connect to the IAM service:
            self.iam_searcher = None

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
                except (configparser.Error):
                    pass
        # Note that there's no 'else' here.  You could have no config file.
        # The init will assume default values where there's no config.
        return config

    @staticmethod
    def route_subtraction(myroutes, coverage_routes):
        """
            This script compacts a list of routes.
            Checks each route in A and removes it if a route in B covers it.
        """
        returnlist = []
        for myroute in myroutes:
            for coverage_route in coverage_routes:
                if myroute in coverage_route:
                    break
            else:
                returnlist.append(myroute)
        return returnlist

    @staticmethod
    def route_exclusion(myroutes, remove_routes):
        """
            This script shrinks route sizes.
            Checks each route in A and B's piece of it.
            Note that this is vastly different from route_subtraction
        """
        # This is a little twisty to read.  When you exclude a subnet
        # B from a larger subnet A, you end up with a list of smaller
        # subnets.  That means, if you have multiple B's, you need
        # to progressively keep the list A updated, so that each B is
        # removed from the ever-longer list of smaller A's.
        # This is probably overkill, since we only really do one extract
        # of B, but, just in case.
        if not isinstance(myroutes, list):
            myroutes = [myroutes]
        if not isinstance(remove_routes, list):
            remove_routes = [remove_routes]
        for remove_route in remove_routes:
            newroutelist = []
            for myroute in myroutes:
                newroutelist = (newroutelist +
                                cidr_exclude(myroute, remove_route))
            myroutes = newroutelist
        return sorted(list(set(myroutes)))

    def get_office_routes(self, from_office):
        """
            This should provide the routes that someone would have,
            based on if they're in/out of an office.
        """
        if isinstance(from_office, bool):
            if from_office:
                user_office_routes = []
            else:
                user_office_routes = self.config['COMPREHENSIVE_OFFICE_ROUTES']
        elif isinstance(from_office, six.string_types):
            if from_office in self.config['PER_OFFICE_ROUTES']:
                user_office_routes = self.route_exclusion(
                    self.config['COMPREHENSIVE_OFFICE_ROUTES'],
                    self.config['PER_OFFICE_ROUTES'][from_office]
                    )
            else:
                user_office_routes = self.config['COMPREHENSIVE_OFFICE_ROUTES']
        else:
            # I don't know how we got here, but let's assume remote.
            user_office_routes = self.config['COMPREHENSIVE_OFFICE_ROUTES']
        return user_office_routes

    def build_user_routes(self, user_string, from_office):
        """
            This is the main function of the class, and builds out the
            routes we want to have available for a user, situationally
            modified for when they're in/out of the offices.

            returns a list of IPNetwork objects.
        """
        if not self.iam_searcher:
            # No connection to the IAM server
            return []
        # Get the user's ACLs:
        user_acl_strings = self.iam_searcher.get_allowed_vpn_ips(user_string)
        if not user_acl_strings:
            # If the user has NO acls, get out now.  We're probably in
            # a bad case where someone doesn't exist, or we've had an
            # upstream failure.  In any case, don't give any routes,
            # so as to provide the least privilege.
            return []
        #
        # user_acls is ['10.0.0.0/8', '192.168.50.0/24', ...]
        # a list of CIDR strings.  Since we're going to do a lot
        # of manipulation, we're going to turn these into
        # IPNetwork objects right off the bat.
        user_acls = [IPNetwork(aclstring) for aclstring in user_acl_strings]

        # First thing, take away "the routes we give everyone".
        # The user is going to get a universal route that is bigger
        # than certain pieces of their config'ed ACLs, so, let's
        # remove those from consideration for a moment.  The user will get
        # these routes back later, so this is just some housekeeping to
        # shrink the size of user_acls.
        user_acls = self.route_subtraction(
            user_acls, self.config['FREE_ROUTES'])
        #
        # Next, we are going to strip out ALL the office routes from
        # the user's ACL list.  The reason here is, their personal _ACLs_
        # are not the same as their situational _routes_.  They may have
        # an ACL to go to a certain box, but if they're in the same office,
        # we don't want them to have a ROUTE to it.  We will give them routes,
        # below, specific to how they're connecting to the VPN.  What we
        # DON'T want is a sysadmin with a big ACL coming along and having
        # that ACL dominating their routes later in this script while they're
        # in an office.
        user_acls = self.route_subtraction(
            user_acls, self.config['COMPREHENSIVE_OFFICE_ROUTES'])
        #
        # Having cleaned out, what is left is the things that a user has
        # an ACL to, that they need a ROUTE to.  So, rename it:
        user_specific_routes = user_acls

        # Now, bundle up the routes:
        # routes everyone gets, plus your personal routes...
        user_nonoffice_routes = sorted(
            cidr_merge(self.config['FREE_ROUTES'] + user_specific_routes))
        # ... plus your office routes, as calculated ...
        user_office_routes = self.get_office_routes(from_office)
        # ... equals ...
        all_routes = sorted(user_nonoffice_routes + user_office_routes)
        # Notice here, we do NOT cidr_merge at this final point.
        # The reason for this is, the user_office_routes are historically
        # a key separate route that people quickly eyeball for
        # presence/absence when triaging issues.
        #
        # If you cidr merge here, you CAN end up with something like
        # (10.X/9) instead of (10.X/10 and 10.Y/10), and if everyone is looking
        # for the Y, it can lead to false triage issues.
        #
        # In the future, this may bear reworking to move cidr_merge later in
        # the process, but we're not there yet.
        return all_routes


class GetUserSearchDomains(object):
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

        try:
            _search_domains = ast.literal_eval(
                _config.get('client-connect', 'GLOBAL_SEARCH_DOMAINS'))
        except:  # pylint: disable=bare-except
            # This bare-except is due to 2.7 limitations in configparser.
            _search_domains = []
        if not isinstance(_search_domains, list):  # pragma: no cover
            _search_domains = []
        self.search_domains = _search_domains

        try:
            _dynamic_dict = ast.literal_eval(
                _config.get('dynamic-dns-search', 'dns_search_domain_map'))
        except:  # pylint: disable=bare-except
            # This bare-except is due to 2.7 limitations in configparser.
            _dynamic_dict = {}
        if not isinstance(_dynamic_dict, dict):  # pragma: no cover
            _dynamic_dict = {}
        self.dynamic_dict = _dynamic_dict
        try:
            self.iam_searcher = iamvpnlibrary.IAMVPNLibrary()
        except RuntimeError:
            # Couldn't connect to the IAM service:
            self.iam_searcher = None

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
                except (configparser.Error):
                    pass
        # Note that there's no 'else' here.  You could have no config file.
        # The init will assume default values where there's no config.
        return config

    def build_search_domains(self, user_groups):
        """
            Build the set of search domains that should exist for someone
            who has a certain set of groups.
        """
        # The global domains form the base list:
        return_list = list(self.search_domains)
        #return_list = self.search_domains.copy()
        # Now, loop through the user's groups list
        for user_group in sorted(user_groups):
            # If their group has anything special associated with it,
            # We should do something.
            if user_group in self.dynamic_dict:
                # Find what we should add:
                value = self.dynamic_dict[user_group]
                if not isinstance(value, list):
                    value = [value]
                for candidate_domain in value:
                    if not isinstance(candidate_domain, six.string_types):
                        continue
                    if not candidate_domain:
                        # In case someone left a blank string:
                        continue
                    if candidate_domain in return_list:
                        continue
                    return_list.append(candidate_domain)
        return return_list

    def get_search_domains(self, user_string):
        """
            This is the main function of the class, and builds out the
            search domains we want to have available for a user

            returns a list of strings.
        """
        user_groups = []
        if user_string:
            if self.iam_searcher:
                # Get the user's ACLs:
                user_acls = self.iam_searcher.get_allowed_vpn_acls(user_string)
                #user_groups = list(set([x.rule for x in user_acls]))
                user_groups = list({x.rule for x in user_acls})
        return self.build_search_domains(user_groups)
