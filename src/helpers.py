import numpy as np
import json

import rpy2
from rpy2.robjects.packages import importr

import fdrtd.server

base = importr('base')
DSI = importr('DSI')
dsBaseClient = importr('dsBaseClient')
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


def r_to_json(output, return_serial_json):
    if return_serial_json:
        return jsonlite_R.serializeJSON(output)[0]
    else:
        return second_sweep(first_sweep(json.loads(jsonlite_R.serializeJSON(output)[0])))


def defaults(func, parameters=None, **kwargs):
    if parameters is None:
        parameters = {}
    parameters.update(**kwargs)
    combined = {}
    formals = func.formals()
    if isinstance(formals, type(rpy2.rinterface.NULL)):
        formals = {}
    else:
        formals = dict((n, o[0]) for n, o in formals.items())
    for key in formals:
        if key not in parameters:
            if key[-5:] == '.name' and key[:-5] in parameters:
                combined[key] = parameters[key[:-5]]
            elif key.replace('.', '_') in parameters:
                combined[key] = parameters[key.replace('.', '_')]
            else:
                combined[key] = formals[key]
        else:
            combined[key] = parameters[key]
    return combined


def login_params_string_builder(parameters, uuid):
    r_params = 'logins=builder%s$build()' % uuid.replace('-', '')
    for key in parameters:
        if key in {'assign', 'missings'}:
            r_params += f', {key}={str(parameters[key]).upper()}'
        elif key in {'symbol', 'id_name', 'id.name', 'restore'}:
            r_params += f', {key.replace("_", ".")}="{parameters[key]}"'
        elif key == 'variables':
            if isinstance(parameters['variables'], list):
                r_params += ', variables=c('
                for variable in parameters['variables']:
                    r_params += f'"{variable}", '
                r_params = r_params[:-2] + ')'
            else:
                r_params += f', variables="{parameters["variables"]}"'
    return r_params


def handle_error(err, func):
    if func == 'login':
        if 'The server parameter cannot be empty' in err:
            return fdrtd.server.exceptions.MissingParameter('server')
        elif 'The url parameter cannot be empty' in err:
            return fdrtd.server.exceptions.MissingParameter("url")
        elif 'Duplicate server name: ' in err:
            return fdrtd.server.exceptions.InvalidParameter('server', 'duplicate')
        elif 'The provided login details is missing both table and resource columns' in err:
            return fdrtd.server.exceptions.InvalidParameter('table, resource', 'both missing')
        elif 'Unauthorized' in err:
            return fdrtd.server.exceptions.ApiError(401, 'Unauthorized')
        else:
            return fdrtd.server.exceptions.InternalServerError(err)


def extract_connections(connections, parameters_servers):
    if isinstance(parameters_servers, list):
        connection = connections.rx(base.c(*parameters_servers))
    else:
        connection = connections.rx(parameters_servers)
    return connection
