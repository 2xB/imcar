import sys

import faulthandler
from PyQt5 import QtWidgets
from multiprocessing import Process
import os
import time

import faultguard
from mca_api.record_info import RecordInfo
from mca_api import utils, drivers
from imcar.gui import mainwindow
from imcar.gui.snapshot_save_dialog import *

def launch(faultguard_data, testing):
    """
    Launching MCA Recorder.
    
    :param faultguard_data: Faultguard data dictionary
    :param testing: Indicates whether the program is executed for testing purposes.
    """

    # Enable faulthandler to get trace route of e.g. segmentation faults
    faulthandler.enable()

    # Launch application
    mainwindow.main(faultguard_data, profiling = False, testing=testing)

def rescue_from_crash(faultguard_data, exit_code, testing):
    """
    Handle crash
    
    :param faultguard_data: Faultguard data dictionary
    :param testing: Indicates whether the program is executed for testing purposes.
    """
    rescue_dialog(faultguard_data, "iMCAr has crashed with exit code " + str(exit_code) + ".")

def rescue_from_savefile(autosave_file):
    def rescue_from_savefile_callback(faultguard_data, autosave_file=autosave_file):
        rescue_dialog(faultguard_data, f"A recent iMCAr session ended unexpectedly.\nBackup found:\n\"{autosave_file}\"\n")
    
    try:
        faultguard.recover(rescue_from_savefile_callback, autosave_file)
        os.remove(autosave_file)
        if os.path.isfile(autosave_file + ".tmp"):
            os.remove(autosave_file + ".tmp")
    except RuntimeError as e:
        print("Failed to rescue data from previous autosave:", e)
        rescue_dialog_nodata("Failed to rescue data from previous autosave.")
        autosave_backup = autosave_file + ".backup"
        os.rename(autosave_file, autosave_backup)
        if os.path.isfile(autosave_file + ".tmp"):
            os.rename(autosave_file + ".tmp", autosave_backup + ".tmp")

def rescue_dialog(faultguard_data, message):
    if "record_info" not in faultguard_data:
        rescue_dialog_nodata(message)
        return
        
    app = QtWidgets.QApplication([sys.argv])
    record_info = faultguard_data["record_info"]
    record_info.__class__ = RecordInfo

    QtWidgets.QMessageBox.critical(None, "DON'T PANIC!", message + "\n"\
                                        "The latest recorded data from the 'Live' tab is still accessible and you will be able "+\
                                        "to save it as soon as you close this dialog. Afterwards, if applicable and possible, "+\
                                        "you might also save all snapshots. Please consider creating an issue including "+\
                                        "as much information as possible - including the terminal output - on the GitLab project page:\n"+\
                                        "https://github.com/2xB/imcar .")
    dlg = snapshot_save_dialog(record_info, title="Save latest data")

    dlg.exec_()

    snapshots = []
    if "snapshot_count" in faultguard_data:
        for i in range(faultguard_data["snapshot_count"]):
            snap = faultguard_data[i]
            snap.__class__ = RecordInfo
            snapshots.append(snap)

    dlg = snapshots_save_dialog(snapshots)

    dlg.exec_()
    
    app.closeAllWindows()

def rescue_dialog_nodata(message):
    app = QtWidgets.QApplication([sys.argv])
    QtWidgets.QMessageBox.critical(None, "DON'T PANIC!", message + "\n"\
                                        "There is no recorded data from the 'Live' tab available for recovery. "+\
                                        "Please consider creating an issue including "+\
                                        "as much information as possible - including the terminal output - on the GitLab project page:\n"+\
                                        "https://github.com/2xB/imcar .")

def main(testing=None):
    """
    Start MCA Recorder application.

    Wraps application launch to show a message on crash.
    """
    print("imcar [--test]")
    print("   --test: Enable test devices for development purposes")
    print()
    print("# Path for custom drivers:", drivers.driver_path)
    print()
    print("---")
    print()
    print("Launching iMCAr.")
    
    if testing is None:
        testing = "--test" in sys.argv
    
    userdir = utils.user_data_dir("imcar")
    backupdir = os.path.join(userdir, "backup")
    os.makedirs(backupdir, exist_ok=True)
    
    for name in os.listdir(backupdir):
        fullname = os.path.join(backupdir, name)
        
        if not os.path.isfile(fullname):
            continue
        
        if ".backup" in name:
            continue
        
        if ".tmp" in name:
            continue
        
        if faultguard.is_active(fullname):
            continue
        
        p = Process(target=rescue_from_savefile, args=(fullname, ))
        p.start()
        p.join()
    
    autosave_file = os.path.join(backupdir, time.strftime("%Y%m%d-%H%M%S") + ".xz")
    faultguard.start(launch, rescue_from_crash, args=(testing), autosave_interval=1*60, autosave_file=autosave_file)


if __name__ == "__main__":
    main()
