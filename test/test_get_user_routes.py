""" Test suite for the utils library """
import unittest
import os.path
import test.context  # pylint: disable=unused-import
import configparser
import mock
from netaddr import IPNetwork
import iamvpnlibrary
from openvpn_client_connect import per_user_configs


class PublicTestsMixin():
    """ Class of tests """

    def test_init(self):
        """ Verify that the self object was initialized """
        self.assertIsInstance(self.library,
                              per_user_configs.GetUserRoutes)
        self.assertIsNotNone(self.library.config)
        self.assertIsInstance(self.library.config, dict)
        self.assertIn('FREE_ROUTES', self.library.config)
        self.assertIn('COMPREHENSIVE_OFFICE_ROUTES', self.library.config)
        self.assertIn('PER_OFFICE_ROUTES', self.library.config)
        self.assertIsInstance(self.library.iam_searcher, iamvpnlibrary.IAMVPNLibrary)

    def test_03_ingest_no_config_files(self):
        """ With no config files, get an empty ConfigParser """
        result = self.library._ingest_config_from_file([])
        self.assertIsInstance(result, configparser.ConfigParser,
                              'Did not create a config object')
        self.assertEqual(result.sections(), [], 'Empty configs must have no parsed config')

    def test_04_ingest_no_config_file(self):
        """ With all missing config files, get an empty ConfigParser """
        result = self.library._ingest_config_from_file(['/tmp/no-such-file.txt'])
        self.assertIsInstance(result, configparser.ConfigParser,
                              'Did not create a config object')
        self.assertEqual(result.sections(), [], 'Empty configs must have no parsed config')

    def test_05_ingest_bad_config_file(self):
        """ With a bad config file, get an empty ConfigParser """
        result = self.library._ingest_config_from_file(['test/context.py'])
        self.assertIsInstance(result, configparser.ConfigParser,
                              'Did not create a config object')
        self.assertEqual(result.sections(), [], 'Empty configs must have no parsed config')

    def test_06_ingest_config_from_file(self):
        """ With an actual config file, get a populated ConfigParser """
        test_reading_file = '/tmp/test-reader.txt'
        with open(test_reading_file, 'w') as filepointer:
            filepointer.write('[aa]\nbb = cc\n')
        filepointer.close()
        result = self.library._ingest_config_from_file(['/tmp/test-reader.txt'])
        self.assertIsInstance(result, configparser.ConfigParser,
                              'Did not create a config object')
        self.assertEqual(result.sections(), ['aa'],
                         'Should have found one configfile section.')
        self.assertEqual(result.options('aa'), ['bb'],
                         'Should have found one option.')
        self.assertEqual(result.get('aa', 'bb'), 'cc',
                         'Should have read a correct value.')
        os.remove(test_reading_file)

    def test_get_office_routes_classic(self):
        """
            verify what kind of data we get for an office routes query
            the contents of the data are hard to test.  Presently this
            is 'either or' but this will change later.
            The most simple test is "when you're in the office, you have
            fewer hosts available than when you're remote"
        """
        ret1 = self.library.get_office_routes(True)
        ret2 = self.library.get_office_routes(False)
        if ret1 == [] and ret2 == []:
            raise self.skipTest('Inconclusive test, no offices defined')
        numhosts1 = sum([x.size for x in ret1])
        numhosts2 = sum([x.size for x in ret2])
        self.assertGreater(numhosts2, numhosts1)

    def test_get_office_routes(self):
        """
            verify what kind of data we get for an office routes query
            the contents of the data are hard to test.  Presently this
            is 'either or' but this will change later.
            The most simple test is "when you're in the office, you have
            fewer hosts available than when you're remote"
        """
        ret1 = self.library.get_office_routes('site1')
        # 'site1' exists as a part of the test_configs for getuserRoutes
        ret2 = self.library.get_office_routes(None)
        if ret1 == [] and ret2 == []:
            raise self.skipTest('Inconclusive test, no offices defined')
        numhosts1 = sum([x.size for x in ret1])
        numhosts2 = sum([x.size for x in ret2])
        self.assertGreater(numhosts2, numhosts1)

    def test_route_subtraction(self):
        """
            This is a listwise removal of routes from a list of routes.
            There could be multiple cases here, but a simple smoke test
            probably covers the intent.
        """
        _input = [
            IPNetwork('10.245.0.1/24'),
            IPNetwork('10.0.0.0/8')
        ]
        office_routes = [
            IPNetwork('10.245.0.0/21'),
            IPNetwork('10.246.0.0/21')
        ]
        proper_output = [
            IPNetwork('10.0.0.0/8'),
        ]
        ret = self.library.route_subtraction(_input, office_routes)
        self.assertEqual(proper_output, ret)

    def test_route_exclusion_single(self):
        """
            This is strips part of a network out of another.
        """
        _input = [
            IPNetwork('10.50.0.0/24'),
            IPNetwork('10.51.0.0/24'),
            IPNetwork('10.52.0.0/24'),
        ]
        remove_routes = IPNetwork('10.50.0.0/25')
        proper_output = [
            IPNetwork('10.50.0.128/25'),
            IPNetwork('10.51.0.0/24'),
            IPNetwork('10.52.0.0/24'),
        ]

        ret = self.library.route_exclusion(_input, remove_routes)
        self.assertEqual(proper_output, ret)

    def test_route_exclusion_fromsingle(self):
        """
            This is strips part of a network out of another
            The catch here, the input is singular.
        """
        _input = IPNetwork('10.50.0.0/24')
        remove_routes = IPNetwork('10.50.0.64/26')
        proper_output = [
            IPNetwork('10.50.0.0/26'),
            IPNetwork('10.50.0.128/25'),
        ]

        ret = self.library.route_exclusion(_input, remove_routes)
        self.assertEqual(proper_output, ret)

    def test_route_exclusion_list(self):
        """
            This is strips part of a network out of another.
            There could be multiple cases here, but a simple smoke test
            probably covers the intent.
        """
        _input = [
            IPNetwork('10.50.0.0/24'),
            IPNetwork('10.51.0.0/24'),
            IPNetwork('10.52.0.0/24')
        ]
        remove_routes = [
            IPNetwork('10.50.0.0/28'),
            IPNetwork('10.51.0.128/25'),
        ]
        proper_output = [
            IPNetwork('10.50.0.16/28'),
            IPNetwork('10.50.0.32/27'),
            IPNetwork('10.50.0.64/26'),
            IPNetwork('10.50.0.128/25'),
            IPNetwork('10.51.0.0/25'),
            IPNetwork('10.52.0.0/24'),
        ]

        ret = self.library.route_exclusion(_input, remove_routes)
        self.assertEqual(proper_output, ret)

    def test_build_user_routes_bad(self):
        """
            This is failed-user test.
        """
        if not self.users.has_section('testing'):  # pragma: no cover
            raise self.skipTest('No testing section defined')
        if not self.users.has_option('testing', 'bad_user'):  # pragma: no cover
            raise self.skipTest('No testing/bad_user defined')
        bad_user = self.users.get('testing', 'bad_user')
        ret = self.library.build_user_routes(bad_user, True)
        self.assertEqual(ret, [])
        ret = self.library.build_user_routes(bad_user, False)
        self.assertEqual(ret, [])

    def test_build_user_routes_classic(self):
        """
            This is pretty much the "get me someone's routes" test.
            Since we're livetesting against a human, who could change their
            available routes, we can't do an awesome check.  But we can
            look for structure.
        """
        with mock.patch.object(self.library, 'iam_searcher', new=None):
            self.assertEqual(self.library.build_user_routes('bob', True), [])
        if not self.users.has_section('testing'):  # pragma: no cover
            raise self.skipTest('No testing section defined')
        if not self.users.has_option('testing', 'normal_user'):  # pragma: no cover
            raise self.skipTest('No testing/normal_user defined')
        normal_user = self.users.get('testing', 'normal_user')
        ret = self.library.build_user_routes(normal_user, True)
        self.assertIsInstance(ret, list)
        self.assertIsInstance(ret[0], IPNetwork)
        self.assertGreaterEqual(len(ret),
                                len(self.library.config['FREE_ROUTES']))
        ret = self.library.build_user_routes(normal_user, False)
        self.assertIsInstance(ret, list)
        self.assertIsInstance(ret[0], IPNetwork)
        _allofficeroutes = self.library.config['COMPREHENSIVE_OFFICE_ROUTES']
        _overlap_routes = (set(ret) &
                           set(_allofficeroutes))
        self.assertEqual(sorted(_overlap_routes),
                         sorted(_allofficeroutes))

    def test_build_user_routes(self):
        """
            This is pretty much the "get me someone's routes" test.
            Since we're livetesting against a human, who could change their
            available routes, we can't do an awesome check.  But we can
            look for structure.
        """
        if not self.users.has_section('testing'):  # pragma: no cover
            raise self.skipTest('No testing section defined')
        if not self.users.has_option('testing', 'normal_user'):  # pragma: no cover
            raise self.skipTest('No testing/normal_user defined')
        normal_user = self.users.get('testing', 'normal_user')
        # If they're in the office, they should have more routes above the
        # minimum provided by 'free'
        ret = self.library.build_user_routes(normal_user, 'site1')
        # 'site1' exists as a part of the test_configs for getuserRoutes
        self.assertIsInstance(ret, list)
        self.assertIsInstance(ret[0], IPNetwork)
        self.assertGreaterEqual(len(ret),
                                len(self.library.config['FREE_ROUTES']))
        # If they're out of the office, they should have the office route.
        ret = self.library.build_user_routes(normal_user, None)
        self.assertIsInstance(ret, list)
        self.assertIsInstance(ret[0], IPNetwork)
        _allofficeroutes = self.library.config['COMPREHENSIVE_OFFICE_ROUTES']
        _overlap_routes = (set(ret) &
                           set(_allofficeroutes))
        self.assertEqual(sorted(_overlap_routes),
                         sorted(_allofficeroutes))


class TestGetUserRoutesGood(PublicTestsMixin, unittest.TestCase):
    """ Test get-user-routes when we have a good file """
    def setUp(self):
        """ Preparing test rig """
        _usersfile = 'test_configs/testing_users.conf'
        _conffile = 'test_configs/get_user_routes.conf'
        if not os.path.isfile(_conffile):  # pragma: no cover
            self.fail('{} must exist to test GetUserRoutes'.format(_conffile))
        self.library = per_user_configs.GetUserRoutes(_conffile)
        self.users = self.library._ingest_config_from_file(_usersfile)


class TestGetUserRoutesBad(PublicTestsMixin, unittest.TestCase):
    """ Test get-user-routes when we have a bad file """
    def setUp(self):
        """ Preparing test rig """
        _usersfile = 'test_configs/testing_users.conf'
        _conffile = 'test_configs/empty.conf'
        if not os.path.isfile(_conffile):  # pragma: no cover
            self.fail('{} must exist to test GetUserRoutes'.format(_conffile))
        self.library = per_user_configs.GetUserRoutes(_conffile)
        self.users = self.library._ingest_config_from_file(_usersfile)


class TestGetUserRoutesNofile(PublicTestsMixin, unittest.TestCase):
    """ Test get-user-routes when we have a wholly missing file """
    def setUp(self):
        """ Preparing test rig """
        _usersfile = 'test_configs/testing_users.conf'
        _conffile = 'test_configs/THIS_FILE_ISNT_HERE.conf'
        self.library = per_user_configs.GetUserRoutes(_conffile)
        self.users = self.library._ingest_config_from_file(_usersfile)
