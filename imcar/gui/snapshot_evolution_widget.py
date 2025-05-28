import sys, os
from PyQt5 import QtCore, QtWidgets, QtGui, uic
import pyqtgraph as pg
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

from imcar.gui.helper import cmapToColormap
from .ColorbarWidget import ColorbarWidget

class SnapshotEvolutionWidget(QtWidgets.QWidget):
    def __init__(self, *args):
        QtWidgets.QWidget.__init__(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'snapshot_evolution.ui'), self)
    
        # Setup plots
        ## Colorbar
        self.colorbar = ColorbarWidget()
        self.colorbarholder.setCentralItem(self.colorbar)
        ## Grids
        self.main_plot.showGrid(True, True)
        self.plot_time.showGrid(True, True)
        self.plot_channel.showGrid(True, True)
        
        ## Axis links
        self.main_plot.setXLink(self.plot_time) 
        self.main_plot.setYLink(self.plot_channel) 

        ## DateAxisItems
        self.main_plot.setAxisItems({'bottom': pg.DateAxisItem()})
        self.plot_time.setAxisItems({'bottom': pg.DateAxisItem()})
        
        ## Axis direction
        self.plot_channel.getViewBox().invertX(True)
        
        ## Axis labels
        self.colorbar.axis.setLabel("Rate", units="cps")

        self.main_plot.setLabel("bottom", "Date time")
        self.main_plot.setLabel("left", "Channel")
        
        self.plot_time.setLabel("bottom", "Date time")
        self.plot_time.setLabel("left", "Rate", units="cps")
        
        self.plot_channel.setLabel("bottom", "Rate", units="cps")
        self.plot_channel.setLabel("left", "Channel")
        
        ## Ranges
        self.main_plot.setLimits(yMin=0)
        self.plot_time.setLimits(yMin=0)
        self.plot_channel.setLimits(xMin=0, yMin=0)
        
        ## Markers
        self.tickslider = CustomTickSliderItem(allowAdd=False, allowRemove=False)
        self.main_plot.plotItem.vb.sigXRangeChanged.connect(self.tickslider.updateRange)
        self.main_plot.plotItem.layout.addItem(self.tickslider, 4, 1)
        
        ### Second slider for equal padding
        self.paddingslider = CustomTickSliderItem(allowAdd=False, allowRemove=False)
        self.plot_channel.plotItem.layout.addItem(self.paddingslider, 4, 1)
        
        ## Context menus
        self.main_plot.getPlotItem().setMenuEnabled(enableMenu=False, enableViewBoxMenu=True)
        self.plot_time.getPlotItem().setMenuEnabled(enableMenu=False, enableViewBoxMenu=True)
        self.plot_channel.getPlotItem().setMenuEnabled(enableMenu=False, enableViewBoxMenu=True)
        
        # Storage for plot objects
        ## Main plot
        self.main_plot_overlays = {}
        self.plot_time_lines = {}
        self.snapshot_views = {}
        
        ## Time plot
        self.time_dotted_item = pg.PlotCurveItem(pen = pg.mkPen(color=(255, 255, 255))) # TODO , style=QtCore.Qt.DotLine))
        self.plot_time.addItem(self.time_dotted_item)
        
        self.time_dotted_grayed_out_item = pg.PlotCurveItem(pen = pg.mkPen(color=(77, 77, 77))) # TODO, style=QtCore.Qt.DotLine))
        self.plot_time.addItem(self.time_dotted_grayed_out_item)
        
        ## Channel plot
        self.channel_dotted_item = pg.PlotCurveItem([], pen = pg.mkPen(color=(255, 255, 255))) # TODO, style=QtCore.Qt.DotLine))
        self.plot_channel.addItem(self.channel_dotted_item)
        
        # TODO
        """
        # Range selection
        self.channel_rangeselect = pg.LinearRegionItem(orientation='horizontal', movable=True)

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

        self.channel_rangeselect.lines[0].__class__ = StepwiseInfiniteLine
        self.channel_rangeselect.lines[1].__class__ = StepwiseInfiniteLine
        self.channel_rangeselect.setBounds([0,1])
        self.channel_rangeselect_bounds = [0,1]

        ## Add Range Selector to Plot
        self.plot_channel.addItem(self.channel_rangeselect)
        """
        
        
        self.colormap.currentTextChanged.connect(self.setColormap)
        
        colormaps = ['gray', 'Greys_r', 'viridis', 'twilight', 'plasma', 'inferno', 'magma', 'cividis']
        for name in colormaps:
            self.colormap.addItem(name)
        
        self.pglut = None
        self.colormap.setCurrentIndex(2) # Use viridis colormap as default

        def levelsChanged():
            for img in self.snapshot_views.values():
                img.setLevels(self.colorbar.getLevels())
                
        self.max_rate = 0.000001

        def disableAutoscale():
            self.cb_autoscale.setChecked(False)
        
        def autoscaleChanged(state):
            if self.cb_autoscale.isChecked():
                self.colorbar.setLevels(0, self.max_rate)
                self.colorbar.setRange(xRange=(0, self.max_rate))

        self.colorbar.sigChanged.connect(levelsChanged)
        self.colorbar.sigUserChanged.connect(disableAutoscale)
        self.cb_autoscale.stateChanged.connect(autoscaleChanged)
        
        self.time_type.currentIndexChanged.connect(self._time_type__currentIndexChanged)

        self.reference_snapshot = None
        self.snapshots = []
        
        # Splitters
        self.splitter_v1.splitterMoved.connect(self.splitter_v1_moved)
        self.splitter_v2.splitterMoved.connect(self.splitter_v2_moved)
        
        self._postinit_performed = False
        
        self.plots.showEvent = self.postinit
        
        self.cb_autoscale_label.mouseReleaseEvent = lambda ev: self.cb_autoscale.nextCheckState()
        
    
    def postinit(self, plots):
        """
        Post-init code to execute when widget is shown
        """
        if self._postinit_performed:
            return
        
        height = sum(self.splitter_v1.sizes())
        
        height_factor = 0.3
        self.splitter_v1.setSizes([int(height*height_factor), int(height*(1-height_factor))])
        self.splitter_v2.setSizes([int(height*height_factor), int(height*(1-height_factor))])
        

        width = sum(self.splitter_h.sizes())

        width_factor = 0.3
        self.splitter_h.setSizes([int(width*width_factor), int(width*(1-width_factor))])
        
        self._postinit_performed = True
    
    def splitter_v1_moved(self, a, b):
        self.splitter_v2.setSizes(self.splitter_v1.sizes())
    
    def splitter_v2_moved(self, a, b):
        self.splitter_v1.setSizes(self.splitter_v2.sizes())

    def _time_type__currentIndexChanged(self, index):
        self.update()
        
    def setColormap(self, name):
        try:
            cmap = plt.get_cmap(name)

            pos, rgba_colors = zip(*cmapToColormap(cmap))
            colormap = pg.ColorMap(pos, rgba_colors)
            
            self.pglut = colormap.getLookupTable()
            
            for img in self.snapshot_views.values():
                img.setLookupTable(self.pglut)
            
            self.colorbar.setCmap(cmap)
        except ValueError:
            pass
    
    def update(self, snapshots=None):
        """
        Update snapshot evolution plot
        """
        
        # Initialization
        time_type = self.time_type.currentIndex()
        
        if snapshots is not None:
            if len(snapshots) < 2:
                self.snap_evolution_message.setCurrentIndex(0)
                return
            
            self.snap_evolution_message.setCurrentIndex(1)
            
            self.snapshots = snapshots.copy()
        
        # ---
        
        # Update list of snapshots
        ## Snapshots to remove and add
        removed_snapshots = [x for x in self.snapshot_views if x not in self.snapshots[1:]]
        new_snapshots = [x for x in self.snapshots[1:] if x not in self.snapshot_views]
        
        ## Remove old snapshots
        for snapshot in removed_snapshots:
            img = self.snapshot_views[snapshot]
            
            self.main_plot.removeItem(img)
            
            del self.snapshot_views[snapshot]
        
        ## Add new snapshots
        for snapshot in new_snapshots:
            img = pg.ImageItem()
            img.setLookupTable(self.pglut)
            img.setLevels(self.colorbar.getLevels())
            self.main_plot.addItem(img)
            self.snapshot_views[snapshot] = img
        
        # ---
        
        # Update all snapshots
        ## (for the remaining snapshots, this is especially important if snapshots before are removed)
        used_overlays = []
        used_lines = []
        _to = 0
        
        x_time_plot_dotted_pairs = []
        y_time_plot_dotted_pairs = []
        
        x_time_plot_dotted_pairs_greyed_out = []
        y_time_plot_dotted_pairs_greyed_out = []
        
        sum_total_time = 0
        sum_data = np.array([], dtype=int)
        
        previous_to = None
        
        ticks = []
        
        self.max_rate = 0.000001
        for i, snapshot in enumerate(self.snapshots):
            if i == 0:
                continue
            
            # Get data
            _to = snapshot.stop_times[-1]
            _from = snapshot.start_times[0]
            
            # Check if snapshot inherits data from previous snapshot
            if i > 0 and _from == self.snapshots[i-1].start_times[0]:
                last_snapshot = self.snapshots[i-1]
                
                _from = last_snapshot.stop_times[-1]
                data = snapshot.events - last_snapshot.events

                if time_type == 0: # Device livetime
                    total_time = snapshot.livetime - last_snapshot.livetime
                elif time_type == 1: # Device runtime
                    total_time = snapshot.realtime - last_snapshot.realtime
                elif time_type == 2: # PC runtime
                    total_time = _to - _from
                
                _type = 0
                
            else:
                data = snapshot.events
                if time_type == 0: # Device livetime
                    total_time = snapshot.livetime
                elif time_type == 1: # Device runtime
                    total_time = snapshot.realtime
                elif time_type == 2: # PC runtime
                    total_time = _to - _from
                
                _type = 1
                
                if previous_to is not None:
                    ticks.append((_to, (99, 99, 99)))
                    
                    previous_to = None
            
            if total_time > 0:
                rates = data/total_time
                
                if len(data) == len(sum_data):
                    sum_data += data
                elif len(data) > len(sum_data):
                    new_sum = data.copy()
                    new_sum[:len(sum_data)] += sum_data
                    sum_data = new_sum
                else:
                    sum_data[:len(data)] += data
                
                sum_total_time += total_time
                
                curr_max = np.max(rates)
                if self.max_rate < curr_max:
                    self.max_rate = curr_max
                
                img = self.snapshot_views[snapshot]
                # Plot data: Main plot
                img.setImage(np.array([rates]), autoLevels=False)
                img.setRect(_from, 0, _to-_from, len(rates))
                
                rate_total = sum(rates)
                x_time_plot_dotted_pairs.append(_from)
                y_time_plot_dotted_pairs.append(rate_total)
                
                for stop_from, stop_to in zip(snapshot.stop_times, snapshot.start_times[1:]):
                    if stop_to <= _from:
                        continue # Out of reach
                    
                    x_time_plot_dotted_pairs.append(stop_from)
                    y_time_plot_dotted_pairs.append(rate_total)
                    
                    x_time_plot_dotted_pairs_greyed_out.append(stop_from)
                    y_time_plot_dotted_pairs_greyed_out.append(rate_total)
                    
                    x_time_plot_dotted_pairs_greyed_out.append(stop_to)
                    y_time_plot_dotted_pairs_greyed_out.append(rate_total)
                    
                    x_time_plot_dotted_pairs.append(stop_to)
                    y_time_plot_dotted_pairs.append(rate_total)
                    
                    used_overlays.append((stop_from, stop_to))
                    
                    if (stop_from, stop_to) not in self.main_plot_overlays:
                        region_begin = max(_from, stop_from)
                        region_item = pg.LinearRegionItem(
                                            values=(region_begin, stop_to), 
                                            movable=False,
                                            pen=(0,0,0,0),
                                            )
                        region_item.setBrush(color=(10,10,10,150))
                        self.main_plot.addItem(region_item)
                        
                        self.main_plot_overlays[(stop_from, stop_to)] = region_item
                
                x_time_plot_dotted_pairs.append(_to)
                y_time_plot_dotted_pairs.append(rate_total)
                
                img.show()
            else:
                img = self.snapshot_views[snapshot]
                img.hide()
                
            # Plot ticks
            color = 255*np.array(
                    to_rgb(
                        "C{}".format(_type)
                        )
                )
            
            ticks.append((_from, color))
            
            previous_to = _to
        
        if previous_to is not None:
            ticks.append((_to, (99, 99, 99)))
        
        self.time_dotted_item.setData(x_time_plot_dotted_pairs, y_time_plot_dotted_pairs, connect="pairs")
        self.time_dotted_grayed_out_item.setData(x_time_plot_dotted_pairs_greyed_out, y_time_plot_dotted_pairs_greyed_out, connect="pairs")
        
        self.tickslider.setTicks(ticks)
        
        for tick, color in ticks:
            if tick not in self.plot_time_lines:
                line = pg.InfiniteLine()
                self.plot_time.addItem(line)
                self.plot_time_lines[tick] = line
            
            line = self.plot_time_lines[tick]
            line.setValue(tick)
            line.setPen(color)
            used_lines.append(tick)
        
        # TODO
        if sum_total_time > 0:
            channels = np.arange(len(sum_data) + 1)
            
            x = np.append(np.append([0], np.repeat(sum_data/sum_total_time, 2)), [0])
            y = np.repeat(channels,2)
            self.channel_dotted_item.setData(x, y + 0.5)
        else:
            self.channel_dotted_item.setData([])
        
        # ---
        
        # Colorbar scaling
        if self.cb_autoscale.isChecked():
            self.colorbar.setLevels(0, self.max_rate)
            self.colorbar.setRange(xRange=(0, self.max_rate))

        # ---
        
        # Remove unused overlays
        for overlay in list(self.main_plot_overlays):
            if overlay in used_overlays:
                continue
            
            overlay_item = self.main_plot_overlays[overlay]
            
            self.main_plot.removeItem(overlay_item)
            del self.main_plot_overlays[overlay]
            
        # Remove unused lines
        for line in list(self.plot_time_lines):
            if line in used_lines:
                continue
            
            line_item = self.plot_time_lines[line]
            
            self.plot_time.removeItem(line_item)
            del self.plot_time_lines[line]
    
    def applyYRegion(self, region):
        self.main_plot.setYRange(*region)

class CustomTickSliderItem(pg.TickSliderItem):
    def __init__(self, *args, **kwds):
        pg.TickSliderItem.__init__(self, *args, **kwds)
        
        self.all_ticks = []
        self.visible_ticks = {}
        self._range = [0,1]
    
    def setTicks(self, ticks):
        for tick, pos in self.listTicks():
            self.removeTick(tick)
        self.visible_ticks = {}
        
        self.all_ticks = ticks
        
        self.updateRange(None, self._range)
    
    def updateRange(self, vb, viewRange):
        origin = self.tickSize/2.
        length = self.length

        lengthIncludingPadding = length + self.tickSize + 2
        
        self._range = viewRange
        
        for pos, color in self.all_ticks:
            if pos not in self.visible_ticks:
                self.visible_ticks[pos] = self.addTick(pos, movable=False)
            
            tick = self.visible_ticks[pos]
            tick.color = pg.mkColor(color)
            
            tickValueIncludingPadding = (pos - viewRange[0]) / (viewRange[1] - viewRange[0])
            tickValue = (tickValueIncludingPadding*lengthIncludingPadding - origin) / length
            
            visible = tickValue >= 0 and tickValue <= 1
            
            if visible:
                self.setTickValue(tick, tickValue)
            elif pos in self.visible_ticks:
                self.removeTick(self.visible_ticks[pos])
                del self.visible_ticks[pos]
