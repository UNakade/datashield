## `DataSHIELD` plugin for `fdrtd` server

This plugin allows `fdrtd` clients to use `DataSHIELD`.
The plugin is written in `Python` and uses the `rpy2` library.


### Requirements:
- These `Python` libraries:
  - `rpy2` (`pip install rpy2[all]`)
  - `numpy`
  - `json`
- In addition to `R`, these `R` libraries:
  - `DSI`
  - `DSOpal`
  - `DSLite`
  - `dsBaseClient` (for installation instructions, please visit the [DataSHIELD website](https://www.datashield.org/) and the [DataSHIELD wiki](https://data2knowledge.atlassian.net/wiki/spaces/DSDEV/overview))
  - `fields`
  - `metafor`
  - `ggplot2`
  - `gridExtra`
  - `data.table`
- `curl` library for your operating system

### Usage:
Here, it is assumed that a DataSHIELD virtual machine is currently accessible at the IP address `192.168.56.100:8080` (please visit the [DataSHIELD wiki](https://data2knowledge.atlassian.net/wiki/spaces/DSDEV/overview) for instructions about how to get it running) and the `fdrtd` server is running on `localhost` on port `5000`.

```Python
# First, initialize the fdrtd api:
import fdrtd
interface = fdrtd.HttpInterface("http://localhost:5000")  # insert appropriate server url here
api = fdrtd.Api(interface)
# Next, select the datashield microservice:
connection = api.select_microservice(microservice='datashield')
# Define required variables for logging in:
# list of servers is a list of kwargs dictionaries which will be passed on to the 
# DSI::newDSLoginBuilder()$append() function
list_of_servers = [
    {"server": "study1", "url": "http://192.168.56.100:8080/", "user": "administrator", "password": "datashield_test&",
     "table": "CNSIM.CNSIM1", "driver": "OpalDriver"},
    {"server": "study2", "url": "http://192.168.56.100:8080/", "user": "administrator", "password": "datashield_test&",
     "table": "CNSIM.CNSIM2", "driver": "OpalDriver"},
    {"server": "study3", "url": "http://192.168.56.100:8080/", "user": "administrator", "password": "datashield_test&",
     "table": "CNSIM.CNSIM3", "driver": "OpalDriver"}
]
assign = True
symbol = 'D'
login_return = connection.login(parameters={'list_of_servers': list_of_servers, 'assign': assign, 'symbol': symbol})
# You can now start using dsBaseClient functions in one of two ways:
quantileMean_1 = connection.quantileMean(parameters={'x': 'D$LAB_HDL'})
quantileMean_2 = connection.call_function(parameters={'x': 'D$LAB_HDL'}, func='ds.quantileMean')
# If there is a '.' in the function name, 
# please replace them by '_' if calling the function without specifying the 'func' argument
# e.g. if you want to call ds.matrixDet.report, either use connection.matrixDet_report(parameters)
# or use connection.call_function(parameters, func='ds.matrixDet.report')

# To logout from the DataSHIELD servers:
logout_return = connection.logout()
```