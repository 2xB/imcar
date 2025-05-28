import time
import datetime
import numpy as np
import copy

class RecordInfo():
    def __init__(self, device, channel_count):
        self.start_times = []
        self.stop_times = []
        self.device = device
        #self.eventcount = 0
        self.events = []
        self.channel_count = 0
        self.new_channel_count(channel_count)

        self.time_lastrun = 0
        self.livetime = 0
        self.livetime_previous = 0
        self.realtime = 0
        self.realtime_previous = 0
        
        self.name = None
        
        self.properties = None
        self.devicename = None

    def get_start_time(self):
        res = ""
        for i, (start, stop) in enumerate(zip(self.start_times, self.stop_times + ["..."])):
            if i > 0:
                res += ", "

            start_str = self.formatdate(start)
            if type(stop) != str:
                stop_str = self.formatdate(stop)
            else:
                stop_str = stop
            res += "({}, {})".format(start_str, stop_str)
        return res

    def get_first_start_time(self):
        if len(self.start_times) == 0:
            return ""
        
        return self.formatdate(self.start_times[0])

    def stopped(self):
        if self.is_running(): # Is running according to amount of stop times wrt. start times?
            # Add stop time
            self.stop_times.append(time.time())
            self.time_lastrun = self.time_lastrun + self.stop_times[-1] - self.start_times[-1]
            # Set previous livetime & realtime
            self.livetime_previous = self.livetime
            self.realtime_previous = self.realtime

    def get_stop_time(self):
        if self.is_running():
            return "Not yet"
        else:
            if len(self.stop_times) == 0:
                return ""
            
            return self.formatdate(self.stop_times[-1])

    def get_name(self):
        if self.name is None:
            return self.get_stop_time()
        return self.name

    def set_name(self, name):
        self.name = name

    def formatdate(self, time):
        return datetime.datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S')

    def get_realtime_pc(self):
        if self.is_running():
            return datetime.timedelta(seconds=self.time_lastrun+time.time()-self.start_times[-1]).total_seconds()
        else:
            return datetime.timedelta(seconds=self.time_lastrun).total_seconds()

    def capture(self, data):
        if len(data) == 0:
            return
        if self.device.internal_memory:
            self.events = data
        else:
            mask = data<self.channel_count
            if np.any(~mask):
                print("Events ignored because they are larger than expected:" + data[~mask])
            newevents = np.bincount(data[mask], minlength=self.channel_count)
            self.events = self.events + newevents
        return

    def restart(self):
        self.start_times.append(time.time())

    def eventcount(self):
        return np.sum(self.events)

    def get_snapshot(self):
        device = self.device
        self.device = None
        snapshot = copy.deepcopy(self)
        self.device = device
        
        if self.is_running:
            snapshot.stopped()
        
        snapshot.properties = self.properties_str()
        snapshot.devicename = self.unique_device_name()
        return snapshot

    def new_channel_count(self, channel_count):
        if self.channel_count < channel_count:
            self.centers = np.arange(1, channel_count + 1)
            self.edges   = np.arange(channel_count+1)+0.5
            self.events = np.append(self.events, np.zeros(channel_count-self.channel_count))
            self.channel_count = channel_count

    def headerstring(self):
        # zip(..., ...+ [-1]): Either (.,.),(.,.),(.,.) or (.,.),(.,.),(.,-1)
        return "#Run times:"+self.get_start_time()+"\n"+\
               "#Run time timestamps:"+str(list(zip(self.start_times, self.stop_times + ["..."])))+"\n"+\
               "#Device name:"+self.unique_device_name()+"\n"+\
               "#Time before started:"+str(self.time_lastrun)+"\n"+\
               "#Live time:"+str(self.livetime)+"\n"+\
               "#Real time:"+str(self.realtime)+"\n"+\
               "#PC Real time:"+str(self.get_realtime_pc())+"\n"+\
               "#Device settings:"+self.properties_str()+"\n"

    def fitplot_x(self, fac):
        """
        Higher-resolution x values to plot fit results.
        """
        return np.linspace(0, self.channel_count-1, len(self.events)*fac)+0.5

    # Device Connection
    def capture_time(self):
        """
        Loads live and realtime from device.
        """
        if self.device != None:
            livetime, realtime = self.device.read_time()
            if not self.device.internal_memory:
                livetime += self.livetime_previous
                realtime += self.realtime_previous
            if not self.device.has_error():
                self.livetime = livetime
                self.realtime = realtime

    def capture_events(self):
        """
        Loads events from device.
        """
        if self.device != None:
            events = self.device.read_events()
            
            if not self.device.has_error():
                self.capture(events)
            
    def unique_device_name(self):
        if self.device != None:
            return self.device.unique_device_name()
        if self.devicename != None:
            return self.devicename
        return "None"
        
    def properties_str(self):
        if self.device != None:
            return str(self.device.properties)
        if self.properties != None:
            return self.properties
        return "None"
        
    def is_empty(self):
        return self.livetime == 0 and self.realtime == 0 and np.sum(self.events) == 0
    
    def is_running(self):
        return len(self.start_times) > len(self.stop_times)
    
    def save(self, path):
        """
        Save snapshot to path.
        """
        np.savetxt(
                path, 
                np.array([self.centers,self.events]).T, 
                fmt='%i', 
                delimiter=';',
                header=self.headerstring()+"\n#Channel;Count"
            )
