from datetime import datetime
from PyQt5 import QtWidgets, QtCore
import sys
import time
import numpy as np

from mca_api.data import DataManager

from imcar.gui.helper import decorate_log_calls


class LogModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super(LogModel, self).__init__()
        dummy = (str(datetime.now()), "manager.add_stop_callback(<function ShellWidget.__init__.<locals>.stop_occurred at 0x7f4e72b480d0>)", "random_return_stuff")
        self._data = [dummy]
        self.record_length = 1000
        
        self.columns = [
            "Time",
            "Command",
            "Result",
            ]

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        if len(self._data) > 0:
            return len(self._data[0])
        else:
            return 0
    
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return str(self.columns[section])

            return ""
    
    def append(self, time, call_str, res_str):
        self._data.insert(0, (time, call_str, res_str))
        if len(self._data) > self.record_length:
            self._data.pop(len(self._data) - 1)
            
        self.layoutChanged.emit()
        
    def removeInitial(self):
        self._data.pop()

class OneShotSignal:
    emitted = False
    
    def emit(self):
        self.emitted = True


import json
import http.server
import socketserver
import socket
from http import HTTPStatus
from imcar.gui.helper import markdown_to_html
from urllib.parse import unquote
from importlib.resources import files

class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True # Avoid port-in-use issues

class ShellServer:
    PORT = 40405
    wrapped = None
    server = None

    class CustomAPIHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, request, client_address, server):
            super().__init__(request, client_address, server)
        
        def do_POST(self):
            assert len(self.path) > 2
            assert self.path[0] == "/"

            _, function, *args = self.path.split("/")
            
            if not ShellServer.is_valid_function(function):
                self.send_response(HTTPStatus.NOT_FOUND)
                return
            
            functionobject = getattr(ShellServer.wrapped, function)
            
            if not len(args) == len(functionobject.__annotations__):
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(bytes(str(f"Expected {functionobject.__annotations__.keys()}, got {repr(args)}").encode()))
                return
            
            try:
                parsed_args = [_type(unquote(arg)) for _type, arg in zip(functionobject.__annotations__.values(), args)]
                result = functionobject(*parsed_args)
            except Exception as e:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(bytes(str(e).encode()))
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(json.dumps(result).encode()))


        def do_GET(self):
            message = ""
            if self.path != "/":
                message = """
**Path not found. To run a function, try submitting a POST request instead of a GET request.**  

---

"""

            htmldoc = markdown_to_html(message + ShellServer.get_api_doc())

            with open(files("imcar").joinpath("gui/shell_POST.html")) as f:
                post_snippet = f.read()
            
            htmldoc = htmldoc.replace("<body>", "<body>" + post_snippet)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "	text/html")
            self.end_headers()
            self.wfile.write(bytes(htmldoc.encode()))

    def run_tick():
        assert ShellServer.server
        ShellServer.server.handle_request()
        return QtCore.QTimer.singleShot(10, ShellServer.run_tick)
    
    def start(wrapped):
        ShellServer.wrapped = wrapped
        ShellServer.server = ReuseTCPServer(("0.0.0.0", ShellServer.PORT), ShellServer.CustomAPIHandler)
        ShellServer.server.timeout = 0
        ShellServer.run_tick()
    
    def is_valid_function(name):
        assert ShellServer.wrapped != None

        return name in [
            "untimed_start_selected_device",
            "stop_selected_device",
            "clear_events",
            "get_selected_device_description",
            "get_selected_device_state",
            "new_snapshot",
        ]
        #return name and name in dir(ShellServer.wrapped) \
        #    and callable(getattr(ShellServer.wrapped, name)) \
        #    and name[0] != "_" \
        #    and "callback" not in name

    def get_api_doc():
        assert ShellServer.wrapped != None

        documentation = ""

        for function in dir(ShellServer.wrapped):
            if not ShellServer.is_valid_function(function):
                continue
            
            functionobject = getattr(ShellServer.wrapped, function)
            documentation += f"""`/{function}/{"/".join([f"<{x}>" for x in functionobject.__annotations__])}`

Parameters:  """ + \
            "\n".join([f"    {_param}: {_type}  " for _param, _type in functionobject.__annotations__.items()]) + \
f"""

Documentation:  
```
{functionobject.__doc__}  
```

---
"""

        return documentation

class ShellLogger:
    def __init__(self, manager, shell_log):        
        decorate_log_calls(DataManager, self.log_calls)
        
        self.shell_log = shell_log
        self.shell_log_model = LogModel()
        self.shell_log.setModel(self.shell_log_model)
        self.shell_log.resizeColumnsToContents()
        self.shell_log_model.removeInitial()
        
    
    def log_calls(self, name, args, kwargs, res):
        if type(args[0]) == DataManager:
            call_str = "manager."
            str_args = [repr(arg) for arg in args[1:]]
        else:
            call_str = "DataManager."
            str_args = [repr(arg) for arg in args]
            
        for key, value in kwargs.items():
            str_args.append(f"{key}={value}")
            
        call_str += "{}({})".format(name, ", ".join(str_args))
        self.shell_log_model.append(str(datetime.now()), call_str, repr(res))
        
