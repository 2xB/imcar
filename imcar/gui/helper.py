# THIS DOCUMENT IS LICENSED UNDER CC BY-SA 3.0
# https://creativecommons.org/licenses/by-sa/3.0/

# The following source code is taken from user "Jean-Sébastien" and the stackoverflow post https://stackoverflow.com/a/32085761 .
# It is modified to support PyQt5 instead of PySide and to adapt to the system color scheme.
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt # This is needed to "apply" matplotlib.use. Otherwise if tkinter is not installed,
                                # matplotlib would not be correctly initialized, resulting in errors.
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PyQt5 import QtGui, QtWidgets

def mathTex_to_QPixmap(mathTex, fs, rgba_array):
    #---- set up a mpl figure instance ----
    fig = matplotlib.figure.Figure()
    fig.patch.set_facecolor('none')
    fig.set_canvas(FigureCanvasAgg(fig))
    renderer = fig.canvas.get_renderer()

    #---- plot the mathTex expression ----

    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.patch.set_facecolor('none')
    t = ax.text(0, 0, mathTex, ha='left', va='bottom', color=rgba_array, fontsize=fs)

    #---- fit figure size to text artist ----

    fwidth, fheight = fig.get_size_inches()
    fig_bbox = fig.get_window_extent(renderer)

    text_bbox = t.get_window_extent(renderer)

    tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
    tight_fheight = text_bbox.height * fheight / fig_bbox.height

    fig.set_size_inches(tight_fwidth, tight_fheight)

    #---- convert mpl figure to QPixmap ----

    buf, size = fig.canvas.print_to_buffer()
    qimage = QtGui.QImage.rgbSwapped(QtGui.QImage(buf, size[0], size[1],
                                                  QtGui.QImage.Format_ARGB32))
    qpixmap = QtGui.QPixmap(qimage)

    return qpixmap

# The following source code is taken from user "Michael Leonard" and the stackoverflow post https://stackoverflow.com/a/41068447/8575607 .
class QHLine(QtWidgets.QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)

# The following source code is adapted from user "Duncan" and the stackoverflow post https://stackoverflow.com/a/3467879/8575607 .
import functools
def decorate_log_calls(cls, callback):
    """
    Calls callback function on method calls to given class
    
    Parameters:
        cls: The class to add callback to
        callback: The callback function receiving name, args, kwargs and result of the executed function
    """
    def decorator(name, member):
        @functools.wraps(member) # Ensure function signature etc. stays valid
        def wrapper(*args, **kwargs):
            if cls.__logcallwrap_block:
                return member(*args, **kwargs)
            
            cls.__logcallwrap_block = True
            res = member(*args, **kwargs)
            cls.__logcallwrap_block = False
            callback(name, args, kwargs, res)
            return res
            
        return wrapper
    
    cls.__logcallwrap_block = False
    
    for name in dir(cls):
        if name.startswith("__"):
            continue
        
        member = cls.__dict__[name]
        if callable(member):
            setattr(cls, name, decorator(name, member))
            

import numpy as np
from collections.abc import Sequence
# author: Sebastian Hoefer
def cmapToColormap(cmap, nTicks=16):
    """
    Converts a Matplotlib cmap to pyqtgraphs colormaps. No dependency on matplotlib.
    Parameters:
    *cmap*: Cmap object. Imported from matplotlib.cm.*
    *nTicks*: Number of ticks to create when dict of functions is used. Otherwise unused.
    """

    # Case #1: a dictionary with 'red'/'green'/'blue' values as list of ranges (e.g. 'jet')
    # The parameter 'cmap' is a 'matplotlib.colors.LinearSegmentedColormap' instance ...
    if hasattr(cmap, '_segmentdata'):
        colordata = getattr(cmap, '_segmentdata')
        if ('red' in colordata) and isinstance(colordata['red'], Sequence):
            # print("[cmapToColormap] RGB dicts with ranges")

            # collect the color ranges from all channels into one dict to get unique indices
            posDict = {}
            for idx, channel in enumerate(('red', 'green', 'blue')):
                for colorRange in colordata[channel]:
                    posDict.setdefault(colorRange[0], [-1, -1, -1])[idx] = colorRange[2]

            indexList = list(posDict.keys())
            indexList.sort()
            # interpolate missing values (== -1)
            for channel in range(3):  # R,G,B
                startIdx = indexList[0]
                emptyIdx = []
                for curIdx in indexList:
                    if posDict[curIdx][channel] == -1:
                        emptyIdx.append(curIdx)
                    elif curIdx != indexList[0]:
                        for eIdx in emptyIdx:
                            rPos = (eIdx - startIdx) / (curIdx - startIdx)
                            vStart = posDict[startIdx][channel]
                            vRange = (posDict[curIdx][channel] - posDict[startIdx][channel])
                            posDict[eIdx][channel] = rPos * vRange + vStart
                        startIdx = curIdx
                        del emptyIdx[:]
            for channel in range(3):  # R,G,B
                for curIdx in indexList:
                    posDict[curIdx][channel] *= 255

            posList = [[i, posDict[i]] for i in indexList]
            return posList

        # Case #2: a dictionary with 'red'/'green'/'blue' values as functions (e.g. 'gnuplot')
        elif ('red' in colordata) and isinstance(colordata['red'], collections.Callable):
            # print("[cmapToColormap] RGB dict with functions")
            indices = np.linspace(0., 1., nTicks)
            luts = [np.clip(np.array(colordata[rgb](indices), dtype=np.float), 0, 1) * 255 \
                    for rgb in ('red', 'green', 'blue')]
            return list(zip(indices, list(zip(*luts))))

    # If the parameter 'cmap' is a 'matplotlib.colors.ListedColormap' instance, with the attributes 'colors' and 'N'
    elif hasattr(cmap, 'colors') and hasattr(cmap, 'N'):
        colordata = getattr(cmap, 'colors')
        # Case #3: a list with RGB values (e.g. 'seismic')
        if len(colordata[0]) == 3:
            # print("[cmapToColormap] list with RGB values")
            indices = np.linspace(0., 1., len(colordata))
            scaledRgbTuples = [(rgbTuple[0] * 255, rgbTuple[1] * 255, rgbTuple[2] * 255) for rgbTuple in colordata]
            return list(zip(indices, scaledRgbTuples))

        # Case #4: a list of tuples with positions and RGB-values (e.g. 'terrain')
        # -> this section is probably not needed anymore!?
        elif len(colordata[0]) == 2:
            # print("[cmapToColormap] list with positions and RGB-values. Just scale the values.")
            scaledCmap = [(idx, (vals[0] * 255, vals[1] * 255, vals[2] * 255)) for idx, vals in colordata]
            return scaledCmap

    # Case #X: unknown format or datatype was the wrong object type
    else:
        raise ValueError("[cmapToColormap] Unknown cmap format or not a cmap!")


# # The following source code is adapted from users "Mik R" and "Michael Herrmann" from the stackoverflow post https://stackoverflow.com/a/62035028 .
from PyQt5 import QtCore, QtGui
def apply_dark_palette(app):
    # Force the style to be the same on all OSs:
    app.setStyle("Fusion")

    # Now use a palette to switch to dark colors:
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(35, 35, 35))
    dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(25, 25, 25))
    dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QtGui.QPalette.Dark, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(35, 35, 35))
    dark_palette.setColor(QtGui.QPalette.Active, QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, QtCore.Qt.darkGray)
    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, QtCore.Qt.darkGray)
    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, QtCore.Qt.darkGray)
    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Light, QtGui.QColor(53, 53, 53))
    app.setPalette(dark_palette)


import markdown2
def markdown_to_html(markdown):
    doc_html = '<style type="text/css">'+\
                '  code { background-color: rgba(0, 0, 0, .2);font-weight: bold;}'+\
                ' </style>' + \
            markdown2.markdown(markdown, extras=["tables", "fenced-code-blocks"])
    return "<!doctype html><html><body>"+doc_html+"</body></html>"
