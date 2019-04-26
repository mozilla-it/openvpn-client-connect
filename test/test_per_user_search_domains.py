#!/usr/bin/python
""" Test suite for the per_user_configs search domains """
import unittest
import sys
import os.path
import six
sys.path.insert(1, 'iamvpnlibrary')
import iamvpnlibrary
# prepend the iam library so that we can locally test.
from openvpn_client_connect import per_user_configs  # pylint: disable=wrong-import-position
# We import our interesting library last, after modifying the
# search order, so we pick up the local copy + libraries,
# rather than ones that might be already installed.
try:
    # 2.7's module:
    from ConfigParser import NoOptionError, NoSectionError
except ImportError:  # pragma: no cover
    # 3's module:
    from configparser import NoOptionError, NoSectionError


class PublicTestsMixin(object):
    """
        This class is used to run a basic litmus test on some
        mediocre setups.  The good checks are later in this file.
    """
    def test_init(self):
        """ Verify that the self object was initialized """
        self.assertIsInstance(self.library, per_user_configs.GetUserSearchDomains,
                              'Somehow you did not instantiate the correct object')
        self.assertIsInstance(self.library.search_domains, list,
                              'default search_domains must be a list')
        self.assertIsInstance(self.library.dynamic_dict, dict,
                              'default dynamic_dict must be a dict')
        self.assertIsInstance(self.library.iam_searcher, iamvpnlibrary.IAMVPNLibrary)

    def test_build_search_domains(self):
        """
            Verify that the main call of this class doesn't blow out
            when presented with a not-unreasonable set of inputs.
        """
        res = self.library.build_search_domains(['no-exist1', 'no-exist2'])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, self.library.search_domains,
                         ('build_search_domains must return the defaults '
                          'when we have uninteresting inputs'))


class TestSearchDomainsGood(PublicTestsMixin, unittest.TestCase):
    """ Quick-test build_search_domains when we have a good file """
    def setUp(self):
        """ Preparing test rig """
        _conffile = 'test_configs/testing_search_domains.conf'
        if not os.path.isfile(_conffile):  # pragma: no cover
            self.fail('{} must exist to test GetUserSearchDomains'.format(_conffile))
        self.library = per_user_configs.GetUserSearchDomains(_conffile)


class TestSearchDomainsBad(PublicTestsMixin, unittest.TestCase):
    """ Quick-test build_search_domains when we have a bad file """
    def setUp(self):
        """ Preparing test rig """
        _conffile = 'test_configs/empty.conf'
        if not os.path.isfile(_conffile):  # pragma: no cover
            self.fail('{} must exist to test GetUserSearchDomains'.format(_conffile))
        self.library = per_user_configs.GetUserSearchDomains(_conffile)


class TestSearchDomainsNofile(PublicTestsMixin, unittest.TestCase):
    """ Quick-test build_search_domains when we have a missing file """
    def setUp(self):
        """ Preparing test rig """
        _conffile = 'test_configs/THIS_FILE_ISNT_HERE.conf'
        self.library = per_user_configs.GetUserSearchDomains(_conffile)


#######################################################################
class TestSearchDomainsContents(unittest.TestCase):
    """
        Test build_search_domains for specific return values.  This is
        the meaty test.  We populate fake values and then test against
        them.  If we ever change the GetUserSearchDomains structure,
        this could become a very invalid suite.
    """
    def setUp(self):
        """ Preparing test rig """
        # Doesn't matter what this file is, we're going to populate
        # it for testing:specifics.  Pick the empty one for kicks.
        _conffile = 'test_configs/empty.conf'
        self.library = per_user_configs.GetUserSearchDomains(_conffile)
        self.library.search_domains = ['example.com', 'example.org', ]
        self.library.dynamic_dict = {
            'vpn_example_string_1': 'example1.example.com',
            'vpn_example_list_1': ['example1.example.com', ],
            'vpn_example_list_2': ['example1.example.com', 'example2.example.net', ],
            'vpn_example_dup_1': 'example.com',
            'vpn_example_dup_2': ['example.org', ],
            'vpn_example_emptystring': '',
            'vpn_example_emptylist': [],
            'vpn_example_number': 3,
        }

    # The test of "no dynamic_dict" is in another class.

    def test_nogroups(self):
        """
            If someone has no groups, they get the defaults.
        """
        res = self.library.build_search_domains([])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, self.library.search_domains,
                         ('build_search_domains must return the defaults '
                          'when we have uninteresting inputs'))

    def test_nomatch_groups(self):
        """
            If someone has groups that have no matches, they get the defaults.
        """
        res = self.library.build_search_domains(['some', 'strings'])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, self.library.search_domains,
                         ('build_search_domains must return the defaults '
                          'when we have uninteresting inputs'))

    def test_string1(self):
        """
            If someone has a match, they pick up the extra group via strings.
        """
        testgroup = 'vpn_example_string_1'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, ['example.com', 'example.org', 'example1.example.com'],
                         'matching groups must inherit a string value')

    def test_list1(self):
        """
            If someone has a match, they pick up an extra group (singular) via list.
        """
        testgroup = 'vpn_example_list_1'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, ['example.com', 'example.org', 'example1.example.com'],
                         'matching groups must inherit from a list')

    def test_list2(self):
        """
            If someone has a match, they pick up extra groups (plural) via list.
        """
        testgroup = 'vpn_example_list_2'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, ['example.com', 'example.org',
                               'example1.example.com', 'example2.example.net'],
                         'matching groups must inherit multiples from a list')

    def test_dup1(self):
        """
            If someone has a match, they should not pick up duplicate pushes from strings.
            This basically safeguards against a stupid config file.
        """
        testgroup = 'vpn_example_dup_1'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, ['example.com', 'example.org'],
                         'matching groups must not create duplicates')

    def test_dup2(self):
        """
            If someone has a match, they should not pick up duplicate pushes from lists.
            This basically safeguards against a stupid config file.
        """
        testgroup = 'vpn_example_dup_2'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, ['example.com', 'example.org'],
                         'matching groups must not create duplicates')

    def test_empty1(self):
        """
            If someone has a '' as an "add this" value, don't include it.
            This basically safeguards against a stupid config file.
        """
        testgroup = 'vpn_example_emptystring'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, self.library.search_domains,
                         ('build_search_domains must return the defaults '
                          'when we have uninteresting inputs'))

    def test_empty2(self):
        """
            If someone has a [] as an "add this" value, don't include it.
            This basically safeguards against a stupid config file.
        """
        testgroup = 'vpn_example_emptylist'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, self.library.search_domains,
                         ('build_search_domains must return the defaults '
                          'when we have uninteresting inputs'))

    def test_numbers(self):
        """
            If someone has a nonstring as an "add this" value, don't include it.
            This basically safeguards against a stupid config file.
        """
        testgroup = 'vpn_example_number'
        self.assertIn(testgroup, self.library.dynamic_dict,
                      ('"{}" must be in dynamic_dict for this '
                       'test to work'.format(testgroup)))
        res = self.library.build_search_domains(['something', testgroup])
        self.assertIsInstance(res, list,
                              'build_search_domains must return a list')
        for item in res:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(res, self.library.search_domains,
                         ('build_search_domains must return the defaults '
                          'when we have uninteresting inputs'))


#######################################################################
class TestSearchDomainsUser(unittest.TestCase):
    """
        Test get_search_domains for non-specific return values.  This is
        testing the 'front door', the call that outsiders will make.
        The code for get_search_domains is VERY simple and a handoff to
        build_search_domains, which is extensively tested above.
        This suite is mostly for coverage and idiot checks.
    """
    def setUp(self):
        """ Preparing test rig """
        _usersfile = 'test_configs/testing_users.conf'
        _conffile = 'test_configs/testing_search_domains.conf'
        self.library = per_user_configs.GetUserSearchDomains(_conffile)
        # pylint: disable=protected-access
        self.users = self.library._ingest_config_from_file(_usersfile)

    def test_getsearch(self):
        """
            This seeks to test that a user who doesn't exist gets the
            standard pile of DNS search domains, and a user who is
            priviliged gets more.  This has the assumption that the
            'normal user' is special, normally.
        """
        try:
            bad_user = self.users.get('testing', 'bad_user')
        except (NoOptionError, NoSectionError):  # pragma: no cover
            raise self.skipTest('No testing/bad_user defined')
        try:
            normal_user = self.users.get('testing', 'normal_user')
        except (NoOptionError, NoSectionError):  # pragma: no cover
            raise self.skipTest('No testing/normal_user defined')

        bad = self.library.get_search_domains(bad_user)
        self.assertIsInstance(bad, list, ('The bad_user should get a list '
                                          'of dns search domains'))
        for item in bad:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertEqual(bad, self.library.search_domains, ('bad users should have '
                                                            'only the default dns '
                                                            'search domains'))

        good = self.library.get_search_domains(normal_user)
        self.assertIsInstance(good, list, ('The normal_user should get a list '
                                           'of dns search domains'))
        for item in good:
            self.assertIsInstance(item, six.string_types,
                                  ('item in dns search domain list was '
                                   'nonstring: "{}"').format(item))
        self.assertLess(len(bad), len(good), ('good users should get more search '
                                              'domains than bad users'))
