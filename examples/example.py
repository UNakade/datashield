# This example assumes that the fdrtd_server is running on http://localhost:5000
# which is very easy to do, just follow these 4 steps:
# git clone https://github.com/fdrtd/server
# cd server
# git clone https://github.com/fdrtd/protocol_DataSHIELD
# python3 -m openapi_server -port:5000

# Now on the client side:
# Initializing the fdrtd api:
import fdrtd
interface = fdrtd.HttpInterface("http://localhost:5000")  # insert appropriate server url here
api = fdrtd.Api(interface)

# Selecting the DataSHIELD login microservice:
login = api.select_microservice(protocol='DataSHIELD', microservice='login')
# Defining required variables for logging in:

# list_of_servers is a list of kwargs dictionaries which will be passed on to the
# DSI::newDSLoginBuilder()$append() function This example assumes that a datashield virtual machine
# is available at http://192.168.56.100:8080/. For instructions on how to get it running, please
# visit the DataSHIELD wiki (link in README).

list_of_servers = [
    {"server": "study1", "url": "http://192.168.56.100:8080/", "user": "administrator", 
     "password": "datashield_test&", "table": "CNSIM.CNSIM1", "driver": "OpalDriver"},
    {"server": "study2", "url": "http://192.168.56.100:8080/", "user": "administrator", 
     "password": "datashield_test&", "table": "CNSIM.CNSIM2", "driver": "OpalDriver"},
    {"server": "study3", "url": "http://192.168.56.100:8080/", "user": "administrator", 
     "password": "datashield_test&", "table": "CNSIM.CNSIM3", "driver": "OpalDriver"}
]

login_callback = login.login(list_of_servers=list_of_servers, assign=True, symbol='D')
# with protocol_DataSHIELD, you can print the progress of any function live, just like it is visible
# in R when a function is called, a function_callback is returned to the client while the function
# keeps running on the server in a separate thread. While it is running, you can use the
# following "result" function to get the live progress bar it will also return the end result of
# the function call.

def result(function_callback):
    status_old = function_callback.get_status()
    print(''.join(status_old['warnerror']), end='')
    while status_old['busy']:
        status_new = function_callback.get_status()
        if len(status_new['warnerror']) != len(status_old['warnerror']):
            print(''.join(status_new['warnerror'][len(status_old['warnerror']):]), end='')
        status_old = status_new
    print(''.join(status_old['print']))
    return function_callback.get_result()

connection_callback = result(login_callback)
# The end result of a login function called on the login microservice is a connection callback. You
# can use it to call functions from the dsBaseClient library. There are multiple convenient ways of
# calling these functions. You can either pass the arguments to the function directly as kwargs, or
# you can specify them as a dictionary and pass it as the kwarg "parameters", or you can mix them
# both together. e. g.:
# connection_callback.quantileMean(x='D$LAB_HDL')
# connection_callback.quantileMean(parameters={'x':'D$LAB_HDL'}, type='split')

# Please note that "ds." has been removed from the beginning of the function name. Also,
# the "datasources" kwarg is not to be used here. By default, all the servers in the connection are
# passed on to the "datasources" argument. If you need to perform the computation on only a limited
# number of servers, please include the argument "servers" as a list of indices as R would index
# them (indexing begins at 1 in R and at 0 in Python).

# Another way of calling the functions is:
# connection_callback.call_function(func='ds.quantileMean', x='D$LAB_HDL')
# connection_callback.call_function(func='ds.quantileMean', parameters={'x':'D$LAB_HDL'})

# The client should note that in Python, the "." character is reserved whereas in R, it can be
# freely used in variable names. Hence, if passing an argument that contains a "." in the name,
# please replace it by an "_" or use the parameters dictionary instead. 

# Same goes for function names. e. g.:
# connection_callback.matrixDet_report(parameters) (instead of matrixDet.report)
# connection_callback.dataFrame(parameters, row_names) (instead of row.names)

# Full example:
quantileMean_result = result(connection_callback.quantileMean(x='D$LAB_HDL'))
print(quantileMean_result)

# To logout from the DataSHIELD servers:
logout_result = result(connection_callback.logout())
