import time
import datetime
import numpy as np
import copy
import math

import usb.core
import usb.util
import sys

from mca_api.device import DeviceMCA, DeviceState
from mca_api.properties import EmptyProperties, PropertyInt, PropertyDict
from mca_api.device_list import register_device

class Util:
    @staticmethod
    def to_byte(value, length):
        return (value).to_bytes(length, byteorder='little')
    
    @staticmethod
    def to_bytearray(value, length):
        return bytearray(Util.to_byte(value, length))
    
    @staticmethod
    def to_int(value):
        return int.from_bytes(value, byteorder='little')

# "Interfaces"
class CaenN957MCA(DeviceMCA):
    # Static
    channel_count = 8064 # Valid counts under any circumstances; Higher channels are invalid
                         # if device is in "sliding scale" mode. See device manual.
    name = "Caen N957"
    internal_memory = False
    timing_internal = False # Indicates whether timed runs are stopped by device

    @staticmethod
    def find():
        """Find all devices of this type.
        Returns DeviceMCA instances."""
        # Find device
        try:
            dev = list(usb.core.find(find_all=True,idVendor=0x0547, idProduct=0x1002))
            alldevs = []
            for i in range(len(dev)):
                device = dev[i]
                if device.get_active_configuration() is None:
                    device.set_configuration()
                alldevs.append(CaenN957MCA(i,device))
            return alldevs
        except (usb.core.USBError, usb.core.NoBackendError) as e:
            if isinstance(e, usb.core.USBError):
                print("CaenN957 device could not be registered. Please check README.")
            return []
    
    # Dynamic
    state = DeviceState.stopped
    device_id = 0
    dev = None
    properties = None
    descr = None
    
    def __init__(self, id, dev):
        self.id = id
        self.dev = dev
    
    # UTILITY
    def get_value(self, value_id):
        command = Util.to_bytearray(value_id,1)
        command.append(0x40)
        result = self.dev.write(2, command)
        assert result == len(command), "Unexpected answer to value " + str(value_id) + ": " + str(result)
        return self.dev.read(0x86, 16384*2) # Buffer is not larger than 16384, factor 2 for the case this assumption could be wrong

    def set_value(self, value_id, value):
        command = Util.to_bytearray(value_id,1)
        command.append(0x00)
        value = Util.to_bytearray(value,2)
        command.extend(value)
        result = self.dev.write(2, command) # TODO win error: Das Ger\xe4t erkennt den Befehl nicht.
        assert result == len(command)

    def setassert(self, value_id, value):
        self.set_value(value_id, value)
        result = Util.to_int(self.get_value(value_id))
        if result != value:
            self.log("[SETASSERTERR] Set and assert failed for value "+str(value_id)+" with result " + str(result))
    
    #CONTROL

    def init(self):
        """Init MCA Connection; Returns -1 if error"""
        self.properties = CaenN957Properties(self)
        try:
            firmware = Util.to_int(self.get_value(2))
            firmware_str = str(firmware)
            self.log("[STATUS] Init - Firmware: " + firmware_str,level=0)
        except usb.core.USBError as e:
            print(e)
            return False
        assert firmware == 8, "Unsupported Firmware Version: v" + firmware_str + ". Supported: v8"
        self.description = "Firmware: " + str(firmware)
        return True

    def quit(self):
        """Quit MCA Connection"""
        self.stop()
        self.state = DeviceState.quit
        usb.util.dispose_resources(self.dev)
        self.log("[STATUS] Disposed",level=0)
        self.dev = None
        return 0
        
    def reset(self):
        # Init
        self.set_value(0x13, 0x0000)
        self.set_value(0x13, 0x0000)
        value = Util.to_int(self.get_value(0x01))
        if value != 0x031e:
            print("Device was not quit successfully")
            self.log("[RESET] Device was not quit successfully")
        else:
            self.log("[RESET] Done.",level=0)
        
    def start(self):
        """Start capturing data"""
        try:
            self.reset()
        except usb.core.USBError as e:
            print(e)
            return 1
        if self.state == DeviceState.stopped:
            self.state = DeviceState.started
            mode_id = self.properties.mode.get_value()
            self.setassert(0x01, 0x011e)
            self.setassert(0x01, 0x001e+mode_id*0x0100)
            self.setassert(0x01, 0x001f+mode_id*0x0100)
            self.set_value(0x01, 0x005f+mode_id*0x0100)
            self.log("[STATE] Started recording with mode " + str(mode_id),level=0)
            return 0
        else:
            return 0
            
    def stop(self):
        """Stop capturing data"""
        if self.state == DeviceState.started:
            self.state = DeviceState.stopped
            mode_id = self.properties.mode.get_value()
            try:
                value = Util.to_int(self.get_value(0x01))
                if value == 0x005f+mode_id*0x0100:
                    self.log("[STATE] Stopped recording successfully with mode " + str(mode_id),level=0)
                else:
                    self.log("[STATE] Stopped recording with mode " + str(mode_id) + ", unexpected return value " + str(value))
            except usb.core.USBError as e:
                print(e)
                return 1
            self.set_value(0x01, 0x001e+mode_id*0x0100)
            return 0
        return 0

    def read_events(self):
        """Read events.
        Returns: Array of new events.
        """
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read events from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read events from a quitted device.")
        buffer_size = self.properties.buffer_value.current_value
        count = 0
        try:
            count = Util.to_int(self.get_value(0x0c))
            self.log("[EVENTCOUNT] Counted " + str(count) + " events",level=0)
        except usb.core.USBError as e:
            self.log("[READ_EVENTSERROR]"+str(e))
            self.activate_error()
            return []
        events = np.array([], dtype=int)
        if count != 0:
            self.set_value(0x07, buffer_size)
            events_raw = bytearray()
            new_len = buffer_size
            max_iterations = math.ceil(buffer_size*2/16384)
            for i in range(0,max_iterations):
                try:
                    new_events = bytearray(self.dev.read(0x86, buffer_size))
                    events_raw.extend(new_events)
                    if len(new_events) < 16384:
                        break;
                except usb.core.USBError as e:
                    break;
            if count < len(events_raw)>>1:
                self.log("[EVENTCOUNT] MCA announced " + str(count) + " events, but " + str(len(events_raw)) + "/2 received",level=0)
            for j in range(len(events_raw)>>1):
                events = np.append(events, Util.to_int(events_raw[j*2:j*2+2])>>3)
        self.log("[EVENTS] " + ' '.join(map(str, events)), level=0)
        events = events[events<self.channel_count]
                # Ignore values that are invalid if "sliding scale" is enabled
                # to prevent potentially invalid data. See device manual.
        return events

    def read_livetime(self):
        """Read live time"""
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read live time from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read live time from a quitted device.")
        try:
            self.set_value(0x0f, 0x0000)
        except usb.core.USBError as e:
            self.log("[READ_LIVETIMEERROR]" + str(e))
            self.activate_error()
            return -1
        livetime = bytearray(self.get_value(0x11))
        livetime.extend(bytearray(self.get_value(0x12)))
        livetime_int = Util.to_int(livetime)
        self.log("[LIVETIME] " + str(livetime_int),level=0)
        return livetime_int/1000

    def read_realtime(self):
        """Read real time"""
        if self.state == DeviceState.stopped:
            raise ValueError("Trying to read real time from a stopped device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read real time from a quitted device.")
        try:
            self.set_value(0x0f, 0x0000)
        except usb.core.USBError as e:
            self.log("[READ_REALTIMEERROR]" + str(e))
            self.activate_error()
            return -1
        realtime = bytearray(self.get_value(0x0f))
        realtime.extend(bytearray(self.get_value(0x10)))
        realtime_int = Util.to_int(realtime)
        self.log("[LIVETIME] " + str(realtime_int),level=0)
        return realtime_int/1000
    
    def _set_threshold(self, value):
        if value > 99:
            self.log("[THRES_ERR] Value too high")
        if self.state == DeviceState.started:
            raise ValueError("Trying to set threshold of a started device.")
        if self.state == DeviceState.quit:
            raise ValueError("Trying to read real time from a quitted device.")
        self.log("[STATE] Setting threshold to " + str(value),level=0)
        self.set_value(0x0a, 0x40)
        self.set_value(0x0a, 0x20)
        self.set_value(0x09, 0x20)
        self.set_value(0x09, 0x40)
        self.set_value(0x0a, 0x02)
        self.set_value(0x09, 0x08)
        for i in range(100):
            time.sleep(0.01)
            self.set_value(0x0a, 0x04)
            time.sleep(0.01)
            self.set_value(0x09, 0x04)
        self.set_value(0x0a, 0x08)
        for i in range(value):
            time.sleep(0.01)
            self.set_value(0x0a, 0x04)
            time.sleep(0.01)
            self.set_value(0x09, 0x04)
        assertvalue = Util.to_int(self.get_value(0x09))
        if assertvalue != 0x65:
            self.log("[THRES] Expected {:x}, got {:x}.".format(0x65, assertvalue))
        self.set_value(0x09, 0x02)
        self.set_value(0x0a, 0x40)
        self.set_value(0x0a, 0x20)
        self.log("[STATE] Threshold set",level=0)
        return 0
        

class CaenN957Properties(EmptyProperties):
    buffer_value = PropertyInt("Buffer size", 1, 39321, 16384)
    mode = PropertyDict("Gate Mode", {"Auto":3, "Ext. Gate":1}, "Auto")
    indirect = [buffer_value, mode]

    threshold = PropertyInt("Set Threshold", 1, 99, 10, CaenN957MCA._set_threshold, unset_at_start=True)
    direct = [threshold]                     

register_device(CaenN957MCA)
