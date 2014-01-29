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
 fiblary.client
 ~~~~~~~~~~~~~~

 Home Center Controller Client Implementation

"""
import logging
import threading
import warlock

from fiblary.client.v3 import devices
from fiblary.client.v3 import events
from fiblary.client.v3 import info
from fiblary.client.v3 import login
from fiblary.client.v3 import rooms
from fiblary.client.v3 import scenes
from fiblary.client.v3 import schemas
from fiblary.client.v3 import sections
from fiblary.client.v3 import users
from fiblary.client.v3 import variables
from fiblary.client.v3 import weather

from fiblary.common.event import EventHook
from fiblary.common import exceptions
from fiblary.common import restapi


_logger = logging.getLogger(__name__)


class Client(object):
    """Home Center 2 Clinet Class.
    Provides interface to different resources managed by HC2
    throught the specialized controllers
    """
    def __init__(self, endpoint, username=None, password=None):

        self.client = restapi.RESTApi(
            base_url=endpoint,
            username=username,
            password=password,
            debug=True
        )

        self.modified = {}
        self.modified_lock = threading.Lock()

        # initialize the managers
        self.schemas = schemas.Controller()

        self.info = info.Controller(
            self.client,
            self._get_info_model()
        )

        self.login = login.Controller(
            self.client,
            self._get_login_model()
        )

        self.sections = sections.Controller(
            self.client,
            self._get_section_model()
        )

        self.rooms = rooms.Controller(
            self.client,
            self._get_room_model()
        )

        self.users = users.Controller(
            self.client,
            self._get_user_model()
        )

        self.variables = variables.Controller(
            self.client,
            self._get_variable_model()
        )

        self.scenes = scenes.Controller(
            self.client,
            self._get_scene_model()
        )

        self.devices = devices.Controller(
            self.client,
            self._get_device_model()
        )

        self.weather = weather.Controller(
            self.client,
            self._get_weather_model()
        )

        self.events = events.Controller(
            self.client,
            self._get_event_model()
        )

        self.state_handler = None

    def _get_info_model(self):
        schema = self.schemas.get('info')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_login_model(self):
        schema = self.schemas.get('login')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_section_model(self):
        schema = self.schemas.get('section')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_room_model(self):
        schema = self.schemas.get('room')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_user_model(self):
        schema = self.schemas.get('user')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_variable_model(self):
        schema = self.schemas.get('variable')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_weather_model(self):
        schema = self.schemas.get('weather')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_event_model(self):
        schema = self.schemas.get('event')
        return warlock.model_factory(schema.raw(), schemas.SchemaBasedModel)

    def _get_scene_model(self):
        def model(**item):
            schema = self.schemas.get('scene')
            wrapped_model = warlock.model_factory(
                schema.raw(),
                schemas.SceneSchemaModel)
            model = wrapped_model(**item)
            model.controller = self.scenes
            return model
        return model

    _schema_ignore = ["HC_user", "VOIP_user", "weather", 'iOS_device', '']

    def _get_device_model(self):
        def model(**item):
            item_type = item['type']
            _logger.debug("Item type: {}".format(item_type))
            if item_type in self._schema_ignore:
                return None
            schema = self.schemas.get(item_type)
            if schema:
                wrapped_model = warlock.model_factory(
                    schema.raw(),
                    schemas.ActionSchemaModel)
                actions = item['actions']
                model = wrapped_model(**item)
                self.devices._add_actions(model, actions)
                return model
            else:
                return None
        return model

    def __repr__(self):
        return "Home Center 2 Client"

    def _on_properity_change(self, **kwargs):
        try:
            property_name = kwargs['property']
            self.modified[property_name](**kwargs)
        except Exception:
            # trick to reduce number of exceptions
            with self.modified_lock:
                self.modified[property_name] = EventHook()  # property_name

    def _on_state_change(self, state):
        timestamp = state.get('timestamp', 0)
        for change in state.get('changes', []):
            device_id = change.pop('id')
            for property_name, value in change.items():
                data = {
                    'timestamp': timestamp,
                    'id': device_id,
                    'property': property_name,
                    'value': value,
                    'client': self
                }
                self._on_properity_change(**data)

# API

    def enable_state_handler(self):
        self.state_handler = StateHandler(self, self._on_state_change)

    def disable_state_handler(self):
        self.state_handler.stop()

    def add_event_handler(self, property_name, handler):
        if property_name not in self.modified:
            with self.modified_lock:
                self.modified[property_name] = EventHook(property_name)

        self.modified[property_name] += handler

    def remove_event_handler(self, property_name, handler):
        try:
            self.modified[property_name] -= handler
        except ValueError:
            raise exceptions.HandlerNotFound(
                message="Handler for property '{}' not found: {}.".format(
                    property_name,
                    handler.__name__))


class StateHandler(threading.Thread):
    def __init__(self, client, callback):
        super(StateHandler, self).__init__(name=self.__class__.__name__)
        self.client = client
        self.api = client.client
        self.callback = callback
        self.daemon = True  # stop unconditionally on exit

        self._stop = threading.Event("Stop")

        self.start()

    def run(self):
        """State Handler main loop"""

        _logger.info("Starting the state change handler")
        last = "0"
        while not self.stopped():

            timeout = 60
            sleep_time = 1
            attempt = 1
            success = False

            while not success:
                if self.stopped():
                    break

                try:
                    state = self.api.get(
                        '/refreshStates?last={}'.format(last),
                        timeout=timeout).json()
                    _logger.debug(state)
                    last = state['last']
                    self.callback(state)
                    success = True
                    break

                except exceptions.ConnectionError:
                    _logger.warn("Connection Error. Attempt number: {}".format(
                        attempt)
                    )
                    attempt += 1

                if not success:
                    if attempt == 10:
                        sleep_time = 30
                        _logger.warn(
                            "Fallback to 30-second connection retry timer."
                        )

                    _logger.warn(
                        "Waiting for next attempt {} second(s)".format(
                            sleep_time)
                    )
                    self._stop.wait(sleep_time)

        _logger.info("State change handler stopped.")

    def stopped(self):
        return self._stop.isSet()

    def stop(self):
        _logger.info("Stopping the state change handler")

        self.api.session.close()  # unfortunatelly not effect on
                                  # pending request
        self._stop.set()