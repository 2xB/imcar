![iMCAr logo](design/logo/logo_wide.png)

# iMCAr: The interactive MCA recorder

This software provides a user-friendly application to use Multi-Channel Analyzers (MCA).

![Screenshot of iMCAr with example data](screenshot.png)

## Contributing
If you e.g. develop your own drivers for iMCAr or extend the application in a different way, consider contributing the code back to this repository through a Pull Request! There is no guarantee that the changes are merged since they may go into a different direction than the original aim of the software, so before implementing a large change consider opening an issue suggesting that feature so it can be discussed beforehand.

## SAFETY NOTE
This software is not developed for usage in medical or other high precision environments. It does implement data recovery after application crashes, however that may not be perfect.  
If you can, please run this software through a terminal so you can report stack traces of crashes on GitHub if you encounter a crash.
Be careful!

## Installation

For this software Python has to be installed and part of the PATH variable. The software is tested with Python 3.8.2. The Windows installer wizard asks at the beginning, if it should edit the PATH. Possibly at the end of the installation the adjustment of its length has to be accepted.

Many Linux distributions ship Python 3 as "python3" with "pip3" (opposed to "python" and "pip"). If that does not work, the commands have to be entered without the number 3.

After downloading the application, in the folder with this README.md file the following commands have to be executed:

```
pip3 install --upgrade setuptools
python3 setup.py install
```

You now can already start the software. To add your device to the software, open the documentation by either clicking the "➕" sign next to the device list.

## Uninstallation

```
pip3 uninstall imcar
```

## Start

After installation the program can be launched with the command

```
imcar
```

. To add a desktop shortcut, the location of the launcher can be found with `where imcar` (Windows) or `whereis imcar` (Linux/Unix). An icon is included in form of the file `imcar/gui/icon.ico`.

**Warning:** This only works if no virtual environment (e.g. via Anaconda) is used. For Anaconda3 under Windows, a solution would be to right click on the on the desktop shortcut, go to the 'Shortcut' tab and change "Start in" to `C:\Users\<username>\Anaconda3\Library\bin` or the equivalent path in your installation.

## Troubleshooting

If the application does not launch, executing
```
sudo pip3 uninstall pyqt5-sip pyqt5 pyqtwebengine
sudo pip3 install pyqtwebengine
```
may solve the problem. The reason is that `pyqt5-sip` has to be installed BEFORE `pyqt5`. Also, both have to be installed in the same directory (`sudo pip3` and `pip3` must not be mixed). The installer of `PyQtWebEngine` installs everything in the right order, so the problem can be solved by uninstalling everything and purely executing the latest installer.

## License

If not stated otherwise in the corresponding files, source code is distributed unter the GPLv3 license. This is at the moment required since this library uses the free version of PyQt5.

## Dependencies

The following requirements are automatically installed if the recommended setup.py is used.

NumPy: <https://www.numpy.org/>  
Matplotlib: <https://matplotlib.org/>  
SciPy: <https://www.scipy.org/>  
Uncertainties: <https://pythonhosted.org/uncertainties/>  
PyUSB: <https://pyusb.github.io/pyusb/>  
PyQt5: <https://www.riverbankcomputing.com/software/pyqt/>  
PyQTGraph: <http://www.pyqtgraph.org/>  
Markdown2: <https://github.com/trentm/python-markdown2>  
faultguard: <https://github.com/2xB/faultguard>  

faultguard was initially developed for this project.

## Currently supported MCAs
As a design principle, this software has no dependencies to binaries from third partys such as MCA manufacturers. This allows the software to be platform independent and open source, but also makes it necessary to reverse engineer every MCA USB protocol for every supported product. If you are a vendor or want to contribute out of other reasons, please get in touch by e.g. creating an github issue with your contact address.


| Name             &nbsp;| Vendor ID   &nbsp;| Product ID    &nbsp;| Data Transfer Type   &nbsp;| Notes                            |
| -----------------------| ------------------| --------------------| ---------------------------| ---------------------------------|
| CAEN N957 8K MCA &nbsp;| 0x0547      &nbsp;| 0x1002        &nbsp;| Eventwise channel IDs&nbsp;| Reading first 8064 channels [1]  |


**Notes**  

[1] The last channels are ignored since they can be invalid depending on internal settings.


## Credits
**Funding:** Institute for Nuclear Physics, University of Münster, Germany
