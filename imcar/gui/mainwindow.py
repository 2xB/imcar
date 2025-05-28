import sys
import os
from PyQt5 import QtCore, QtWidgets, QtGui, uic
import sip
import pyqtgraph as pg
import numpy as np
import faulthandler
import signal
from importlib.resources import files

from mca_api.data import DataManager
from mca_api.device import DeviceState

from imcar.workers import FittingWorker
from imcar.gui.helper import QHLine, mathTex_to_QPixmap, apply_dark_palette, markdown_to_html
from imcar.gui.device_config import DeviceConfig
from imcar.gui.shell import ShellLogger, ShellServer
from imcar.gui.snapshot_save_dialog import *

import _thread

def relative_to_absolute_path(rel_path):
    return files("imcar").joinpath(rel_path)

def main(faultguard_data=None, profiling = False, testing = False):
    print(sys.argv)
    
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = init_qt_app()
    main_window = MCARec(faultguard_data, profiling, testing)
    main_window.showMaximized()
    app.exec_()

def init_qt_app():
    app = QtWidgets.QApplication([sys.argv])
    apply_dark_palette(app)
    app.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'icon.png')))
    return app

class MCARec(QtWidgets.QMainWindow):
    def __init__(self, faultguard_data=None, profiling=False, testing=False):
        QtWidgets.QMainWindow.__init__(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'MCA_simple_UI.ui'), self)
        
        self.mgr = DataManager.get_mgr(faultguard_data, profiling, testing)
        
        # Shell
        # As early as possible to log as much as possible
        self.shell_widget = ShellLogger(self.mgr, self.shell_log)

        # Start web server for programmatic access
        try:
            ShellServer.start(self.mgr)
        except OSError as e:
            QtWidgets.QMessageBox.critical(None, "Port in use", \
                                        "Port 40405 is already in use. This is required for programmatic control of iMCAr. Maybe an instance of iMCAr is already running?")
            sys.exit(-1)
        # Show documentation
        shell_doc = markdown_to_html(ShellServer.get_api_doc())
        self.shell_commandoverview.setHtml(shell_doc)
        
        # Record timer
        self.record_timer = QtCore.QTimer(self)
        self.record_timer.timeout.connect(self.record_tick)
        self.record_timer.setSingleShot(True)
        
        self.mgr.add_tick_request_callback(self.record_timer.start)
        self.mgr.add_stop_callback(self.record_timer.stop)

        self.mgr.add_start_callback(self.update_device_status)
        self.mgr.add_stop_callback(self.update_device_status)
        
        self.mgr.add_snapshots_changed_callback(self.redraw_snapshots)
        self.mgr.add_snapshots_changed_callback(self.snap_evolution_update)
        self.mgr.add_snapshots_changed_callback(self.change_snapshot)
        self.mgr.add_snapshots_changed_callback(self.update_plot_live_main) # For snapshots shown in live plot

        self.mgr.add_record_existence_callback(self.update_record_exists)

        self.mgr.add_device_changed_callback(self.device_changed)
        self.mgr.add_device_errored_callback(self.device_errored)

        # Create Range Selector / Calibration Widgets
        self.snap_view.addLinearRegion()
        
        def calibrationChanged(self=self):
            cal = self.snap_view.calibrationWidget.getCalibration()
            for caxis in (self.snap_view.caxis, self.live_view.caxis):
                if cal is not None:
                    caxis.setCalibration(*cal)
                    caxis.setCalibration(*cal)
                    caxis.setVisible(True)
                else:
                    caxis.setVisible(False)
            
            self.update_fit_info()
        
        self.snap_view.addCalibrationWidgets(calibrationChanged)
        self.live_view.addCalibrationWidgets(calibrationChanged)
        
        self.live_view.view.showselected.setChecked(False)

        # Refresh Device List
        self.live_device_refresh.clicked.connect(self.refresh_devicelist)
        self.refresh_devicelist(dialog=False)
        
        # Add Device
        self.live_device_add.clicked.connect(self._live_device_add)

        # Start Button
        self.live_startbutton.setText("Start")
        self.live_startbutton.toggled.connect(self._live_startbutton_toggled)

        # Timed runs
        self.live_timed_runs.toggled.connect(self._live_timed_runs_toggled)
        self.live_timed_runs.setChecked(False)
        self._live_timed_runs_toggled(False)

        # Clear Dummy Snapshots
        for widget in [self.live_dummy1, 
                       self.live_dummy2,
                       self.live_dummy3,
                       self.snap_dummy1,
                       self.snap_dummy2,
                       self.snap_dummy3,
                       self.snap_dummy4]:
                widget.setParent(None)
                sip.delete(widget)

        self.snapshotwidgets = []
        self.redraw_snapshots()
        
        # Clear Button
        self.live_clear.clicked.connect(self.clear_events)
        self.update_live_info()

        # Change device
        self.live_device_selector.currentIndexChanged.connect(self.other_device)
        # No device
        self.device_changed() # Calls update_device_status
        self.update_record_exists()

        # New Snapshot
        self.live_new_snapshot.clicked.connect(self.new_snapshot)
        self.snap_new_snapshot.clicked.connect(self.new_snapshot)

        # Select Snapshot
        self.snap_select_group.buttonClicked.connect(self.change_snapshot)

        # Add Realtime to button group
        self.snap_select_group.addButton(self.snap_realtime)
        self.snap_select_group.setId(self.snap_realtime,-2)

        # Snapshot Data Range changed
        self.snap_view.snap_rangeselect.sigRegionChanged.connect(lambda: self.snap_range_change()) # Lambda to prevent accidentally passing args

        # Snapshot Zoom to Range
        self.snap_range_zoom.clicked.connect(self.snap_range_zoom_apply)

        # Fitting Function changed
        self.snap_fitfunction.currentIndexChanged.connect(self.snap_index_change)

        # Save Snapshot
        self.snap_save.clicked.connect(self.save_snapshot)
        self.snap_save.setEnabled(False)

        # Save & Delete all snapshots
        self.snap_saveall.clicked.connect(self.save_all_snapshots)
        self.snap_deleteall.clicked.connect(self.delete_all_snapshots)

        # Clear Info
        self.update_fit_info()

        # Pregenerate Pixmaps for formula
        fs = self.snap_curr_formula.font().pointSize()*1.2
        color = self.snap_curr_formula.palette().color(QtGui.QPalette.WindowText)
        color = np.array([color.red(), color.green(), color.blue(), color.alpha()])/256
        self.pixmaps_fit = [mathTex_to_QPixmap("$f(x)=\\frac{a}{\\sigma \\sqrt{2\\pi}}\\cdot e^{-\\frac{1}{2} \\left(\\frac{x-\\mu}{\\sigma}\\right)^2}$", fs, color),
                            mathTex_to_QPixmap("$f(x)=\\frac{a}{\\sigma \\sqrt{2\\pi}}\\cdot e^{-\\frac{1}{2} \\left(\\frac{x-\\mu}{\\sigma}\\right)^2}+b$", fs, color),
                            mathTex_to_QPixmap("$f(x)=\\frac{a}{\\sigma \\sqrt{2\\pi}}\\cdot e^{-\\frac{1}{2} \\left(\\frac{x-\\mu}{\\sigma}\\right)^2}+m\cdot x + b$", fs, color)]

        # Init Snap Fit Labels
        self.snap_index_change()

        # Snap: Fitting Worker
        self.worker = FittingWorker(self)
        self.worker.signal_update.connect(self.update_fit_info)
        self.worker.start()

        # Live: Record Log
        self.live_log_checkbox.stateChanged.connect(self.live_log_change)

        self.live_log_save.clicked.connect(self.save_log)

        # Live: Configure device
        self.live_device_configure.clicked.connect(self._live_display_configure)
        
        def row_height(tablewidget, value):
            header = tablewidget.verticalHeader()
            header.setMinimumSectionSize(value)
            header.setDefaultSectionSize(value)
            
        # Snap: Evolution plot
        self.snap_evolution_update()
            
        # QTableView row height(s)
        row_height(self.snap_fit_info, 20)
        row_height(self.shell_log, 20)
        
        self.snap_visible_buttons = []
        
        self.snap_color.currentTextChanged.connect(self.snap_colormap_changed)
        
        for name in self.snap_view.available_colors:
            self.snap_color.addItem(name)
    
    def snap_colormap_changed(self):
        self.update_plot_live_main()
        self.update_plot_snap()
        self.redraw_snapshots()
    
    def snap_evolution_update(self):
        snapshots = self.mgr.get_snapshots()
        self.snap_evolution.update(snapshots=snapshots)

    def update_plot_live_main(self):
        self.live_view.update(self.mgr.get_record_info(), self.mgr.get_visible_snapshots(), self.snap_color.currentText())

    def update_plot_snap(self):
        self.snap_view.update(self.mgr.get_active_snapshot(), self.mgr.get_visible_snapshots(), self.snap_color.currentText())

    def general_update_log(self, plot, xlog, ylog):
        plot.setLogMode(xlog, ylog)
        #plot.setMouseEnabled(x=not xlog, y=not ylog)
        if ylog:
            #plot.setFillLevel(-1)
            plot.getViewBox().setLimits(yMin=-1)
        else:
            plot.getViewBox().setLimits(yMin=0)
        
    def refresh_devicelist(self,value=None,dialog=True):
        """
        Refresh device list, disable current device and update GUI.
        """
        if dialog:
            msgBox = QtWidgets.QMessageBox(self)
        else:
            msgBox = None
        
        def __refresh(self=self):
            # Refresh device list
            self.mgr.refresh_active_devices()
            # Unselect current device
            self.deselect_device()
            # Redraw device list
            self.live_device_selector.clear()
            self.live_device_selector.addItem("")
            for device in self.mgr.get_active_devices():
                self.live_device_selector.addItem("Device: " + device.unique_device_name())
        
        def __refresh_answered(button=None,msgBox=msgBox):
            if msgBox.standardButton(button) != QtWidgets.QMessageBox.Yes:
                return
            
            __refresh()
        
        if dialog:
            msgBox.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setWindowTitle("Warning")
            msg = "Refreshing the device list will unset the current device. Are you sure?"
            msgBox.setText(msg)
            msgBox.setModal(False)
            msgBox.buttonClicked.connect(__refresh_answered)
            msgBox.show()
        else:
            __refresh()
                             
        
    def deselect_device(self):
        """
        Deselect selected device and update GUI.
        """
        self.mgr.selected_device_unselect()
        
    def load_markdown(self, path):
        with open(relative_to_absolute_path(path), 'r') as doc:
            doc_text = doc.read()
            return markdown_to_html(doc_text)
        
    def doc_display(self, path):
        Dialog = QtWidgets.QDialog(self)
        
        #Dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        Dialog.setWindowTitle("Displaying {}".format(path))
        Dialog.resize(800,600)
        
        verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        textBrowser = QtWidgets.QTextBrowser(Dialog)
        textBrowser.setOpenExternalLinks(True)
        verticalLayout.addWidget(textBrowser)
        buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        buttonBox.setOrientation(QtCore.Qt.Horizontal)
        buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Close)
        verticalLayout.addWidget(buttonBox)
        
        buttonBox.accepted.connect(Dialog.accept)
        buttonBox.rejected.connect(Dialog.reject)
        
        html = self.load_markdown(path)
        textBrowser.setHtml(html)
        
        Dialog.show()

        
    def _live_device_add(self):
        self.doc_display(os.path.join("gui","AddDevice.md"))
    
    def _live_timed_runs_toggled(self, on):
        self.live_timing.setVisible(on)
    
    def _live_startbutton_toggled(self):
        # Check if function is for sure not called because of user interaction
        if not self.live_startbutton.isEnabled():
            return

        is_start = self.live_startbutton.isChecked()
        is_timed = self.live_timed_runs.isChecked() # Only relevant if is_start is True

        self.start_stop(is_start, is_timed)

    def start_stop(self, is_start=True, is_timed=False):
        """
        Process device start and stop.
        """
        if is_start:
            if is_timed:
                # Get timing configuration
                timing_context = self.live_timing_context.currentIndex()
                timing_time = self.live_timing_value.value()
                timing_unit = self.live_timing_unit.currentIndex()

                # Start timed run
                success = self.mgr.timed_start_selected_device(timing_time, timing_unit, timing_context)
            else:
                success = self.mgr.untimed_start_selected_device()
        else:
            self.mgr.stop_selected_device()

            # Timed: On completion:
            if is_timed and self.mgr.timing_status() == 1.:
                # Create snapshot
                if self.live_timed_snapshot.isChecked():
                    self.new_snapshot()
                
                # Clear events
                if self.live_timed_clear.isChecked():
                    self.clear_events()
                
                # Repeat
                if self.live_timed_repeat.isChecked():
                    self.live_startbutton.click()
            
        self.update_realtime()

    def update_record_exists(self):
        boolean = self.mgr.record_info is not None

        self.live_new_snapshot.setEnabled(boolean)
        self.snap_new_snapshot.setEnabled(boolean)
        self.snap_realtime.setEnabled(boolean)
        if boolean:
            self.snap_set_enabled(True)
            self.update_plot_snap()
        else:
            self.snap_realtime.setChecked(False)
            if self.mgr.is_active_snapshot_live():
                self.snap_set_enabled(False)
            self.live_clear.setEnabled(False)

        self.update_realtime()

    def snap_set_enabled(self, boolean):
        if boolean:
            self.snap_message.setCurrentIndex(1)
        else:
            self.snap_message.setCurrentIndex(0)
        self.snap_fitfunction.setEnabled(boolean)

    def update_timing(self, timing_status):
        self.live_timing_bar.setValue(int(timing_status*100))

    def update_realtime(self):
        # Redraw info
        self.update_live_info()
        
        # Redraw Data
        self.update_plot_live_main()
        if self.mgr.is_active_snapshot_live():
            self.change_snapshot()

    def update_live_info(self):
        self.live_view.update_info(self.mgr.get_record_info())
            
    def update_snap_info(self):
        self.snap_view.update_info(self.mgr.get_active_snapshot())
    
    def update_device_status(self):
        """
        Updates the GUI regarding device status.

        Including: Start/Stop button label and enabled/disabled settings.
        """
        state = self.mgr.get_selected_device_state()
        recording = DeviceState.started == state
        connected = DeviceState.connected(state)
        if recording:
            title = "Stop"
        else:
            title = "Start"
        self.live_startbutton.setText(title)
        if self.live_startbutton.isChecked() != recording:
            self.live_startbutton.setChecked(recording)
        if not self.live_startbutton.isEnabled():
            self.live_startbutton.setChecked(False)
        self.live_clear.setEnabled(not recording)
        self.live_timing_config.setEnabled(not recording)
        self.live_device_configure.setEnabled(connected and not recording)
        self.live_log_checkbox.setEnabled(connected)

        self.live_timed_runs.setEnabled(not recording)
            
    
    # === DEVICE COMMUNICATION ===
    def device_errored(self):
        """
        Updates GUI according to device error.
        """
        self.update_device_status()

        error_message = self.mgr.pop_error_message()

        reply = QtWidgets.QMessageBox.warning(self, 'Message', 
                            error_message, QtWidgets.QMessageBox.Ok)
        self.refresh_devicelist(dialog=False)
            
    def record_tick(self):
        """
        Process single device record in 150 ms steps. Modal for security reasons.
        Stops device on error.
        """
        # Record data
        running = self.mgr.tick_selected_device()
        
        if not running:
            # If this is executed, timed data aquisition ended.
            self.live_startbutton.setChecked(False) # Also toggles start_stop call

        self.update_timing(self.mgr.timing_current)
        self.update_realtime()
    
    def other_device(self):
        """
        New device selected.
        """
        dev_id = self.live_device_selector.currentIndex()-1
        if dev_id < 0:
            self.deselect_device()
        else:
            self.mgr.change_device_index(self.live_device_selector.currentIndex()-1)

    def new_snapshot(self):
        self.mgr.new_snapshot()
        
    def redraw_snapshots(self):
        # Check Realtime if used
        if self.mgr.is_active_snapshot_live():
            self.snap_realtime.setChecked(True)

        snapshots = self.mgr.get_snapshots()
        active_snapshot = self.mgr.get_active_snapshot()
        
        maxid = len(self.mgr.get_visible_snapshots())
        
        # Remove snapshot widgets
        while len(self.snapshotwidgets) > len(snapshots):
            widgets = self.snapshotwidgets.pop()
            for key, widget in widgets.items():
                if not "top_" in key:
                    # Skipping widgets that are below the main layout
                    continue
                
                widget.setParent(None)
                sip.delete(widget)
        
        
        while len(self.snapshotwidgets) < len(snapshots):
            i = len(self.snapshotwidgets)
            widgets = {}
            
            line = QHLine()
            widgets["top_line_snap"] = line
            self.snap_snapshotlist.layout().addWidget(line)

            if i != 0:
                line = QHLine()
                widgets["top_line_live"] = line
                self.live_snapshotlist.layout().addWidget(line)
            
            # Live
            live_widget = QtWidgets.QWidget()
            widgets["top_live"] = live_widget
            self.live_snapshotlist.layout().addWidget(live_widget)
            live_widget.sizePolicy().setVerticalPolicy(QtWidgets.QSizePolicy.Maximum)

            live_layout = QtWidgets.QHBoxLayout()
            live_layout.setContentsMargins(3, 0, 3, 0)
            live_label = QtWidgets.QLabel()
            live_layout.addWidget(live_label)
            widgets["live_label"] = live_label
            live_widget.setLayout(live_layout)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            live_layout.addItem(spacer)
            live_edit = QtWidgets.QToolButton()
            live_edit.setText("✎")
            def edit(value, self=self, _id=i):
                snapshots = self.mgr.get_snapshots()
                if _id >= len(snapshots):
                    print("Warning: Trying to rename a snapshot that is not available. " +
                        "Id:", _id, "Length of snapshots:", len(snapshots))
                    return
                snapshot = snapshots[_id]
                
                dialog = QtWidgets.QInputDialog(self)
                dialog.setInputMode(QtWidgets.QInputDialog.TextInput)
                dialog.setTextValue(snapshot.get_name())
                def setnredraw(text,set_name=snapshot.set_name,redraw=self.redraw_snapshots):
                    set_name(text)
                    redraw()
                dialog.textValueSelected.connect(setnredraw)
                dialog.show()
            live_edit.clicked.connect(edit)
            live_layout.addWidget(live_edit)
            live_remove = QtWidgets.QToolButton()
            live_remove.setText("✘")
            def remove(value,self=self,_id=i):
                self.mgr.remove_snapshot_by_id(_id)
            live_remove.clicked.connect(remove)
            live_layout.addWidget(live_remove)
            
            # Snapshot
            snap_widget = QtWidgets.QWidget()
            widgets["top_snap"] = snap_widget
            self.snap_snapshotlist.layout().addWidget(snap_widget)
            snap_widget.sizePolicy().setVerticalPolicy(QtWidgets.QSizePolicy.Maximum)

            snap_layout = QtWidgets.QHBoxLayout()
            snap_layout.setContentsMargins(3, 0, 3, 0)
            
            snap_show = QtWidgets.QToolButton()
            snap_show.setMaximumSize(30, 16777215)
            snap_show.setMinimumSize(30, 0)
            snap_show.setAutoRaise(True)
            
            def show(value,self=self,_id=i):
                self.mgr.toggle_visibility_snapshot_by_id(_id)
            snap_show.clicked.connect(show)
            snap_layout.addWidget(snap_show)
            widgets["snap_show"] = snap_show
            
            snap_select = QtWidgets.QRadioButton()
            self.snap_select_group.addButton(snap_select)
            self.snap_select_group.setId(snap_select,i)
            snap_layout.addWidget(snap_select)
            widgets["snap_select"] = snap_select
            snap_widget.setLayout(snap_layout)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            snap_layout.addItem(spacer)
            snap_edit = QtWidgets.QToolButton()
            snap_edit.setText("✎")
            snap_edit.clicked.connect(edit)
            snap_layout.addWidget(snap_edit)
            snap_remove = QtWidgets.QToolButton()
            snap_remove.setText("✘")
            snap_remove.clicked.connect(remove)
            snap_layout.addWidget(snap_remove)
        
            self.snapshotwidgets.append(widgets)

        for i, (widgets, snapshot) in enumerate(zip(self.snapshotwidgets, snapshots)):
            name = snapshot.get_name()
            if snapshot == active_snapshot:
                widgets["snap_select"].setChecked(True)
            
            visibility_index = self.mgr.get_visibility_snapshot(snapshot)
            if visibility_index is False:
                widgets["snap_show"].setText("+")
                widgets["snap_show"].setStyleSheet("")
            else:
                widgets["snap_show"].setText(f"{visibility_index}.")
                color = ", ".join([str(x) for x in np.array(self.snap_view.get_color_by_id(visibility_index, maxid, False))*255])
                widgets["snap_show"].setStyleSheet(f"color:rgb({color}); font-weight: bold;")

            widgets["live_label"].setText(name)
            widgets["snap_select"].setText(name)
        self.snap_saveall.setEnabled(len(snapshots) > 0)
        self.snap_deleteall.setEnabled(len(snapshots) > 0)
    
    def closeEvent(self, event):

        quit_msg = "All unsaved snapshots will be deleted. Continue?"
        reply = QtWidgets.QMessageBox.question(self, 'Message', 
                         quit_msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.record_timer.stop()
            self.mgr.selected_device_unselect()
            self.mgr.quit_active_devices()
            self.worker.quit()
            self.worker.wait()
            event.accept()
        else:
            event.ignore()

    def change_snapshot(self):
        _id = self.snap_select_group.checkedId()
        self.mgr.set_active_snapshot_id(_id)
        self.snap_save.setEnabled(_id != -2)
        self.update_plot_snap()
        
        active_snapshot = self.mgr.get_active_snapshot()
        if active_snapshot is not None:
            self.snap_set_enabled(True)
        else:
            self.snap_set_enabled(False)
        self.update_snap_info()

        # Fitting
        self.snap_range_change(True)
            

    def update_fit_info(self):
        # Update GUI

        self.snap_fit_info.clearContents()
        
        fit_info = self.mgr.get_fit_info()
        active_snapshot = self.mgr.get_active_snapshot()

        self.snap_view.update_fit_info(fit_info, active_snapshot)
        
        parameters = {"Fit":("disabled", "")}

        calibration_active = self.snap_view.caxis.isVisible()

        if fit_info != None:
            if not calibration_active:
                parameters = fit_info.get_parameters()
            else:
                parameters = fit_info.get_parameters(self.snap_view.caxis)
        
        self.snap_fit_info.setRowCount(len(parameters))
        if calibration_active:
            self.snap_fit_info.setColumnCount(2)
            item = QtWidgets.QTableWidgetItem()
            item.setText("Cal. Results")
            self.snap_fit_info.setHorizontalHeaderItem(1, item)
        else:
            self.snap_fit_info.setColumnCount(1)

        for i, (key, value) in enumerate(parameters.items()):
            # Row label
            item = QtWidgets.QTableWidgetItem()
            item.setText(key)
            self.snap_fit_info.setVerticalHeaderItem(i, item)

            # Result columns
            for j in range(int(calibration_active)+1):
                item = QtWidgets.QTableWidgetItem()
                item.setText(value[j])
                self.snap_fit_info.setItem(i, j, item)


    def snapshot_fitting(self):
        if self.snap_fitfunction.currentIndex() > 0:
            # Error "QThread: Destroyed while thread is still running" may occur if previous worker was not finished at this point
            # If that happens, some thread interruption could be implemented
            self.mgr.set_last_region(self.get_snap_region())
            self.mgr.create_fit_info(self.snap_fitfunction.currentIndex(), self.mgr.get_last_region(), self.mgr.get_active_snapshot(), self.snap_fitcounts.value())
            self.worker.fit_info = self.mgr.get_fit_info()
        else:
            self.mgr.unset_fit_info()
            self.update_fit_info()
            self.snap_view.clear_fit_info()

    def get_snap_region(self):
        region = self.snap_view.snap_rangeselect.getRegion()
        return [int(region[0]-0.5),int(region[1]-0.5)]
    
    def snap_range_change(self, force_fitting = False):
        if self.mgr.get_active_snapshot() is None:
            return False
        region = self.get_snap_region()
        count = int(np.sum(self.mgr.get_active_snapshot().events[region[0]:region[1]]))
        self.snap_counts.setText("Counts between cursors: " + str(count))

        last_region = self.mgr.get_last_region()

        if not force_fitting: # Always fit if force_fitting
            if last_region == None: # Always fit if last_region == None
                if np.all(np.array(last_region)!=np.array(region)): # Fit if last_region != region
                    return

        self.snapshot_fitting()
    
    def snap_range_zoom_apply(self):
        region = self.get_snap_region()
        self.snap_view.applyXRegion(region)

    def save_snapshot(self):
        """
        Wrapper for GUI: Save dialog for snapshots.
        """
        snapshot_save_dialog(self.mgr.get_active_snapshot())
    
    def save_all_snapshots(self):
        """
        Wrapper for GUI: Save dialog for all snapshots.
        """
        snapshots_save_dialog(self.mgr.get_snapshots())
    
    def delete_all_snapshots(self):
        msgBox = QtWidgets.QMessageBox(self)
        
        def __delete_all_snapshots(button,self=self, msgBox=msgBox):
            if msgBox.standardButton(button) != QtWidgets.QMessageBox.Yes:
                return

            self.mgr.remove_all_snapshots()
        
        msgBox.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msgBox.setWindowTitle("Warning")
        msg = "You are about to remove all snapshots. If you did not save them, they will be lost. Are you sure?"
        msgBox.setText(msg)
        msgBox.setModal(False)
        msgBox.buttonClicked.connect(__delete_all_snapshots)
        msgBox.show()

    def snap_index_change(self):
        self.snap_range_change(True)
        curr = self.snap_fitfunction.currentIndex()
        self.snap_curr_formula.clear()
        if curr == 1:
            self.snap_curr_formula.setPixmap(self.pixmaps_fit[0])
        if curr == 2:
            self.snap_curr_formula.setPixmap(self.pixmaps_fit[1])
        if curr == 3:
            self.snap_curr_formula.setPixmap(self.pixmaps_fit[2])

    def live_log_change(self):
        log_requested = self.live_log_checkbox.isChecked()
        logging = self.mgr.set_log_selected_device(log_requested)
        self.live_log_save.setEnabled(logging)


    def save_log(self):
        log = self.mgr.get_log_selected_device()
        dlg = QtWidgets.QFileDialog(self)
        dlg.setWindowTitle('Save Log')
        dlg.setViewMode(QtWidgets.QFileDialog.Detail)
        dlg.setNameFilters( [self.tr('TXT file (*.txt)'), self.tr('All Files (*)')] )
        dlg.setDefaultSuffix( '.txt' )
        dlg.setFileMode(QtWidgets.QFileDialog.AnyFile);
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.show()
        
        def savefile(self):
            filename = dlg.selectedFiles()[0]
            f = open(filename, "w")
            f.write(log)
            f.close()
        dlg.fileSelected.connect(savefile)

    def _live_display_configure(self):
        DeviceConfig(self.mgr.get_selected_device_properties()).exec_()
        self.update_live_info()
        
    def clear_events(self):
        self.mgr.clear_events()
    
    def device_changed(self):
        if self.mgr.selected_device is not None:
            # New device
            if self.mgr.selected_device.internal_memory:
                msg = "The selected device has internal memory. If live data existed, it is saved in a new snapshot."
                reply = QtWidgets.QMessageBox.information(self, 'Message', msg, QtWidgets.QMessageBox.Ok)
            descr = self.mgr.get_selected_device_description()
            self.live_firmware.setText(descr)
            self.live_startbutton.setEnabled(True)
        else:
            # Freshly disconnected device
            self.live_firmware.setText("No device selected")
            self.live_startbutton.setEnabled(False)

        self.update_device_status()
        self.update_realtime()
        
if __name__ == "__main__":
    main()
