import numpy as np
import random
import time

from mca_api.device import DeviceMCA, DeviceState
from mca_api.properties import EmptyProperties, PropertyInt, PropertyDict
from mca_api.device_list import register_device

# Included Classes:
# BrokenMCA, RandomMCA, RandomProperties
    
# Broken Device
class BrokenMCA(DeviceMCA):
    # Static
    name = "broken test device"
    @staticmethod
    def find():
        return [BrokenMCA()]
    
    # Dynamic
    error = True
    
    def __init__(self, error_message=None):
        self.error_message = error_message

register_device(BrokenMCA, True)

# Random example device
class RandomMCA(DeviceMCA):
    # Static
    channel_count = 8065
    name = "random device"
    internal_memory = False
    timing_internal = False # Indicates whether timed runs are stopped by device

    @staticmethod
    def find():
        """Find all devices of this type.
        Returns DeviceMCA instances."""
        return [RandomMCA()]
    
    # Dynamic
    properties = None

    def __init__(self):
        self.state = DeviceState.stopped
        self.time = None
        self.lifetimesubtraction = 0
        self.mean = 10
        self.device_id = int(random.random()*10)
        self.firmware = int(random.random()*200)/100
        self.oldtime = 0

    def init(self):
        """Init MCA Connection; Returns -1 if error"""
        self.log("[STATUS] Init - Firmware: " + str(self.firmware),level=0)
        self.properties = RandomProperties(self)
        self.description = "Firmware: " + str(self.firmware)
        return True

    def quit(self):
        """Quit MCA Connection"""
        self.stop()
        self.state = DeviceState.quit
        self.log("[STATUS] Quit",level=0)
        return 0

    def start(self):
        """Start capturing data"""
        if self.state == DeviceState.stopped:
            self.state = DeviceState.started
            self.time = time.time()
            self.log("[STATE] Started recording",level=0)
            return 0
        else:
            return 0

    def stop(self):
        """Stop capturing data"""
        if self.state == DeviceState.started:
            self.state = DeviceState.stopped
            # Stop code here
            self.oldtime = 0
            self.time = None
            self.lifetimesubtraction = 0
            self.log("[STATE] Stopped recording",level=0)
            return 0
        else:
            return 0
        return 0

    def read_events(self):
        """Read events.
        Returns: Array of new events.
        """
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read events from a stopped device.")
        if self.state == DeviceState.quit:
            print("q2",self)
            raise ValueError("Trying to read events from a quitted device.")
        buffer_size = self.properties.buffer_value.current_value
        count = int(random.random()*(buffer_size+1))
        self.log("[EVENTCOUNT] Counted " + str(count) + " events",level=0)
        events = np.random.normal(self.mean,scale=self.properties.scale.current_value,size=count).astype(int)
        events = events[events<8064]
        events = events[events>0]
        self.lifetimesubtraction = self.lifetimesubtraction + len(events)
        self.log("[EVENTS] " + ' '.join(map(str, events)),level=0)
        return events

    def read_livetime(self):
        """Read live time"""
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read live time from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read live time from a quitted device.")
        livetime_int = int(self.read_realtime()-self.lifetimesubtraction*0.000005)
        self.log("[LIVETIME] " + str(livetime_int),level=0)
        return livetime_int

    def read_realtime(self):
        """Read real time"""
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read real time from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read real time from a quitted device.")
        realtime_int = int(self.oldtime + time.time()-self.time)
        self.log("[REALTIME] " + str(realtime_int),level=0)
        return realtime_int

    # Configuration functions
    def _set_mean(self, value):
        """Set mean to given value"""
        if self.state == DeviceState.started:
            raise ValueError("Trying to set threshold of a started device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read real time from a quitted device.")
        self.mean = value
        self.log("[STATE] Setting threshold to " + str(value),level=0)
        return 0

class RandomProperties(EmptyProperties):
    buffer_value = PropertyInt("Buffer size", 1, 39321, 16384)
    mode = PropertyDict("Gate Mode", {"Auto":3, "Ext. Gate":1}, "Auto")
    scale = PropertyInt("Scale", 1, 4000,1)
    indirect = [buffer_value, mode, scale]

    threshold = PropertyInt("Set Mean", 1, 9999, 100, RandomMCA._set_mean, unset_at_start=True)
    direct = [threshold]

register_device(RandomMCA, True)


# Random example device
class RandomInternalMemoryMCA(DeviceMCA):
    # Static
    channel_count = 8065
    name = "random internal memory device"
    internal_memory = True
    timing_internal = False # Indicates whether timed runs are stopped by device
    
    @staticmethod
    def find():
        """Find all devices of this type.
        Returns DeviceMCA instances."""
        return [RandomInternalMemoryMCA()]

    # Dynamic
    properties = None

    def __init__(self):
        self.state = DeviceState.stopped
        self.time = None
        self.lifetimesubtraction = 0
        self.mean = 10
        self.device_id = int(random.random()*10)
        self.firmware = int(random.random()*200)/100
        self.oldtime = 0
        self.events = np.zeros(8065)
        
    def clear_events(self):
        self.oldtime = 0
        self.time = None
        self.lifetimesubtraction = 0
        self.events = np.zeros(8065)

    def init(self):
        """Init MCA Connection; Returns -1 if error"""
        self.log("[STATUS] Init - Firmware: " + str(self.firmware),level=0)
        self.properties = RandomInternalProperties(self)
        self.description = "Firmware: " + str(self.firmware)
        return True

    def quit(self):
        """Quit MCA Connection"""
        self.stop()
        self.state = DeviceState.quit
        self.log("[STATUS] Quit",level=0)
        return 0

    def start(self):
        """Start capturing data"""
        if self.state == DeviceState.stopped:
            self.state = DeviceState.started
            self.time = time.time()
            self.log("[STATE] Started recording",level=0)
            return 0
        else:
            return 0

    def stop(self):
        """Stop capturing data"""
        if self.state == DeviceState.started:
            self.state = DeviceState.stopped
            # Stop code here
            self.oldtime = self.oldtime + time.time()-self.time
            self.log("[STATE] Stopped recording",level=0)
            return 0
        else:
            return 0
        return 0

    def read_events(self):
        """Read events.
        Returns: Array of new events.
        """
        if self.state == DeviceState.stopped:
            return self.events
        if self.state == DeviceState.quit:
            print("q2",self)
            raise ValueError("Trying to read events from a quitted device.")
        buffer_size = self.properties.buffer_value.current_value
        count = int(random.random()*(buffer_size+1))
        self.log("[EVENTCOUNT] Counted " + str(count) + " events",level=0)
        events = np.random.normal(self.mean,scale=self.properties.scale.current_value,size=count).astype(int)
        events = events[events<8064]
        events = events[events>0]
        self.lifetimesubtraction = self.lifetimesubtraction + len(events)
        self.log("[EVENTS] " + ' '.join(map(str, events)),level=0)
        self.events += np.bincount(events, minlength=8065)
        return self.events

    def read_livetime(self):
        """Read live time"""
        livetime_int = int(self.read_realtime()-self.lifetimesubtraction*0.000005)
        self.log("[LIVETIME] " + str(livetime_int),level=0)
        return livetime_int

    def read_realtime(self):
        """Read real time"""
        if self.state == DeviceState.stopped:
            return self.oldtime
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read real time from a quitted device.")
        realtime_int = int(self.oldtime + time.time()-self.time)
        self.log("[REALTIME] " + str(realtime_int),level=0)
        return realtime_int

    # Configuration functions
    def _set_mean(self, value):
        """Set mean to given value"""
        if self.state == DeviceState.started:
            raise ValueError("Trying to set threshold of a started device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read real time from a quitted device.")
        self.mean = value
        self.log("[STATE] Setting threshold to " + str(value),level=0)
        return 0


class RandomInternalProperties(EmptyProperties):
    buffer_value = PropertyInt("Buffer size", 1, 39321, 16384)
    mode = PropertyDict("Gate Mode", {"Auto":3, "Ext. Gate":1}, "Auto")
    scale = PropertyInt("Scale", 1, 4000,1)
    indirect = [buffer_value, mode, scale]

    threshold = PropertyInt("Set Mean", 1, 9999, 100, RandomInternalMemoryMCA._set_mean)
    direct = [threshold]

register_device(RandomInternalMemoryMCA, True)
