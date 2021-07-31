import functools
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

    def list_functions(self):
        return {
            'login': {'public': True, 'pointer': self.login},
            'get_status': {'public': True, 'pointer': self.get_status},
            'login_helper': {'public': False, 'pointer': self.login_helper},
            'get_result': {'public': True, 'pointer': self.get_result}
        }

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


class Connection(Microservice):

    def __init__(self, bus, endpoint):

        super().__init__(bus, endpoint)

        self.connections = {}
        self.storage = {}
        self.function_callbacks_storage = {}
        self.deprecated = {
            'ds.listOpals', 'ds.listServersideFunctions', 'ds.look', 'ds.meanByClass', 'ds.message', 'ds.recodeLevels',
            'ds.setDefaultOpals', 'ds.subset', 'ds.subsetByClass', 'ds.table1D', 'ds.table2D', 'ds.vectorCalc'
        }
        self.return_types = {
            'return': set(base.ls('package:dsBaseClient')) - {
                'ds.exp', 'ds.assign', 'ds.c', 'ds.recodeLevels', 'ds.changeRefGroup', 'ds.list', 'ds.log',
                'ds.vectorCalc', 'ds.subset', 'ds.sqrt', 'ds.replaceNA', 'ds.abs', 'ds.subsetByClass', 'ds.heatmapPlot',
                'ds.contourPlot'
            },
            'plot': {
                'ds.histogram', 'ds.boxPlot', 'ds.contourPlot', 'ds.heatmapPlot', 'ds.scatterPlot'
            }
        }
        self.input_type_requirements = {
            'x_vec': ['ds.vectorCalc']
        }

    def list_functions(self):
        functions_dict = {
            'connect': {'public': False, 'pointer': self.connect},
            'call_function': {'public': True, 'pointer': self.call_function},
            'call_function_helper': {'public': False, 'pointer': self.call_function_helper},
            'logout': {'public': True, 'pointer': self.logout},
            'logout_helper': {'public': False, 'pointer': self.logout_helper},
            'get_status': {'public': True, 'pointer': self.get_status},
            'get_result': {'public': True, 'pointer': self.get_result}
        }
        funcnames = list(base.ls('package:dsBaseClient'))
        for func in funcnames:
            functions_dict[func[3:].replace('.', '_')] = {
                'public': True,
                'pointer': functools.partial(self.call_function, func=func)
            }
        return functions_dict

    def connect(self, connection, uuid):
        self.connections[uuid] = connection
        self.storage[uuid] = {
            'warnerror': [],
            'print': [],
            'busy': False,
            'path_to_temp_plot_storage': '',
            'calls': {}
        }
        self.function_callbacks_storage[uuid] = {}
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: self.storage[uuid]['warnerror'].append(e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: self.storage[uuid]['print'].append(e)
        return self.callback({'connection': uuid})

    def call_function(self, callback: dict, func: str, parameters: dict = None, **kwargs):
        connection_uuid = callback['connection']
        if parameters is None:
            parameters = {}
        parameters.update(kwargs)
        call_uuid = str(_uuid.uuid4())
        callback.update({'call': call_uuid})
        self.storage[connection_uuid]['busy'] = True
        self.storage[connection_uuid]['calls'][call_uuid] = {
            'function': func,
            'warnerror': [],
            'print': [],
            'busy': True
        }
        Thread(target=self.call_function_helper, args=(callback, func, parameters), daemon=True).start()
        return self.callback(callback)

    def call_function_helper(self, callback: dict, func: str, parameters: dict):
        func_ = func.replace('.', '_')
        connection_uuid = callback['connection']
        call_uuid = callback['call']
        connection = self.connections[connection_uuid]
        if 'servers' in parameters:
            if isinstance(parameters['servers'], list):
                connection = connection.rx(base.c(*parameters['servers']))
            else:
                connection = connection.rx(parameters['servers'])
        return_serial_json = parameters.get('return_serial_JSON', False)
        call = self.storage[connection_uuid]['calls'][call_uuid]
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: call['warnerror'].append(e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: call['print'].append(e)
        parameters_used = helpers.defaults(getattr(dsBaseClient, func_), parameters)
        if 'datasources' in parameters_used:
            parameters_used['datasources'] = connection
        if func_ not in dir(dsBaseClient):
            self.storage[connection_uuid]['busy'] = False
            call['busy'] = False
            raise fdrtd_server.exceptions.FunctionNotFound(f'{func} not in dsBaseClient')
        try:
            if func in self.return_types['plot']:
                plot_uuid = str(_uuid.uuid4())
                aspect_mul = 1
                if (parameters_used['type'] == 'split') | (parameters_used['type'][0] == 'split'):
                    aspect_mul = len(connection)
                grDevices.png(
                    filename=self.storage[connection_uuid]['path_to_temp_plot_storage'] + plot_uuid + '.png', height=10,
                    width=aspect_mul * 10, units='in', res=300
                )
                return_r = getattr(dsBaseClient, func_)(**parameters_used)
                grDevices.dev_off()
                return_dict = {'plot_uuid': plot_uuid}
                call['plot_uuid'] = plot_uuid
                if func in self.return_types['return']:
                    if return_serial_json:
                        return_dict['return_serial_json'] = jsonlite_R.serializeJSON(return_r)[0]
                    else:
                        return_dict['return_json'] = helpers.r_to_json(return_r)
                self.storage[connection_uuid]['busy'] = False
                call['busy'] = False
                self.function_callbacks_storage[connection_uuid][call_uuid] = return_dict
                return None
            else:
                return_r = getattr(dsBaseClient, func_)(**parameters_used)
                self.storage[connection_uuid]['busy'] = False
                call['busy'] = False
                if func in self.return_types['return']:
                    if return_serial_json:
                        self.function_callbacks_storage[connection_uuid][call_uuid] = jsonlite_R.serializeJSON(
                            return_r)[0]
                        return None
                    else:
                        self.function_callbacks_storage[connection_uuid][call_uuid] = helpers.r_to_json(return_r)
                        return None
                self.function_callbacks_storage[connection_uuid][call_uuid] = None
                return None
        except Exception as err:
            self.storage[connection_uuid]['busy'] = False
            call['busy'] = False
            if 'datashield.errors' in str(err):
                raise fdrtd_server.exceptions.InternalServerError(
                    f'Error: \n {str(err)} \n datashield.errors(): \n {str(DSI.datashield_errors())}'
                )
            else:
                raise fdrtd_server.exceptions.InternalServerError(f'Error: \n{str(err)}')

    def logout(self, callback: dict):
        connection_uuid = callback['connection']
        call_uuid = str(_uuid.uuid4())
        self.storage[connection_uuid]['calls'][call_uuid] = {
            'function': 'logout',
            'warnerror': [],
            'print': [],
            'busy': True
        }
        self.storage[connection_uuid]['busy'] = True
        callback.update({'call': call_uuid})
        Thread(target=self.logout_helper, args=(callback,), daemon=True).start()
        return self.callback(callback)

    def logout_helper(self, callback: dict):
        connection_uuid = callback['connection']
        call_uuid = callback['call']
        connection = self.connections[connection_uuid]
        call = self.storage[connection_uuid]['calls'][call_uuid]
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: call['warnerror'].append(e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: call['print'].append(e)
        try:
            return_r = DSI.datashield_logout(connection)
            call['busy'] = False
            self.storage[connection_uuid]['busy'] = False
            # del self.connections[callback['connection']]
            self.function_callbacks_storage[connection_uuid][call_uuid] = None
            return None
        except Exception as err:
            call['busy'] = False
            self.storage[connection_uuid]['busy'] = False
            err_str = str(err)
            if 'datashield.errors' in str(err):
                err_str += str(DSI.datashield_errors())
            self.function_callbacks_storage[connection_uuid][call_uuid] = {'error': err_str}
            raise fdrtd_server.exceptions.InternalServerError(err_str)

    def get_status(self, callback):
        connection_uuid = callback['connection']
        call_uuid = callback['call']
        try:
            return self.storage[connection_uuid]['calls'][call_uuid]
        except KeyError:
            if connection_uuid not in self.storage:
                raise fdrtd_server.exceptions.InvalidParameter(f'connection {connection_uuid}', 'not found')
            else:
                raise fdrtd_server.exceptions.InvalidParameter(f'call {call_uuid}', 'not found')

    def get_result(self, callback):
        connection_uuid = callback['connection']
        call_uuid = callback['call']
        try:
            return self.function_callbacks_storage[connection_uuid][call_uuid]
        except KeyError:
            if connection_uuid not in self.function_callbacks_storage:
                raise fdrtd_server.exceptions.InvalidParameter(f'connection {connection_uuid}', 'not found')
            else:
                raise fdrtd_server.exceptions.InvalidParameter(f'call {call_uuid}', 'not found')
