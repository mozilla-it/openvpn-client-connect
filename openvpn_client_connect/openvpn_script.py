"""
    Script to give VPN clients their runtime config.
    Mostly focused on routes, dns, and search domains.
"""
import os
import sys
from argparse import ArgumentParser
import openvpn_client_connect.client_connect
sys.dont_write_bytecode = True


def client_version_allowed(config_object, client_version):
    """
        Check our client version against the config'ed minimums
    """
    return config_object.client_version_allowed(client_version)

def userid_allowed(config_object, userid):
    """
        Check if the user is allowed to connect.
        With the use of auth-gen-token a connection may happen that
        does not go through auth-user-pass-verify, which means we need
        to do an authorization check that we formerly didn't need to do.
    """
    return config_object.userid_allowed(userid)

def build_lines(config_object, username_is, username_as, client_ip):
    """
        Create the contents of the lines that should be returned
        to the connecting client.
    """
    output_array = []
    output_array += config_object.get_dns_server_lines()
    output_array += config_object.get_search_domains_lines(username_is=username_is,
                                                           username_as=username_as)
    output_array += config_object.get_dynamic_route_lines(username_is=username_is,
                                                          username_as=username_as,
                                                          client_ip=client_ip)
    output_array += config_object.get_static_route_lines()
    output_array += config_object.get_protocol_lines()
    return output_array


def main_work(argv):
    """
        Print the config that should go to each client into a file.
        Return True on success, False upon failure.
        Side effect is that we write to the output_filename.
    """
    # We will push routes/configs to the configuration filename
    # we're given as the LAST argument in reality there's usually
    # only one arg, but, that's the spec.
    parser = ArgumentParser(description='Args for client-connect')
    parser.add_argument('--conf', type=str, required=True,
                        help='Config file',
                        dest='conffile', default=None)
    parser.add_argument('output_filename', type=str,
                        help='Filename to push config to')
    args = parser.parse_args(argv[1:])

    # 2.2 did not send IV_VER.
    # 2.3+ clients send IV_VER.
    # A 2.3 server, if sent IV_VER, does not send it to the script.
    # 2.4 clients and servers are all well-behaved.
    # Basically: "this can be blank"... (but see later)
    client_version_string = os.environ.get('IV_VER')

    # common_name is an environmental variable passed in:
    # "The X509 common name of an authenticated client."
    # https://openvpn.net/index.php/open-source/documentation/manuals/65-openvpn-20x-manpage.html
    usercn = os.environ.get('common_name')
    trusted_ip = os.environ.get('trusted_ip')
    unsafe_username = os.environ.get('username')

    # Super failure in openvpn, or hacking, or an improper test from a human.
    if not usercn:
        print('No common_name or username environment variable provided.')
        return False
    if not trusted_ip:
        print('No trusted_ip environment variable provided.')
        return False
    # We're now at the point where anything NOT sending IV_VER is too broken to tolerate.
    if not client_version_string:
        print('No IV_VER environment variable provided.')
        return False

    config_object = openvpn_client_connect.client_connect.ClientConnect(args.conffile)

    if not client_version_allowed(config_object, client_version_string):
        return False

    if not userid_allowed(config_object, usercn):
        return False

    output_array = build_lines(
        config_object=config_object,
        username_is=usercn,
        username_as=unsafe_username,
        client_ip=trusted_ip,
    )
    output_lines = '\n'.join(output_array) + '\n'

    try:
        with open(args.output_filename, 'w', encoding='utf-8') as filehandle:
            filehandle.write(output_lines)
    except IOError:
        # I couldn't write to the file, so we can't tell openvpn what
        # happened.  There's nothing to do but error out.
        return False
    return True

def main():
    """ Interface to the outside """
    if main_work(sys.argv):
        sys.exit(0)
    sys.exit(1)

if __name__ == '__main__':  # pragma: no cover
    main()
