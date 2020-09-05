#  Copyright 2020 Daniel Pervan
#  Copyright 2014 Klaudiusz Staniek
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
 fiblary.devices
 ~~~~~~~~~~~~~~

 Home Center Device Manager Implementation
"""

from fiblary3.client.v5 import base
from fiblary3.common import exceptions

import logging


_logger = logging.getLogger(__name__)


class Controller(base.CommonController):
    RESOURCE = 'devices'
    API_PARAMS = ('id', 'type', 'roomID')

    def action(self, device_id, action, *args):
        cmd = 'devices/{}/action/{}'.format(device_id, action)
        if args:
            data = '{ "args":'
            for i, arg in enumerate(args):
                if (i > 1):
                    data = '{}, '.format(data)
                data = '{}"{}"'.format(data, arg)
        else:
            data = "{}"
        resp = self.http_client.post(cmd, data=data)
        if resp.status_code != 200 and resp.status_code != 202:
            exceptions.from_response(resp)

    def update(self, data):
        try:
            """
            HC2 does not like those properties to be PUT
            """
            data.properties.pop("associationView")
            data.properties.pop("associationSet")

        except Exception:
            pass

        return super(Controller, self).update(data)
