# Testing ground for possible refactoring

class Notifier:
    def __init__(self):
        self._callbacks = []
    
    def add_callback(self, function):
        """
        Add function to call on notification
        """
        self._callbacks.append(function)
    
    def remove_callback(self, function):
        """
        No longer call function on notification
        """
        self._callbacks.remove(function)
    
    def notify(self):
        """
        Notify callback functions
        """
        for callback in self._callbacks:
            callback()


class DeviceViewNotifiers:
    def __init__(self):
        updated_status = Notifier()
        
        updated_main_hist = Notifier()
        updated_snap_hist = Notifier()
        updated_snap_fit  = Notifier()


class DeviceControlNotifiers:
    def __init__(self):
        start = DataBridge() # Infinite runs, timed runs etc.
        stop = DataBridge()  # Stop/Abord
        
        settings = DataBridge() # Device settings
        

class DeviceInfo:
    """
    Information about device, e.g. regarding available settings.
    """
    def __init__(self):
        pass
    

class VirtualDevice:
    def __init__(self):
        self.info = None # No device active
        self.view = DeviceViewNotifiers()
        self.control = DeviceControlNotifiers()
