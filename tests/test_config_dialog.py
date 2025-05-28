# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from imcar.gui.device_config import DeviceConfig
from test_properties import dummy_properties
from PyQt5 import QtWidgets

def main():
    app = QtWidgets.QApplication(["Test Device Config"])
    for properties in dummy_properties():
        device_config = DeviceConfig(properties)
        device_config.exec_()

if __name__ == "__main__":
    main()
