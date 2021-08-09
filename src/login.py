import uuid as _uuid
from fdrtd_server.microservice import Microservice
import fdrtd_server
import rpy2
import rpy2.rinterface
import rpy2.rinterface_lib
from rpy2.rinterface_lib.embedded import RRuntimeError
from rpy2.robjects.packages import importr
from rpy2.robjects import r
from threading import Thread
import sys
sys.path.append('./protocol_DataSHIELD/src')
import helpers

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
            except RRuntimeError as err:
                self.storage[uuid]['busy'] = False
                if "The server parameter cannot be empty" in str(err):
                    raise fdrtd_server.exceptions.MissingParameter("server")
                elif "The url parameter cannot be empty" in str(err):
                    raise fdrtd_server.exceptions.MissingParameter("url")
                elif "Duplicate server name: " in str(err):
                    raise fdrtd_server.exceptions.InvalidParameter('server', 'duplicate')
                else:
                    raise fdrtd_server.exceptions.InternalServerError(str(err))
            except Exception as err:
                self.storage[uuid]['busy'] = False
                raise fdrtd_server.exceptions.InternalServerError(str(err))
        try:
            connection = r('connections%s <- DSI::datashield.login(%s)'
                           % (uuid.replace('-', ''), helpers.login_params_string_builder(parameters, uuid)))
        except RRuntimeError as err:
            self.storage[uuid]['busy'] = False
            if 'The provided login details is missing both table and resource columns' in str(err):
                raise fdrtd_server.exceptions.InvalidParameter('table, resource', 'both missing')
            elif 'Unauthorized' in str(err):
                raise fdrtd_server.exceptions.ApiError(401, 'Unauthorized')
            else:
                raise fdrtd_server.exceptions.InternalServerError(str(err))
        except Exception as err:
            self.storage[uuid]['busy'] = False
            raise fdrtd_server.exceptions.InternalServerError(str(err))
        self.storage[uuid]['busy'] = False
        connection_microservice_uuid = self.bus.select_microservice(
            requirements={'protocol': 'DataSHIELD', 'microservice': 'connection'}
        )
        self.connection_callbacks_storage[uuid] = self.bus.call_microservice(
            handle=connection_microservice_uuid,
            function='connect',
            parameters={'connection': connection, 'uuid': uuid}
        )
        return None

    def get_status(self, callback):
        try:
            return self.storage[callback]
        except KeyError:
            raise fdrtd_server.exceptions.InvalidParameter(f'uuid {callback}', 'not found')

    def get_result(self, callback):
        try:
            return self.connection_callbacks_storage[callback]
        except KeyError:
            fdrtd_server.exceptions.InvalidParameter(f'uuid {callback}', 'not found')

