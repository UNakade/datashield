import uuid as _uuid
from threading import Thread

import rpy2
import rpy2.rinterface
import rpy2.rinterface_lib
from rpy2.robjects.packages import importr
from rpy2.robjects import r

import fdrtd.server
from fdrtd.server.microservice import Microservice
from fdrtd.plugins.datashield import helpers

consolewrite_warnerror_backup = rpy2.rinterface_lib.callbacks.consolewrite_warnerror
consolewrite_print_backup = rpy2.rinterface_lib.callbacks.consolewrite_print

base = importr('base')
DSI = importr('DSI')
DSOpal = importr('DSOpal')
dsBaseClient = importr('dsBaseClient')
grDevices = importr('grDevices')
jsonlite_R = importr('jsonlite')


class Login(Microservice):

    def __init__(self, bus, endpoint):
        super().__init__(bus, endpoint)
        self.storage = {}
        self.connection_callbacks_storage = {}

    def login(self, list_of_servers, parameters=None, **kwargs):
        if parameters is None:
            parameters = {}
        parameters.update(kwargs)
        uuid = str(_uuid.uuid4())
        self.storage[uuid] = {'warnerror': [], 'print': [], 'busy': True}
        Thread(target=self.login_helper, args=(uuid, list_of_servers, parameters), daemon=True).start()
        return self.callback(uuid)

    def login_helper(self, uuid, list_of_servers, parameters):
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: self.storage[uuid]['warnerror'].append(e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: self.storage[uuid]['print'].append(e)
        builder = r('builder%s <- DSI::newDSLoginBuilder()' % uuid.replace('-', ''))
        for server in list_of_servers:
            try:
                builder['append'](**server)
            except Exception as err:
                self.storage[uuid]['busy'] = False
                raise helpers.handle_error(str(err), 'login')
        try:
            connection = r('connections%s <- DSI::datashield.login(%s)'
                           % (uuid.replace('-', ''), helpers.login_params_string_builder(parameters, uuid)))
        except Exception as err:
            self.storage[uuid]['busy'] = False
            raise helpers.handle_error(str(err), 'login')
        self.storage[uuid]['busy'] = False
        for key in self.bus.microservices:
            if [self.bus.microservices[key]['identifiers'].get(identifier)
                    for identifier in ['protocol', 'microservice']] == ['DataSHIELD', 'connection']:
                self.connection_callbacks_storage[uuid] = \
                    self.bus.microservices[key]['instance'].connect(connection, uuid)
        return None

    def get_status(self, callback):
        try:
            return self.storage[callback]
        except KeyError:
            raise fdrtd.server.exceptions.InvalidParameter(f'uuid {callback}', 'not found')

    def get_result(self, callback):
        try:
            return self.connection_callbacks_storage[callback]
        except KeyError:
            fdrtd.server.exceptions.InvalidParameter(f'uuid {callback}', 'not found')
