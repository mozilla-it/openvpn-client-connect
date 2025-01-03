"""
    This script's job is to print out a list of ROUTES that a user
    is entitled to have access to, and should be pushed upon VPN connect.

    This script is invoked as a second-tier script from our client-connect
    As such, we could have this script output pretty much anything we want
    so long as the message gets across.

    The output format is presently lines that look like:

    10.8.0.0 255.255.120.0

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

import sys
from argparse import ArgumentParser
from openvpn_client_connect.per_user_configs import GetUserRoutes
sys.dont_write_bytecode = True


def main_work(argv):
    """
        Handle argument parsing, build a route list, and print it.
    """
    parser = ArgumentParser(description='Args to control the CRL checking')
    parser.add_argument('--office-id', type=str, required=False,
                        help='Office that someone is connecting from',
                        dest='office_id', default=None)
    parser.add_argument('--trusted-ip', type=str, required=False,
                        help='IP of connecting client',
                        dest='client_ip', default=None)
    parser.add_argument('--conf', type=str, required=True,
                        help='Config file',
                        dest='conffile', default=None)
    parser.add_argument('username', type=str,
                        help='User that is connecting to us')
    args = parser.parse_args(argv[1:])

    gur = GetUserRoutes(args.conffile)
    user_routes = gur.build_user_routes(args.username, args.office_id, args.client_ip)

    # Finally, we need to output all the routes in a nice list of
    #    NETWORK SPACE NETMASK
    # that bash will be able to iterate over
    for net_object in user_routes:
        # For one entry per line, remove the trailing comma
        print(f'{net_object.network} {net_object.netmask}')

def main():
    """ Interface to the outside """
    main_work(sys.argv)
    sys.exit(0)

if __name__ == '__main__':  # pragma: no cover
    main()
