# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from imcar.gui.helper import QHLine

def label_text(name, value, unset):
    """
    Text to label a property
    """
    if unset:
        return "<b>{}</b> <pre>State: <i>unset</i></pre>".format(name)
    return "<b>{}</b> <pre>State: {}</pre>".format(name, value)
    
class DeviceConfig(QtWidgets.QDialog):
    def __init__(self, properties):
        super(DeviceConfig, self).__init__()
        self.properties = properties
        device_name = properties.device.name

        # Setup UI
        self.setWindowTitle("Device Settings")
        self.main_widget = QtWidgets.QVBoxLayout(self)

        show_indirect = len(properties.indirect) > 0
        show_direct = len(properties.direct) > 0
        
        self.labels = {}

        if show_indirect:
            # Indirect settings
            self.main_widget.addWidget(QtWidgets.QLabel("Later applied settings for device \"{}\"".format(device_name)))

            self.scrollArea = QtWidgets.QScrollArea()
            if show_direct:
                sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
                self.scrollArea.setSizePolicy(sizePolicy)
            self.scrollArea.setWidgetResizable(True)
            self.scrollAreaWidgetContents = QtWidgets.QWidget()
            gridLayout = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
            gridLayout.setContentsMargins(0, 0, 0, 0)

            for i, _property in enumerate(properties.indirect):
                label = QtWidgets.QLabel(
                        label_text(_property.name, _property.current_value, _property.unset)
                    )
                self.labels[_property] = label
                gridLayout.addWidget(label,
                                          2*i, 0, 1, 1)
                gridLayout.addWidget(_property.get_ui(),
                                          2*i, 1, 1, 1)
                gridLayout.addWidget(QHLine(), 2*i+1, 0, 1, 2)

            self.scrollArea.setWidget(self.scrollAreaWidgetContents)
            self.main_widget.addWidget(self.scrollArea)

            if not show_direct:
                spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
                gridLayout.addItem(spacerItem, 9999, 1, 1, 1)

            self.buttonBox = QtWidgets.QDialogButtonBox()
            self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
            self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Close|QtWidgets.QDialogButtonBox.Save)
            self.main_widget.addWidget(self.buttonBox)
            self.buttonBox.accepted.connect(self._accept)
            self.buttonBox.rejected.connect(self.reject)
        elif not show_direct:
            self.main_widget.addWidget(QtWidgets.QLabel("Device " + device_name + " does not provide settings."))

        if show_direct and show_indirect:
            self.main_widget.addWidget(QHLine())

        if show_direct:
            self.main_widget.addWidget(QtWidgets.QLabel("Directly applied settings for device " + device_name))

            self.scrollArea_2 = QtWidgets.QScrollArea()
            self.scrollArea_2.setWidgetResizable(True)
            self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
            gridLayout = QtWidgets.QGridLayout(self.scrollAreaWidgetContents_2)
            gridLayout.setContentsMargins(0, 0, 0, 0)
            
            for i, _property in enumerate(properties.direct):
                label = QtWidgets.QLabel(
                        label_text(_property.name, _property.current_value, _property.unset)
                    )
                self.labels[_property] = label
                gridLayout.addWidget(label,
                                          2*i, 0, 1, 1)
                gridLayout.addWidget(_property.get_ui(),
                                          2*i, 1, 1, 1)
                apply_button = QtWidgets.QPushButton("Apply")
                def run_apply(x,_property=_property, label=label):
                    """
                    _property = _property for to prevent late binding
                    """
                    _property.run_apply(properties.device)
                    label.setText(label_text(_property.name, _property.current_value, _property.unset))
                apply_button.clicked.connect(run_apply)
                gridLayout.addWidget(apply_button,
                                          2*i, 2, 1, 1)

                gridLayout.addWidget(QHLine(), 2*i+1, 0, 1, 3)


                self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)
                self.main_widget.addWidget(self.scrollArea_2)

            spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            gridLayout.addItem(spacerItem, 9999, 1, 1, 1)


    def _accept(self):
        self.properties.apply_indirect()
        
        for _property in self.properties.indirect:
            label = self.labels[_property]
            label.setText(label_text(_property.name, _property.current_value, _property.unset))

    def reject(self):
        self.close()

    def closeEvent(self,evt):
        """
        Rejects all unapplied changes after warning.
        """
        for _property in self.properties.direct:
            if _property.new_value is not None:
                res = QtWidgets.QMessageBox.warning(self, 
                            "Discarding changes",
                            'You did not apply all changes in "Directly applied properties". Discard unapplied changes?',
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                
                if res == QtWidgets.QMessageBox.No:
                    evt.ignore()
                    return
                
                # User warned, proceed
                break

        self.properties.reject_indirect()
        self.properties.reject_direct()

        evt.accept()

