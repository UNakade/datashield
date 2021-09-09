import functools
import uuid as _uuid
from threading import Thread
import importlib.util
from pathlib import Path

import rpy2
import rpy2.rinterface
import rpy2.rinterface_lib
from rpy2.robjects.packages import importr

import fdrtd.server
from fdrtd.server.microservice import Microservice
try:
    from fdrtd.plugins.protocol_DataSHIELD.src import helpers
except ImportError:
    spec_helpers = importlib.util.spec_from_file_location('helpers', Path(__file__).resolve().parent / 'helpers.py')
    helpers = importlib.util.module_from_spec(spec_helpers)
    spec_helpers.loader.exec_module(helpers)

consolewrite_warnerror_backup = rpy2.rinterface_lib.callbacks.consolewrite_warnerror
consolewrite_print_backup = rpy2.rinterface_lib.callbacks.consolewrite_print

base = importr('base')
DSI = importr('DSI')
DSOpal = importr('DSOpal')
dsBaseClient = importr('dsBaseClient')
grDevices = importr('grDevices')
jsonlite_R = importr('jsonlite')


class Connection(Microservice):

    def __init__(self, bus, endpoint):

        super().__init__(bus, endpoint)

        self.connections = {}
        self.storage = {}
        self.function_results_storage = {}
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

    def make_public(self):
        functions_dict = {}
        funcnames = list(base.ls('package:dsBaseClient'))
        for func in funcnames:
            functions_dict[func[3:].replace('.', '_')] = functools.partial(self.call_function, func=func)
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
        self.function_results_storage[uuid] = {}
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
        call = self.storage[connection_uuid]['calls'][call_uuid]
        if 'servers' in parameters:
            connection = helpers.extract_connections(connection, parameters['servers'])
        return_serial_json = parameters.get('return_serial_JSON', False)
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: call['warnerror'].append(e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: call['print'].append(e)
        parameters_used = helpers.defaults(getattr(dsBaseClient, func_), parameters)
        if 'datasources' in parameters_used:
            parameters_used['datasources'] = connection
        if func_ not in dir(dsBaseClient):
            self.storage[connection_uuid]['busy'] = False
            call['busy'] = False
            raise fdrtd.server.exceptions.FunctionNotFound(f'{func} not in dsBaseClient')
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
                self.storage[connection_uuid]['calls'][call_uuid]['plot_uuid'] = plot_uuid
                if func in self.return_types['return']:
                    return_dict['return_json'] = helpers.r_to_json(return_r, return_serial_json)
                self.storage[connection_uuid]['busy'] = False
                self.storage[connection_uuid]['calls'][call_uuid]['busy'] = False
                self.function_results_storage[connection_uuid][call_uuid] = return_dict
                return None
            else:
                return_r = getattr(dsBaseClient, func_)(**parameters_used)
                self.storage[connection_uuid]['busy'] = False
                self.storage[connection_uuid]['calls'][call_uuid]['busy'] = False
                if func in self.return_types['return']:
                    self.function_results_storage[connection_uuid][call_uuid] = helpers.r_to_json(return_r,
                                                                                                  return_serial_json)
                    return None
                self.function_results_storage[connection_uuid][call_uuid] = None
                return None
        except Exception as err:
            self.storage[connection_uuid]['busy'] = False
            self.storage[connection_uuid]['calls'][call_uuid]['busy'] = False
            if 'datashield.errors' in str(err):
                err_str = f'Error: \n {str(err)} \n datashield.errors(): \n {str(DSI.datashield_errors())}'
            else:
                err_str = f'Error: \n{str(err)}'
            self.storage[connection_uuid]['calls'][call_uuid]['error'] = err_str
            raise fdrtd.server.exceptions.InternalServerError(err_str)

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
            self.storage[connection_uuid]['calls'][call_uuid]['busy'] = False
            self.storage[connection_uuid]['busy'] = False
            if isinstance(return_r, type(rpy2.rinterface.NULL)):
                self.function_results_storage[connection_uuid][call_uuid] = None
            else:
                self.function_results_storage[connection_uuid][call_uuid] = helpers.r_to_json(return_r, False)
            return None
        except Exception as err:
            self.storage[connection_uuid]['calls'][call_uuid]['busy'] = False
            self.storage[connection_uuid]['busy'] = False
            if 'datashield.errors' in str(err):
                err_str = f'Error: \n {str(err)} \n datashield.errors(): \n {str(DSI.datashield_errors())}'
            else:
                err_str = f'Error: \n{str(err)}'
            self.storage[connection_uuid]['calls'][call_uuid]['error'] = err_str
            raise fdrtd.server.exceptions.InternalServerError(err_str)

    def get_status(self, callback):
        connection_uuid = callback.get('connection')
        call_uuid = callback.get('call')
        try:
            return self.storage[connection_uuid]['calls'][call_uuid]
        except KeyError:
            if connection_uuid not in self.storage:
                raise fdrtd.server.exceptions.MissingParameter(f'connection {connection_uuid}')
            else:
                raise fdrtd.server.exceptions.MissingParameter(f'call {call_uuid}')

    def get_result(self, callback):
        connection_uuid = callback.get('connection')
        call_uuid = callback.get('call')
        try:
            return self.function_results_storage[connection_uuid][call_uuid]
        except KeyError:
            if connection_uuid not in self.function_results_storage:
                raise fdrtd.server.exceptions.MissingParameter(f'connection {connection_uuid}')
            else:
                raise fdrtd.server.exceptions.MissingParameter(f'call {call_uuid}')
