from mca_api.properties import *
from mca_api.device_list import register_device
        
class DeviceState:
    """
    Enum representing current device state.
    """
    nonexistent = -1
    stopped = 0
    started = 1
    quit    = 2
    
    @staticmethod
    def connected(device_state):
        """
        Returns wether or not device status indicates a connected device.
        """
        return device_state is DeviceState.started or device_state is DeviceState.stopped

# "Interfaces"
class DeviceMCA:
    # Static
    channel_count = 8065
    name = "abstract device"
    internal_memory = False
    timing_internal = False # Indicates whether timed runs are stopped by device

    @staticmethod
    def find():
        """Find all devices of this type.
        Returns DeviceMCA instances."""
        return []

    # Dynamic
    state = DeviceState.stopped
    device_id = 0
    _log = None
    error = False
    error_message = None
    properties = None
    description = None
    initial_record_info = None # Replaces previous record info if not None
    log_level = 1

    def __init__(self):
        print("[Warning] Abstract device instantiated")
        print("---")
        import traceback as tb
        tb.print_stack()
        print("---")

    def init(self):
        """Init MCA Connection; Returns -1 if error"""
        self.properties = EmptyProperties(None)
        self.error_message = self.check_environment()
        error = self.error_message is not None
        return not error
    
    def check_environment(self):
        """
        Check for problems in the environment.
        
        Returns None if everything is fine. Returns message if the user is requred to take an action before the device is used.
        """
        return None

    def quit(self):
        """Quit MCA Connection"""
        self.state = DeviceState.quit
        return 0

    def timed_run_setup(self, timing_duration, timing_context):
        """
        Set a timed run up.
        
        Only if timing_internal.
        
        :param timing_duration: Total duration of timed run in s
        :param timing_context: Context of timing (0:device time, 2:live time)
        """
        if self.timing_internal:
            self.error_message = "timed_run_setup not implemented by driver"
            return False
        return True
    
    def timed_run_finished(self):
        """
        Cleans setup of timed run.
        
        Only if timing_internal.
        """
        if self.timing_internal:
            self.error_message = "timed_run_finished not implemented by driver"

    def is_running(self):
        """
        Whether the device is currently running.
        
        Only required if timing_internal.
        """
        if self.timing_internal:
            self.error_message = "is_running not implemented by driver"
            return False
        
        return self.state == DeviceState.started

    def start(self):
        """Start capturing data"""
        if self.state == DeviceState.stopped:
            self.state = DeviceState.started
            # Start code here
            return 0
        else:
            return 0

    def stop(self):
        """Stop capturing data"""
        if self.state == DeviceState.started:
            self.state = DeviceState.stopped
            # Stop code here
            return 0
        else:
            return 0
        return 0

    def read_events(self, buffer_size):
        """Read events.
        Returns: Array of new events.
        """
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read events from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read events from a quitted device.")
        # Reading code here
        return []

    def read_time(self):
        """Read live and real time.
        """
        livetime = self.read_livetime()
        realtime = self.read_realtime()
        return livetime, realtime

    def read_livetime(self):
        """Read live time"""
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read live time from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read live time from a quitted device.")
        return 0

    def read_realtime(self):
        """Read real time"""
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read real time from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read real time from a quitted device.")
        return 0

    def clear_events(self):
        """
        Clears all events from device memory if a memory exists.
        """
        pass

    def unique_device_name(self):
        """Get unique name of device"""
        return str(self.device_id) + " " + self.name

    def setLog(self, value):
        """Set logging device communication"""
        if value:
            self._log = ""
        else:
            self._log = None

    def log(self, text, level=1):
        """Write text to log (if log is not None) and for level > 0 to console."""
        if self._log is not None:
            self._log += text + "\n"
        if level > self.log_level:
            print("[Device Log]",text)

    def has_error(self):
        return self.error

    def activate_error(self):
        self.error = self.error or True
        
    def __getstate__(self):
        """
        Prevent Python from pickling devices.
        """
        return None
