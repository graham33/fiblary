# Copyright 2013 Nebula Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

"""Test rest module"""

import base64
import json

import requests
from requests_mock.contrib import fixture

from fiblary3.common import exceptions
from fiblary3.common import restapi
from fiblary3.tests import utils


fake_user_agent = 'test_rapi'

fake_auth = '11223344556677889900'
fake_url = 'http://gopher.com'
fake_key = 'gopher'
fake_keys = 'gophers'
fake_username = 'admin'
fake_password = 'admin'


fake_gopher_mac = {
    'id': 'g1',
    'name': 'mac',
    'actor': 'Mel Blanc',
}
fake_gopher_tosh = {
    'id': 'g2',
    'name': 'tosh',
    'actor': 'Stan Freeberg',
}
fake_gopher_single = {
    fake_key: fake_gopher_mac,
}
fake_gopher_list = {
    fake_keys: [
        fake_gopher_mac,
        fake_gopher_tosh,
    ]
}
fake_headers = {
    'User-Agent': fake_user_agent,
}


class TestRESTApi(utils.TestCase):

    def setUp(self):
        super(TestRESTApi, self).setUp()
        self.requests_mock = self.useFixture(fixture.Fixture())

    def test_request_get(self):
        self.requests_mock.get(fake_url, json=fake_gopher_single)

        api = restapi.RESTApi(
            user_agent=fake_user_agent,
        )
        gopher = api.request('GET', fake_url)

        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.headers['User-Agent'], fake_user_agent)
        self.assertEqual(self.requests_mock.last_request.timeout, 10)

        self.assertEqual(gopher.status_code, 200)
        self.assertEqual(gopher.json(), fake_gopher_single)

    def test_request_get_return_300(self):
        self.requests_mock.get(fake_url, json=fake_gopher_single, status_code=300)

        api = restapi.RESTApi(
            user_agent=fake_user_agent,
        )
        gopher = api.request('GET', fake_url)

        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.headers['User-Agent'], fake_user_agent)
        self.assertEqual(self.requests_mock.last_request.timeout, 10)

        self.assertEqual(gopher.status_code, 300)
        self.assertEqual(gopher.json(), fake_gopher_single)

    def test_request_get_fail_404(self):
        self.requests_mock.get(fake_url, json=fake_gopher_single, status_code=404)

        api = restapi.RESTApi(
            user_agent=fake_user_agent,
        )
        self.assertRaises(
            exceptions.HTTPNotFound,
            api.request,
            'GET',
            fake_url)

        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.headers['User-Agent'], fake_user_agent)
        self.assertEqual(self.requests_mock.last_request.timeout, 10)

    def test_request_get_auth(self):
        self.requests_mock.get(fake_url, json=fake_gopher_single)

        api = restapi.RESTApi(
            username=fake_username,
            password=fake_password,
            user_agent=fake_user_agent,
        )
        gopher = api.request('GET', fake_url)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.headers['User-Agent'], fake_user_agent)
        self.assertEqual(self.requests_mock.last_request.timeout, 10)
        encoded_auth = base64.b64encode(bytes(f"{fake_username}:{fake_password}", encoding='utf-8')).decode("ascii")
        self.assertEqual(self.requests_mock.last_request.headers["Authorization"], f"Basic {encoded_auth}")
        self.assertEqual(gopher.json(), fake_gopher_single)

    def test_request_post(self):
        self.requests_mock.post(fake_url, json=fake_gopher_single)

        api = restapi.RESTApi(
            user_agent=fake_user_agent,
        )
        data = fake_gopher_tosh
        gopher = api.request('POST', fake_url, json=data)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.headers['User-Agent'], fake_user_agent)
        self.assertEqual(self.requests_mock.last_request.timeout, 10)
        self.assertEqual(self.requests_mock.last_request.headers['Content-Type'], 'application/json')
        self.assertEqual(self.requests_mock.last_request.json(), data)
        self.assertEqual(gopher.json(), fake_gopher_single)

    # Methods
    # TODO(dtroyer): add the other method methods

    def test_delete(self):
        self.requests_mock.delete(fake_url)

        api = restapi.RESTApi()
        gopher = api.delete(fake_url)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(gopher.status_code, 200)

    # Commands

    def test_create(self):
        self.requests_mock.post(fake_url, json=fake_gopher_single)

        api = restapi.RESTApi()
        data = fake_gopher_mac

        # Test no key
        gopher = api.create(fake_url, data=data)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.json(), data)
        self.assertEqual(gopher, fake_gopher_single)

        # Test with key
        self.requests_mock.reset_mock()
        gopher = api.create(fake_url, data=data, response_key=fake_key)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.json(), data)
        self.assertEqual(gopher, fake_gopher_mac)

    def test_list(self):
        self.requests_mock.get(fake_url, json=fake_gopher_list)
        self.requests_mock.post(fake_url, json=fake_gopher_list)

        # test base
        api = restapi.RESTApi()
        gopher = api.list(fake_url, response_key=fake_keys)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.method, 'GET')
        self.assertEqual(gopher, [fake_gopher_mac, fake_gopher_tosh])

        # test body
        api = restapi.RESTApi()
        data = {'qwerty': 1}
        gopher = api.list(fake_url, response_key=fake_keys, data=data)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.method, 'POST')
        self.assertEqual(self.requests_mock.last_request.json(), data)
        self.assertEqual(gopher, [fake_gopher_mac, fake_gopher_tosh])

        # test query params
        api = restapi.RESTApi()
        params = {'qaz': '123'}
        gophers = api.list(fake_url, response_key=fake_keys, params=params)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(self.requests_mock.last_request.method, 'GET')
        self.assertEqual(self.requests_mock.last_request.qs, {k: [v] for k, v in params.items()})
        self.assertEqual(gophers, [fake_gopher_mac, fake_gopher_tosh])

    def test_set(self):
        self.requests_mock.put(fake_url, json=fake_gopher_single)

        new_gopher = fake_gopher_single
        new_gopher[fake_key]['name'] = 'Chip'

        api = restapi.RESTApi()
        data = fake_gopher_mac
        data['name'] = 'Chip'

        # Test no data, no key
        gopher = api.set(fake_url)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(gopher, None)

        # Test data, no key
        gopher = api.set(fake_url, data=data)
        self.assertEqual(self.requests_mock.call_count, 2)
        self.assertEqual(self.requests_mock.last_request.json(), data)
        self.assertEqual(gopher, fake_gopher_single)

        # NOTE:(dtroyer): Key and no data is not tested as without data
        # the response_key is moot

        # Test data and key
        gopher = api.set(fake_url, data=data, response_key=fake_key)
        self.assertEqual(self.requests_mock.call_count, 3)
        self.assertEqual(self.requests_mock.last_request.json(), data)
        self.assertEqual(gopher, fake_gopher_mac)

    def test_show(self):
        self.requests_mock.get(fake_url, json=fake_gopher_single)

        api = restapi.RESTApi()

        # Test no key
        gopher = api.show(fake_url)
        self.assertTrue(self.requests_mock.called)
        self.assertEqual(gopher, fake_gopher_single)

        # Test with key
        gopher = api.show(fake_url, response_key=fake_key)
        self.assertEqual(self.requests_mock.call_count, 2)
        self.assertEqual(gopher, fake_gopher_mac)
