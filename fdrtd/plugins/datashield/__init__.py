from fdrtd.plugins.datashield.login import Login
from fdrtd.plugins.datashield.connection import Connection

def get_microservices():
    return [
        {
            "identifiers": {
                "namespace": "fdrtd",
                "protocol": "DataSHIELD",
                "version": "0.3.0",
                "microservice": "login"
            },
            "class": Login,
            "public": [
                "login",
                "get_status",
                "get_result"
            ]
            },
            {
               "identifiers": {
                   "namespace": "fdrtd",
                   "protocol": "DataSHIELD",
                   "version": "0.3.0",
                   "microservice": "connection"
               },
               "class": Connection,
               "public": [
                   "call_function",
                   "logout",
                   "get_status",
                   "get_result"
               ]
        }
    ]
