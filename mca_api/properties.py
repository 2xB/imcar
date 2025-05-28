# -*- coding: utf-8 -*-

import numpy as np
from PyQt5 import QtWidgets

class EmptyProperties:
    """
    Collects all properties of MCAs. To be implemented by each MCA.

    Example:
        class MyProperties(EmptyProperties):
            direct = [PropertyInt("Prop 1",1,3,2),
                      PropertyInt("Prop 2",-10,50,2)]
            indirect = [PropertyBoolean("Prop indirect 1",False),
                        PropertyInt("Prop Int 3",2,22,21)]
    """
    direct   = []
    indirect = []

    def __init__(self, device):
        self.device = device
        

    def __str__(self):
        result = "{ "
        for param in self.direct+self.indirect:
            if param.unset:
                result += "'" + param.name + "':'unset', "
            else:
                result += "'" + param.name + "':" + str(param.current_value) + ", "
        result += "}"
        return result

    def apply_direct(self):
        for obj in self.direct:
            obj.run_apply(self.device)

    def apply_indirect(self):
        for obj in self.indirect:
            obj.run_apply(self.device)

    def reject_direct(self):
        for obj in self.direct:
            obj.reject()

    def reject_indirect(self):
        for obj in self.indirect:
            obj.reject()

class Property:
    """
    Abstract property.
    """

    old_value = None

    def __init__(self, name, default_value, apply_handler_function=None, documentation = "", unset_at_start=False):
        """
        Abstract property. apply_handler_function(value,device) is run after hitting "apply" for
        direct and after saving the config for indirect properties.
        """
        self.name = name
        self.apply_handler_function = apply_handler_function
        self.documentation = documentation
        self.new_value = None
        self.default_value = default_value
        self._current_value = default_value
        self.unset = unset_at_start

    def run_apply(self, device):
        if self.new_value is not None:
            self._current_value = self.new_value
            self.new_value = None
        
        self.unset = False

        if self.apply_handler_function is not None:
            self.apply_handler_function(device, self.current_value)

    @property
    def current_value(self):
        return self._current_value

    @current_value.setter
    def current_value(self, value):
        raise RuntimeError("Used setter of current_value. Call new_value and apply it instead.")

    def reject(self):
        """
        Discard current value. Called after hitting "Cancel" for every property and after hitting "Save" for direct
        properties.
        """
        self.new_value = None

    def get_ui(self):
        return QtWidgets.QLabel("No UI for this property available")

class PropertyInt(Property):
    """
    Ranged integer property.
    """
    def __init__(self, name, min_value, max_value, *args, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        super(PropertyInt, self).__init__(name, *args, **kwargs)

    def get_ui(self):
        box = QtWidgets.QSpinBox()
        box.setMinimum(self.min_value)
        box.setMaximum(self.max_value)
        box.setValue(self.current_value)
        def _valueChanged(value):
            if self.min_value > value or self.max_value < value:
                raise ValueError("Value out of bounds: " + str(value))
            self.new_value = value
        box.valueChanged.connect(_valueChanged)
        return box

class PropertyDict(Property):
    """
    Dict property. Keys are visible in the UI, values are not. Default value is key.

    Dictionaries are order-preserving since Python 3.7.
    """
    def __init__(self, name, dict_value, *args, **kwargs):
        self.dict_value = dict_value
        super(PropertyDict, self).__init__(name, *args, **kwargs)

    def get_key(self):
        """
        Returns key of current selection.
        """
        return self.current_value

    def get_value(self):
        """
        Returns value of current selection.
        """
        return self.dict_value[self.current_value]

    def get_ui(self):
        box = QtWidgets.QComboBox()
        for key, value in self.dict_value.items():
            box.addItem(key, value)
        box.setCurrentIndex(list(self.dict_value.keys()).index(self.current_value))
        def _valueChanged(index):
            value = box.itemText(index)
            if value not in self.dict_value:
                raise ValueError("Value out of bounds: " + str(value))
            self.new_value = value
        box.currentIndexChanged.connect(_valueChanged)
        return box

class PropertyBoolean(Property):
    """
    Boolean property.
    """
    def __init__(self, name, *args, **kwargs):
        super(PropertyBoolean, self).__init__(name, *args, **kwargs)

    def get_ui(self):
        box = QtWidgets.QCheckBox()
        box.setChecked(self.current_value)
        def _valueChanged(value):
            self.new_value = value != 0
        box.stateChanged.connect(_valueChanged)
        return box
