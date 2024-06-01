""" Test suite for the per_user_configs non-class methods """
import unittest
import test.context  # pylint: disable=unused-import
import mock
from openvpn_client_connect import per_user_configs


class TestUserMayVPN(unittest.TestCase):
    """ Test user_may_vpn """

    def test_user_may_not_vpn_when_ldap_fails(self):
        """ Fail secure"""
        with mock.patch('iamvpnlibrary.IAMVPNLibrary',
                        side_effect=RuntimeError) as mock_library:
            res = per_user_configs.user_may_vpn('foo@example.com')
        mock_library.assert_called_once()
        self.assertFalse(res)

    def test_user_may_not_vpn(self):
        """ Verify pipeline call """
        with mock.patch('iamvpnlibrary.IAMVPNLibrary.user_allowed_to_vpn',
                        return_value=False) as mock_library:
            res = per_user_configs.user_may_vpn('foo@example.com')
        mock_library.assert_called_once_with('foo@example.com')
        self.assertFalse(res)

    def test_user_may_vpn(self):
        """ Verify pipeline call """
        with mock.patch('iamvpnlibrary.IAMVPNLibrary.user_allowed_to_vpn',
                        return_value=True) as mock_library:
            res = per_user_configs.user_may_vpn('bar@example.com')
        mock_library.assert_called_once_with('bar@example.com')
        self.assertTrue(res)
