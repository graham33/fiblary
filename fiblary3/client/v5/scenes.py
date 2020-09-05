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
 fiblary.scenes
 ~~~~~~~~~~~~~~

 Home Center Scene Manager Implementation
"""

import logging

from fiblary3.client.v5 import base
from fiblary3.common import exceptions


_logger = logging.getLogger(__name__)


class Controller(base.CommonController):
    RESOURCE = 'scenes'

    def _scene_control(self, scene_id, action=None, data=None, method=None):
        cmd = '{}/{}'.format(self.RESOURCE, scene_id)
        if action is not None:
            cmd = '{}/{}'.format(cmd, action)
        if data is None:
            data = "{}"
        if method == "PUT":
            resp = self.http_client.put(cmd, data=data)
        else:
            resp = self.http_client.post(cmd, data=data)

        if resp.status_code != 202:
            exceptions.from_response(resp)
        return self.get(scene_id)

    def _scene_post(self, scene_id, action=None, data=None):
        return self._scene_control(scene_id, action, data)

    def _scene_put(self, scene_id, action=None, data=None):
        return self._scene_control(scene_id, action, data, "PUT")

    def start(self, scene_id):
        scene = self._scene_post(scene_id, "execute")
        _logger.info("Scene {}({}) started".format(scene.name, scene.id))
        return scene

    def stop(self, scene_id, pin=None):
        data = {}
        if pin is not None:
            data = '{"pin": "{0}"}'.format(pin)
        scene = self._scene_post(scene_id, "kill", data)
        _logger.info("Scene {}({}) stopped".format(scene.name, scene.id))
        return scene

    def enable(self, scene_id):
        data = '{ "enabled": true }'
        scene = self._scene_put(scene_id, data=data)
        _logger.info("Scene {}({}) enabled".format(scene.name, scene.id))
        return scene

    def disable(self, scene_id):
        data = '{ "enabled": false }'
        scene = self._scene_put(scene_id, data=data)
        _logger.info("Scene {}({}) disabled".format(scene.name, scene.id))
        return scene

    def update(self, data):
        # scene is Null due to
        # http://bugzilla.fibaro.com/view.php?id=1176
        # must be retrieved again
        scene = super(Controller, self).update(data)
        try:
            scene_id = data['id']
            if scene_id:
                _logger.warning(
                    "Refer to: http://bugzilla.fibaro.com/view.php?id=1176")
                scene = self.get(scene_id)
        except Exception:
            pass

        return scene
