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
        
