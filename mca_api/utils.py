import sys
import os

def user_data_dir(appname):
    if sys.platform == "win32":
        # Windows
        path = os.getenv('LOCALAPPDATA', None)
        if not path:
            raise RuntimeError("Could not read LOCALAPPDATA environment variable")
    elif sys.platform == 'darwin':
        # Mac
        path = os.path.expanduser('~/Library/Application Support/')
    else:
        # Linux
        path = os.path.expanduser("~/.local/share")
    return os.path.join(path, appname)

def site_data_dir(appname):
    if sys.platform == "win32":
        # Windows
        path = os.getenv('ProgramData', None)
        if not path:
            raise RuntimeError("Could not read ProgramData environment variable")
    elif sys.platform == 'darwin':
        # Mac
        path = os.path.expanduser('/Library/Application Support/')
    else:
        # Linux
        path = os.path.expanduser("/usr/local/share")
    return os.path.join(path, appname)
