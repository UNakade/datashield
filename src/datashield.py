import functools
import uuid as _uuid
from fdrtd_server.microservice import Microservice
import fdrtd_server
import rpy2
import rpy2.rinterface
import rpy2.robjects
import rpy2.rinterface_lib
from rpy2.robjects.packages import importr
from rpy2.robjects import r
import numpy as np
import json

TRUE, FALSE = True, False
NULL = rpy2.rinterface.NULL

consolewrite_warnerror_backup = rpy2.rinterface_lib.callbacks.consolewrite_warnerror
consolewrite_print_backup = rpy2.rinterface_lib.callbacks.consolewrite_print

global_warnerror_array = []
global_print_array = []


def custom_callbacks(array, e):
    array.append(e)


rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: custom_callbacks(global_warnerror_array, e)
rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: custom_callbacks(global_print_array, e)

base = importr('base')
DSI = importr('DSI')
DSOpal = importr('DSOpal')
dsBaseClient = importr('dsBaseClient')
grDevices = importr('grDevices')
jsonlite_R = importr('jsonlite')

types_dict = {'integer': int, 'double': float, 'character': str, 'complex': complex, 'logical': bool}


def first_sweep(d):
    if isinstance(d, list):
        if len(d) == 1:
            return first_sweep(d[0])
        else:
            return list([first_sweep(d[i]) for i in range(len(d))])
    elif not isinstance(d, dict):
        return d
    else:
        if 'type' not in d:
            return dict((k, first_sweep(v)) for (k, v) in d.items())
        elif d['type'] == 'NULL':
            return None
        elif d['type'] == 'list':
            tempd = {'value': first_sweep(d['value'])}
            if 'attributes' not in d:
                return tempd['value']
            else:
                for key in d['attributes']:
                    tempd[key] = first_sweep(d['attributes'][key])
                return tempd
        else:
            templist = list(map(lambda val: types_dict[d['type']](val) if val != 'NA' else 'NA', d['value']))
            if len(templist) == 1:
                templist = templist[0]
            if d['attributes'] == {}:
                return templist
            else:
                tempd = {'value': templist}
                for key in d['attributes']:
                    tempd[key] = first_sweep(d['attributes'][key])
                return tempd


def second_sweep(d):
    if isinstance(d, list):
        return list([second_sweep(d[i]) for i in range(len(d))])
    elif not isinstance(d, dict):
        return d
    elif d is None:
        return d
    else:
        if set(d.keys()) == {'value'}:
            return second_sweep(d['value'])
        elif set(d.keys()) == {'value', 'names'}:
            if not isinstance(second_sweep(d['value']), list):
                return {second_sweep(d['names']): second_sweep(d['value'])}
            else:
                return dict(zip(second_sweep(d['names']), second_sweep(d['value'])))
        elif set(d.keys()) == {'value', 'dim', 'dimnames'}:
            if isinstance(second_sweep(d['dim']), list):
                templist = np.reshape(second_sweep(d['value']), second_sweep(d['dim'])[::-1]).T.tolist()
                if isinstance(second_sweep(d['dimnames']), list):
                    if isinstance(second_sweep(d['dimnames'])[1], list):
                        colnames = [None] + second_sweep(d['dimnames'])[1]
                    else:
                        colnames = [None] + [second_sweep(d['dimnames'])[1]]
                    if len(templist) > 1:
                        for i in range(len(templist)):
                            templist[i] = [second_sweep(d['dimnames'])[0][i]] + templist[i]
                    else:
                        templist[0] = [second_sweep(d['dimnames'])[0]] + templist[0]
                    return [colnames] + templist
                elif isinstance(second_sweep(d['dimnames']), dict):
                    tempdimnames = second_sweep(d['dimnames']['value'])
                    rowcoltitles = second_sweep(d['dimnames']['names'])
                    if tempdimnames[0] is not None:
                        colnames = [rowcoltitles[0]] + tempdimnames[1]
                        for i in range(len(templist)):
                            templist[i] = [tempdimnames[0][i]] + templist[i]
                        return {rowcoltitles[1]: [colnames] + templist}
                    else:
                        if not all([tempdimnames[1][i] == '' for i in range(len(tempdimnames[1]))]):
                            return {rowcoltitles[1]: [tempdimnames[1]] + templist}
                        else:
                            return {rowcoltitles[1]: templist}
            else:
                return second_sweep(d['dimnames']) + second_sweep(d['value'])
        elif set(d.keys()) == {'value', 'names', 'row.names', 'class'}:
            templist = np.array(second_sweep(d['value'])).T.tolist()
            colnames = [None] + second_sweep(d['names'])
            if isinstance(second_sweep(d['row.names']), list):
                for i in range(len(templist)):
                    templist[i] = [second_sweep(d['row.names'])[i]] + templist[i]
            else:
                templist = [[second_sweep(d['row.names'])] + templist]
            return {'value': [colnames] + templist, 'class': second_sweep(d['class'])}
        elif set(d.keys()) == {'value', 'logarithm'}:
            if second_sweep(d['logarithm']):
                return np.e ** second_sweep(d['value'])
            else:
                return second_sweep(d['value'])
        elif set(d.keys()) == {'value', 'names', 'class'}:
            if not isinstance(second_sweep(d['value']), list):
                return {second_sweep(d['names']): second_sweep(d['value']), 'class': second_sweep(d['class'])}
            else:
                tempd = dict(zip(second_sweep(d['names']), second_sweep(d['value'])))
                tempd.update({'class': second_sweep(d['class'])})
                return tempd
        else:
            return d


def r_to_json(output):
    return second_sweep(first_sweep(json.loads(jsonlite_R.serializeJSON(output)[0])))


deprecated = ['ds.listOpals', 'ds.listServersideFunctions', 'ds.look', 'ds.meanByClass', 'ds.message',
              'ds.recodeLevels', 'ds.setDefaultOpals', 'ds.subset', 'ds.subsetByClass', 'ds.table1D', 'ds.table2D',
              'ds.vectorCalc']

return_types = {'return': set(base.ls('package:dsBaseClient')) - {'ds.exp', 'ds.assign', 'ds.c', 'ds.recodeLevels',
                                                                  'ds.changeRefGroup', 'ds.list', 'ds.log',
                                                                  'ds.vectorCalc', 'ds.subset', 'ds.sqrt',
                                                                  'ds.replaceNA', 'ds.abs', 'ds.subsetByClass',
                                                                  'ds.heatmapPlot', 'ds.contourPlot'},
                'plot': {'ds.histogram', 'ds.boxPlot', 'ds.contourPlot', 'ds.heatmapPlot', 'ds.scatterPlot'}}
path_to_temp_plot_storage = ''
input_type_requirements = {'x_vec': ['ds.vectorCalc']}
plot_filenames_dict = {}


class Connection(Microservice):

    def __init__(self, bus, endpoint):

        super().__init__(bus, endpoint)

        self.connection = NULL
        self.label = str(_uuid.uuid4())

    def list_functions(self):
        functions_dict = {
            'login': {'public': True, 'pointer': self.login},
            'call_function': {'public': True, 'pointer': self.call_function},
            'logout': {'public': True, 'pointer': self.logout}
        }
        funcnames = list(base.ls('package:dsBaseClient'))
        for func in funcnames:
            functions_dict[func[3:].replace('.', '_')] = {'public': True,
                                                          'pointer': functools.partial(self.call_function, func=func)}
        return functions_dict

    def login(self, parameters):
        login_warnerror_array = []
        login_print_array = []
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: custom_callbacks(login_warnerror_array, e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: custom_callbacks(login_print_array, e)
        return_dict = {}
        try:
            builder = r('builder <- DSI::newDSLoginBuilder()')
            for server in parameters['list_of_servers']:
                builder['append'](**server)
            self.connection = r('connections%s <- DSI::datashield.login(logins=builder$build(), assign=%s, symbol="%s")'
                                % (self.label.replace('-', ''), str(parameters.get('assign', False)).upper(),
                                   parameters.get('symbol', 'D')))
        except Exception as err:
            return_dict['error'] = str(err)
            if 'datashield.errors' in str(err):
                return_dict['datashield.errors'] = str(DSI.datashield_errors())
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: custom_callbacks(global_warnerror_array, e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: custom_callbacks(global_print_array, e)
        return_dict.update({'label': self.label, 'warnerror': ''.join(login_warnerror_array),
                            'print': ''.join(login_print_array)})
        if type(self.connection) is not type(NULL):
            return_dict['connection'] = list(map(str, self.connection))
        return return_dict

    def call_function(self, parameters, func):
        func_ = func.replace('.', '_')
        parameters_server = {}
        parameters_unused = {}
        func_warnerror_array = []
        func_print_array = []
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: custom_callbacks(func_warnerror_array, e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: custom_callbacks(func_print_array, e)
        func_formals = getattr(dsBaseClient, func_).formals()
        d = {}
        if type(func_formals) is not type(NULL):
            func_formals = list(func_formals.items())
            for n, o in func_formals:
                d[n] = o[0]
        for key in d:
            if key not in parameters:
                if key[-5:] == '.name' and key[:-5] in parameters:
                    parameters_server[key] = parameters[key[:-5]]
                else:
                    parameters_server[key] = d[key]
            else:
                parameters_server[key] = parameters[key]
        for key in parameters:
            if (key not in d) & (key + '.name' not in d):
                parameters_unused[key] = parameters[key]
        del parameters_server['datasources']
        try:
            if func_ in dir(dsBaseClient):
                if func in return_types['plot']:
                    plot_uuid = str(_uuid.uuid4())
                    plot_name = plot_uuid + '.png'
                    aspect_mul = 1
                    if (parameters_server['type'] == 'split') | (parameters_server['type'][0] == 'split'):
                        aspect_mul = len(self.connection)
                    grDevices.png(filename=path_to_temp_plot_storage + plot_name, height=10, width=aspect_mul * 10,
                                  units='in', res=300)
                    return_r = getattr(dsBaseClient, func_)(**parameters_server, datasources=self.connection)
                    grDevices.dev_off()
                    return_dict = {'warnerror': ''.join(func_warnerror_array), 'print': ''.join(func_print_array),
                                   'plot_file_uuid': plot_uuid}
                    plot_filenames_dict[plot_uuid] = path_to_temp_plot_storage + plot_name
                else:
                    return_r = getattr(dsBaseClient, func_)(**parameters_server, datasources=self.connection)
                    return_dict = {'warnerror': ''.join(func_warnerror_array), 'print': ''.join(func_print_array)}
                return_dict['return_json_R'] = jsonlite_R.serializeJSON(return_r)[0]
                if func in return_types['return']:
                    return_dict['return_json'] = r_to_json(return_r)
                else:
                    return_dict['return_json'] = {}
                rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: custom_callbacks(global_warnerror_array, e)
                rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: custom_callbacks(global_print_array, e)
                return return_dict
            else:
                raise fdrtd_server.exceptions.FunctionNotFound(func)
        except Exception as err:
            error_dict = {'warnerror': ''.join(func_warnerror_array), 'print': ''.join(func_print_array),
                          'error': str(err)}
            if 'datashield.errors' in str(err):
                error_dict['datashield.errors'] = str(DSI.datashield_errors())
            return error_dict

    def logout(self):
        logout_warnerror_array = []
        logout_print_array = []
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: custom_callbacks(logout_warnerror_array, e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: custom_callbacks(logout_print_array, e)
        return_dict = {}
        try:
            self.connection = DSI.datashield_logout(self.connection)
        except Exception as err:
            return_dict['error'] = str(err)
            if 'datashield.errors' in str(err):
                return_dict['datashield.errors'] = str(DSI.datashield_errors())
        return_dict['warnerror'] = ''.join(logout_warnerror_array)
        return_dict['print'] = ''.join(logout_print_array)
        rpy2.rinterface_lib.callbacks.consolewrite_warnerror = lambda e: custom_callbacks(global_warnerror_array, e)
        rpy2.rinterface_lib.callbacks.consolewrite_print = lambda e: custom_callbacks(global_print_array, e)
        return return_dict
