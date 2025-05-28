import sys, os
from PyQt5 import QtCore, QtWidgets, QtGui, uic
import pyqtgraph as pg
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

from .custom_axes import CalibratedAxis
from .RegionIndicatorWidget import RegionIndicatorWidget
from .CalibrationWidget import CalibrationDialog, CalibrationWidget
from .ErrorLineItem import ErrorLineItem

def log_or_value(islog, value):
    if islog:
        if value > 1:
            return np.log10(value+0.5)
        else:
            return 0.5
    else:
        return value

class DropInGrid(pg.GraphicsWidget):
    def __init__(self, parent):
        pg.GraphicsWidget.__init__(self, parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        self.layout = QtWidgets.QGraphicsGridLayout()
        self.layout.setContentsMargins(1,1,1,1)
        self.setLayout(self.layout)
        self.layout.setHorizontalSpacing(0)
        self.layout.setVerticalSpacing(0)

class PlotLine:
    def __init__(self, plot, _id, fill_to_zero, current_color=None):
        self.is_active = _id == 0

        self.plot_data = plot.plot([0,1],[0],stepMode=True, skipFiniteCheck=True)
        self.plot_data.setZValue(300000-_id)
        
        zero_arr = np.zeros(3)
        self.plot_error = ErrorLineItem(x=zero_arr,y=zero_arr,top=zero_arr,bottom=zero_arr,beam=1, skipFiniteCheck=True)
        plot.addItem(self.plot_error)
        self.plot_error.hide()
        self.plot_error.setZValue(200000-_id)
        
        self.show_uncertainty = False
        self.visible = True
        
        if fill_to_zero:
            ## Fill area between 0 and data
            self.xaxisline = plot.plot([0,1],[0.0000001],stepMode=True)
            self.xaxisline.hide()
            self.fill_between_data = pg.FillBetweenItem(self.plot_data, self.xaxisline)
            plot.addItem(self.fill_between_data)
            self.fill_between_data.setZValue(100000-_id)
        else:
            self.fill_between_data = None
            self.xaxisline = None
        
        self.update_colors(current_color=current_color)
    
    def update_colors(self, current_color=None, transparency=0):
        if current_color is None:
            current_color = (0,0,0)
        
        self.current_color = current_color
        
        opacity = 1-transparency
        color_line = np.array(self.current_color+(opacity,))*255
        color_error = np.array(self.current_color+(0.7*opacity,))*255
        color_filled = np.array(self.current_color+(0.1,))*255
        
        self.plot_data.setPen(pg.mkPen(color_line, width=2))
        self.plot_error.setData(pen=pg.mkPen(color_error, width=2, style=QtCore.Qt.DashLine))
        
        if self.fill_between_data:
            self.fill_between_data.setBrush(color_filled)
            
        self.set_visible(self.visible) # Avoid resetting visibility
            
    
    def update(self, record_info, timing_context, show_uncertainty):
        if record_info is not None:
            edges = record_info.edges
            events = record_info.events
            
            # TODO +0.00001 because of PyQtGraph log bug
            
            # Set visibility of plot elements
            any_events = np.any(events)
            self.plot_data.setVisible(any_events) # show if any event can be displayed
            if self.fill_between_data:
                self.fill_between_data.setVisible(any_events)
            
            norm = 1
            
            if timing_context == 1:
                # device runtime
               norm = record_info.realtime
                
            elif timing_context == 2:
                # PC runtime
               norm = record_info.get_realtime_pc()
                
            elif timing_context == 3:
                # device_livetime
               norm = record_info.livetime
                
            
            error_mask = events > 10
            error_events = np.array(events)
            error_events[~error_mask] = np.nan
            errors = np.sqrt(error_events)
            
            data_available = norm != 0
            
        else:
            data_available = False
        
        if data_available:
            self.plot_data.setData(edges, (events+0.00001)/norm)
            if self.xaxisline:
                self.xaxisline.setData(edges, np.zeros(len(events))+0.00001)
            self.plot_error.setData(x=(edges[:-1] + edges[1:])/2, y=error_events/norm, top=errors/norm, bottom=errors/norm)
        else:
            # Set visibility of plot elements
            self.plot_data.hide()
            
            if self.fill_between_data:
                self.fill_between_data.hide()
            
            self.plot_data.setData([0,1],[1])
            if self.xaxisline:
                self.xaxisline.setData([0,1],[0])
            
            zero_arr = np.zeros(3)
            self.plot_error.setData(x=zero_arr,y=zero_arr,top=zero_arr,bottom=zero_arr)
            
        self.set_uncertainty_visible(show_uncertainty)
    
    def trigger_change(self):
        # Workaround for pyqtgraph bug
        if self.fill_between_data:
            self.fill_between_data.curveChanged()
    
    def set_uncertainty_visible(self, show_uncertainty):
        self.show_uncertainty = show_uncertainty
        self.plot_error.setVisible(self.show_uncertainty and self.visible)
        
    def remove(self, plot):
        plot.removeItem(self.plot_data)
        del self.plot_data
        
        plot.removeItem(self.plot_error)
        del self.plot_error
        
        if self.fill_between_data:
            plot.removeItem(self.fill_between_data)
            del self.fill_between_data
        
        if self.xaxisline:
            plot.removeItem(self.xaxisline)
            del self.xaxisline
    
    def set_visible(self, visible):
        self.visible = visible
        
        self.plot_data.setVisible(visible)
        self.plot_error.setVisible(visible and self.show_uncertainty)
        
        if self.fill_between_data:
            self.fill_between_data.setVisible(visible)

class SnapshotViewWidget(QtWidgets.QMdiArea):
    
    available_colors = ['matplotlib cycle', 'gray', 'Greys_r', 'viridis', 'twilight', 'plasma', 'inferno', 'magma', 'cividis']
    
    def __init__(self, *args):
        QtWidgets.QMdiArea.__init__(self)
        self.view = QtWidgets.QWidget(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'snapshot_view.ui'), self.view)
        self.setViewport(self.view)
        self.subwindow = QtWidgets.QMdiSubWindow(self)
        self.info = QtWidgets.QWidget(self)
        self.subwindow.setWidget(self.info)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'snapshot_info.ui'), self.info)
        self.addSubWindow(self.subwindow)
        self.subwindow.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowShadeButtonHint | QtCore.Qt.WindowTitleHint)
        self.subwindow.setWindowTitle("Info")
        self.subwindow.move(60,20)
        
        self.record_info = None
        self.additional_snapshots = []
        self.colormap = self.available_colors[0]

        # Initialize info
        # Fix row height
        header = self.info.table.verticalHeader()
        header.setMinimumSectionSize(20)
        header.setDefaultSectionSize(20)

        # Initialize plot
        self.main_plot = PlotLine(self.view.plot, 0, True, self.get_color_by_id(0, 1, True))
        
        self.plot_scatter = self.view.plot.plot([],[], pen=None, symbol='x')
        self.plot_fit  = self.view.plot.plot([],[], pen=pg.mkPen((240, 170, 100, 255),width=2),antialias=True)
        self.plot_fit.setZValue(500000)

        self.view.plot.getViewBox().setLimits(yMin=0, xMin=-1)
        
        self.view.plot.getPlotItem().setMenuEnabled(enableMenu=False, enableViewBoxMenu=True)
        
        # Add energy calibration CalibratedAxis
        CalibrationDialog.instance = CalibrationDialog(parent=self)

        self.caxis = CalibratedAxis(originalAxis=self.view.plot.getAxis("bottom"), orientation='top')
        self.caxis.setLabel('Calibrated axis')
        self.view.plot.setAxisItems({"top":self.caxis})
        self.view.plot.showGrid(True, True)
        self.caxis.hide()

        # Prevent plots from jumping after setting first log scale
        self.view.plot.setLogMode(True, True)
        QtCore.QTimer.singleShot(100, self.noLog)

        # Interactive
        self.view.ylog.stateChanged.connect(self.update_log)
        self.view.xlog.stateChanged.connect(self.update_log)
        self.view.viewall.clicked.connect(self.view.plot.enableAutoRange)
        
        self.view.showuncertainty.stateChanged.connect(self.update_uncertainty)
        
        self.region = None # Stores Linear Region Item
        self.snap_rangeselect = None
        
        self.xMin = -1
        self.xMax = -1
        
        self.dropInGrid = DropInGrid(self.view.plot.plotItem)
        self.view.plot.plotItem.layout.removeItem(self.view.plot.plotItem.titleLabel)
        self.view.plot.plotItem.layout.addItem(self.dropInGrid, 0, 1)
        
        self.view.displaytype.currentIndexChanged.connect(self.drawUpdate)
        self.view.showselected.stateChanged.connect(self.drawUpdate)
        self.view.selectedtransparency.valueChanged.connect(self.drawUpdate)
        
        self.plot_pool = []
        
    def get_color_by_id(self, _id, maxid, is_active=False):
        if self.colormap == self.available_colors[0]:
            current_color = to_rgb(f"C{_id}")
        else:
            _maxid = np.maximum(float(maxid), 5.)
            current_color = plt.get_cmap(self.colormap)(_id/_maxid)[:3]

        is_active = _id == 0
        if is_active:
            current_color = tuple(np.minimum(np.array(current_color)*1.2,[1]*3))
            
        return current_color
        
    def addLinearRegion(self):
        # Add region selector
        self.snap_rangeselect = pg.LinearRegionItem(
            bounds=[0,101], 
            brush=(0,0,0,0), 
            hoverBrush=np.array(to_rgb("C0")+(0.2,))*256, 
            pen=np.array(to_rgb("C0"))*200,
            hoverPen=np.array(to_rgb("C0"))*256,
            movable=True)
        self.snap_rangeselect.setBounds([0.5, self.xMax])
        self.snap_rangeselect.setRegion([1, self.xMax])

        ## Make Range Selector stepwise
        class StepwiseInfiniteLine(pg.graphicsItems.InfiniteLine.InfiniteLine):
            _p = [0,0]
            @property
            def p(self):
                return self._p

            @p.setter
            def p(self, pos):
                x = round(pos[0]+0.5)-0.5
                y = pos[1]
                self._p = [x,y]

        self.snap_rangeselect.lines[0].__class__ = StepwiseInfiniteLine
        self.snap_rangeselect.lines[1].__class__ = StepwiseInfiniteLine
        self.snap_rangeselect.setRegion([1.5, 100.5])

        ## Add Range Selector to Plot
        self.view.plot.addItem(self.snap_rangeselect)
        
        self.region_indicator = RegionIndicatorWidget(self.view.plot.plotItem.vb, self.snap_rangeselect, np.array(to_rgb("C0"))*256)
        self.dropInGrid.layout.addItem(self.region_indicator, 2, 1)
    
    def addCalibrationWidgets(self, callback):
        self.calibrationWidget = CalibrationWidget(parent=self.view.plot.plotItem, vb=self.view.plot.plotItem.getViewBox())
        
        self.calibrationWidget.sigCalibrationChanged.connect(callback)
        self.dropInGrid.layout.addItem(self.calibrationWidget, 0, 1)
    
    def noLog(self):
        # Prevent plots from jumping after setting first log scale
        self.view.plot.setLogMode(False, False)

    def update_log(self, int):
        xlog = self.view.xlog.isChecked()
        ylog = self.view.ylog.isChecked()
        self.view.plot.setLogMode(xlog, ylog)
        self.main_plot.trigger_change()
        
        for plot in self.plot_pool:
            plot.trigger_change()
        
        if ylog:
            self.view.plot.getViewBox().setLimits(yMin=-1)
        else:
            self.view.plot.getViewBox().setLimits(yMin=0)

    def update_info(self, record_info):
        if record_info is None:
            for i in range(0,13):
                self.info.table.setItem(i,0,QtWidgets.QTableWidgetItem(""))
            return
        self.info.table.setItem(0,0,QtWidgets.QTableWidgetItem(record_info.get_first_start_time()))
        self.info.table.setItem(1,0,QtWidgets.QTableWidgetItem(record_info.get_start_time()))
        self.info.table.setItem(2,0,QtWidgets.QTableWidgetItem(record_info.get_stop_time()))
        self.info.table.setItem(3,0,QtWidgets.QTableWidgetItem(str(record_info.get_realtime_pc())))
        self.info.table.setItem(4,0,QtWidgets.QTableWidgetItem(str(record_info.realtime)))
        self.info.table.setItem(5,0,QtWidgets.QTableWidgetItem(str(record_info.livetime)))
        eventcount = record_info.eventcount()
        evtperlivetime = "inf"
        if record_info.livetime > 0:
            evtperlivetime = round(eventcount/record_info.livetime*100)/100
        evtperrealtime = "inf"
        deadtime = "inf"
        if record_info.realtime > 0:
            evtperrealtime = round(eventcount/record_info.realtime*100/100, 2)
            deadtime = round((record_info.realtime - record_info.livetime)/record_info.realtime*100, 2)
        self.info.table.setItem(6,0,QtWidgets.QTableWidgetItem(str(deadtime) + " %"))
        self.info.table.setItem(7,0,QtWidgets.QTableWidgetItem(str(eventcount)))
        self.info.table.setItem(8,0,QtWidgets.QTableWidgetItem(str(evtperrealtime)+" 1/s"))
        self.info.table.setItem(9,0,QtWidgets.QTableWidgetItem(str(evtperlivetime)+" 1/s"))
        self.info.table.setItem(10,0,QtWidgets.QTableWidgetItem(record_info.unique_device_name()))
        self.info.table.setItem(11,0,QtWidgets.QTableWidgetItem(record_info.properties_str()))
    
    def drawUpdate(self):
        record_info = self.record_info
        
        xlog_checked = self.view.xlog.isChecked()

        if record_info is None:
            xMin = log_or_value(xlog_checked,-1)
            xMax = log_or_value(xlog_checked,101)
        else:
            xMin = log_or_value(xlog_checked, -1)
            xMax = log_or_value(xlog_checked, record_info.channel_count)
                
        _vb = self.view.plot.getViewBox()
        if not self.xMin == xMin or not self.xMax == xMax:
            _vb.setLimits(xMin=xMin, xMax=xMax)
            #_vb.setRange(xRange=(xMin, xMax))  # TODO This could also be done once per device resolution change
            if self.snap_rangeselect is not None:
                self.snap_rangeselect.setBounds([0.5, xMax-1])
                self.snap_rangeselect.setRegion([1, xMax-1])
            self.xMin = xMin
            self.xMax = xMax
        self.main_plot.update(record_info, self.view.displaytype.currentIndex(), self.view.showuncertainty.isChecked())
        
        while len(self.plot_pool) < len(self.additional_snapshots):
            _id = len(self.plot_pool) + 1
            self.plot_pool.append(PlotLine(self.view.plot, _id, False))
        
        while len(self.plot_pool) > len(self.additional_snapshots):
            self.plot_pool.pop().remove(self.view.plot)
        
        maxid = len(self.additional_snapshots)
        for i, (plot, snapshot) in enumerate(zip(self.plot_pool, self.additional_snapshots)):
            plot.update(snapshot, self.view.displaytype.currentIndex(), self.view.showuncertainty.isChecked())
            plot.set_visible(self.view.showselected.isChecked())
            plot.update_colors(self.get_color_by_id(i+1, maxid, False), self.view.selectedtransparency.value()/100.)
    
    def update(self, record_info, additional_snapshots=None, colormap=None):
        if additional_snapshots is None:
            additional_snapshots = []
        
        if colormap is None:
            colormap = self.available_colors[0]
        
        self.record_info = record_info
        self.additional_snapshots = additional_snapshots
        self.colormap = colormap
        self.drawUpdate()

    def update_fit_info(self, fit_info, active_snapshot):
        
        # Update GUI
        if fit_info is not None and fit_info.popt is not None:
            centers = active_snapshot.centers[fit_info.fit_range[0]:fit_info.fit_range[1]]
            values = active_snapshot.events[fit_info.fit_range[0]:fit_info.fit_range[1]]+0.00001
            mask = values >= fit_info.cutoff
            self.plot_scatter.setData(centers[mask], values[mask])
            self.plot_fit.setData(*fit_info.plot())
            
            self.calibrationWidget.item.updateFittedTick(True, pos=fit_info.popt[1])
        else:            
            self.plot_fit.setData([],[])
            self.plot_scatter.setData([],[])
    
    def update_uncertainty(self, int):
        show_uncertainty = self.view.showuncertainty.isChecked()
        self.main_plot.set_uncertainty_visible(show_uncertainty)
        
        for plot in self.plot_pool:
            plot.set_uncertainty_visible(show_uncertainty)

    def clear_fit_info(self):
        self.plot_fit.setData([],[])
    
    def applyXRegion(self, region):
        self.view.plot.setXRange(*region)
    

# Test on run
if __name__ == "__main__":
    app = QtWidgets.QApplication(["test"])
    w = QtWidgets.QMainWindow()
    widget = SnapshotViewWidget()
    w.setCentralWidget(widget)
    w.show()
    sys.exit(app.exec_())
