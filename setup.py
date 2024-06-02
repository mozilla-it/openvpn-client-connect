""" Setup script """

import os
import subprocess
from setuptools import setup

NAME = 'openvpn-client-connect'
VERSION = '1.4.2'


def git_version():
    """ Return the git revision as a string """
    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {}
        for envvar in ['SYSTEMROOT', 'PATH']:
            val = os.environ.get(envvar)
            if val is not None:
                env[envvar] = val
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               env=env).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        git_revision = out.strip().decode('ascii')
    except OSError:
        git_revision = u"Unknown"

    return git_revision

setup(
    name='openvpn-client-connect',
    version=VERSION,
    author="Greg Cox",
    author_email="gcox@mozilla.com",
    url="https://github.com/mozilla-it/openvpn-client-connect",
    description=("Calculates minimal user routes, given a user's VPN ACLs\n" +
                 'This package is built upon commit ' + git_version()),
    long_description=open('README.md').read(),
    license="MPL",
    install_requires=['iamvpnlibrary>=0.31.0', 'netaddr'],
    entry_points={
        'console_scripts': ['openvpn-client-connect=openvpn_client_connect.openvpn_script:main',
                            'vpn-user-routes=openvpn_client_connect.vpn_user_routes:main'],
    },
    packages=['openvpn_client_connect'],
)
