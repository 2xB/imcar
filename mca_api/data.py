import datetime

from mca_api import device_list
from mca_api.record_info import RecordInfo
from mca_api.device import DeviceState, DeviceMCA

from mca_api.fitting import FitInfo

class CallbackCollection:
    """
    Collection of callback functions
    """
    def __init__(self):
        self.callbacks = []
        
    def append(self, function):
        """
        Append function to callbacks
        """
        self.callbacks.append(function)
        
    def call(self, *args, **kwargs):
        """
        Call callback functions with args and kwargs
        """
        for callback in self.callbacks:
            callback(*args, **kwargs)

class DataManager:
    """
    Singleton containing the current application state.
    """
    
    # General Variables
    selected_device = None
    active_devices = []
    snapshots = []
    visible_snapshots = []
    active_snapshot = True
    fit_info = None
    last_region = None
    _record_info = None
    error_message = None
    generic_error_message = \
        "The device could not be adressed. Try (re)connecting computer and device and reloading the device list.\n"+\
        "For device and operating system specific troubleshooting, read the Readme or the About tab in the GUI."
    
    # Timing info
    is_timed = False # Is the current run timed?
    timing_time = 0  # Time to record in total
    timing_unit = 0  # Unit of time to record (s, min, h, d)
    timing_context = 0 # Context of timing (device time, PC time, live time)
    timing_start = 0 # Time at start
    
    manager = None
    
    def __init__(self, faultguard_data, profiling, testing):
        """
        Do not use. Use DataManager.get_mgr instead.
        """
        if DataManager.manager is not None:
            raise RuntimeError("Did not initialize via get_mgr() or is instanciated over multiple prcesses")
            
        self.faultguard_data=faultguard_data
        self.testing = testing
        
        self.callbacks_tick_request = CallbackCollection()
        self.callbacks_start = CallbackCollection()
        self.callbacks_stop = CallbackCollection()
        
        self.callbacks_snapshots_changed = CallbackCollection()
        self.callbacks_record_existence_changed = CallbackCollection()

        self.callbacks_device_changed = CallbackCollection()
        self.callbacks_device_errored = CallbackCollection()
        
        #if testing:
        #    DeviceMCA.log_level = -9001
        
        # Profiling for optimization
        self.profiling = profiling
        if profiling:
            self.last_count = datetime.datetime.now()
            
    # Singleton Method
    @staticmethod
    def get_mgr(faultguard_data, profiling, testing):
        """
        Static singleton factory method for DataManager
        """
        DataManager.manager = DataManager(faultguard_data, profiling, testing)
        return DataManager.manager
    
    @property
    def record_info(self):
        return self._record_info

    @record_info.setter
    def record_info(self, value):
        if self._record_info == value:
            return
        
        old = self._record_info

        self._record_info = value

        if old is None or value is None:
            self.callbacks_record_existence_changed.call()
    
    def pop_error_message(self):
        """
        Get and clear error_message
        """
        error_message = self.error_message
        self.error_message = None
        return error_message
    
    # Function callback on tick request
    def add_tick_request_callback(self, function):
        """
        Call function on tick request, passing time until tick in milliseconds
        """
        self.callbacks_tick_request.append(function)
    
    def add_start_callback(self, function):
        """
        Call function on start of device
        """
        self.callbacks_start.append(function)
    
    def add_stop_callback(self, function):
        """
        Call function on tick request cancellation
        """
        self.callbacks_stop.append(function)
        
    def add_snapshots_changed_callback(self, function):
        """
        Call function on snapshot changes
        """
        self.callbacks_snapshots_changed.append(function)
    
    def add_record_existence_callback(self, function):
        """
        Call function on record changes
        """
        self.callbacks_record_existence_changed.append(function)
    
    def add_device_changed_callback(self, function):
        """
        Call function on change of selected device
        """
        self.callbacks_device_changed.append(function)
    
    def add_device_errored_callback(self, function):
        """
        """
        self.callbacks_device_errored.append(function)
        
    # Device descriptors
    def get_infos(self):
        """
        Returns current device infos.
        """
        return device_list.all_drivers(self.testing)
        
    # .Active devices
    def refresh_active_devices(self):
        infos = self.get_infos()
        self.quit_active_devices()
        self.active_devices = []
        for info in infos:
            self.active_devices.extend(info.find())
            
    def get_active_devices(self):
        return self.active_devices
        
    # .Selected device
    def selected_device_unselect(self):
        """
        Stops selected device and unsets it.
        
        Returns
        True if device existed before, False otherwise
        """
        if self.selected_device != None:
            self.stop_selected_device()
            self.__set_device(None)
            self.callbacks_device_changed.call()
            return True
        return False
        
    def quit_active_devices(self):
        """
        Quits selected device.
        
        Return
        Success (Boolean)
        """
        for device in self.active_devices:
            device.quit()
        return True
        
    def __init_record_info(self):
        """
        Creates new record info if none existed.
        """
        no_recordinfo = self.record_info == None
        if no_recordinfo:
            self.record_info = RecordInfo(self.selected_device, self.selected_device.channel_count)
        return no_recordinfo
            
    def __cancel_record_info(self):
        """
        Clears record info and sets device to None.
        """
        if self.record_info.is_empty():
            self.record_info = None
        self.__set_device(None)
        self.callbacks_device_changed.call()
        
    def __selected_device__start(self):
        """
        Start data taking on selected device.
        """
        self.__init_record_info()
        self.record_info.restart()
        
        success = self.selected_device.start() == 0
        if success:
            self.callbacks_tick_request.call(150)
        else:
            self.stop_selected_device()
            self.selected_device_unselect()
            self.__cancel_record_info()
        return success
    
    def __context_time(self, context):
        record_info = self.get_record_info()
        if record_info is None:
            return 0
        
        if context == 0: # Device runtime
            return record_info.realtime
        elif context == 1: # PC runtime
            return self.record_info.get_realtime_pc()
        else: # Livetime
            return self.record_info.livetime
    
    def __timing_duration(self):
        if self.timing_unit == 0:
            multiplier = 1
        elif self.timing_unit == 1:
            multiplier = 60
        elif self.timing_unit == 2:
            multiplier = 60*60
        else:
            multiplier = 60*60*24
        
        return self.timing_time*multiplier
    
    def load_error_selected_device(self):
        """
        Loads the current error of the active device or a generic error message.
        """
        new_error_message = self.selected_device.error_message
        if new_error_message is not None:
            self.error_message = new_error_message
        if self.error_message is None:
            self.error_message = self.generic_error_message
        self.callbacks_device_errored.call()
    
    def untimed_start_selected_device(self):
        """
        Starts untimed data taking on selected device
        """
        self.is_timed = False
        
        success = self.__selected_device__start()

        if not success:
            self.load_error_selected_device()

        self.callbacks_start.call()
    
    def timed_start_selected_device(self, timing_time:float, timing_unit:int, timing_context:int):
        """
        Starts timed data taking on selected device.
        
        :param timing_time: Time to record in total
        :param timing_unit: Unit of time to record (0:s, 1:min, 2:h, 3:d)
        :param timing_context: Context of timing (0:device time, 1:PC time, 2:live time)
        """
        self.is_timed = True
        self.timing_time = timing_time
        self.timing_unit = timing_unit
        self.timing_context = timing_context
        self.timing_start = self.__context_time(self.timing_context)
        
        self.timing_responsible = (timing_context == 1) or (not self.selected_device.timing_internal) # Is mca_api responsible for controlling the timing status?
        
        if not self.timing_responsible:
            if not self.selected_device.timed_run_setup(self.__timing_duration(), timing_context):
                return False
        
        success = self.__selected_device__start()

        if not success:
            self.load_error_selected_device()

        self.callbacks_start.call()
        
    def stop_selected_device(self):
        """
        Stops data taking on selected device.
        """
        if self.selected_device is not None:
            self.selected_device.stop()
            
            if self.record_info is not None:
                self.record_info.stopped()
            
            if self.selected_device.internal_memory and self.record_info is not None:
                self.tick_selected_device()
        self.callbacks_stop.call()
            
    def timing_status(self):
        if not self.is_timed:
            return 0
        
        current = self.__context_time(self.timing_context) - self.timing_start
        
        value = current / self.__timing_duration()
        if value > 1:
            value = 1
        
        return value
        
    def tick_selected_device(self):
        """
        Process single device record.

        Returns False if data should not be taken.
        """
        # Capture Events
        self.record_info.capture_events()
        
        # Capture Time
        self.record_info.capture_time()
        
        error = self.selected_device.has_error()
        
        if error:
            self.load_error_selected_device()
            return -1
        
        # Autosave to RAM
        self.__backup_record_info()

        self.timing_current = self.timing_status()
        
        if self.record_info.is_running():
            self.callbacks_tick_request.call(150)
        
        if not self.is_timed:
            return True
        
        if self.timing_responsible:
            return self.timing_current != 1
        else:
            if self.selected_device.is_running():
                return True
            else:
                self.selected_device.timed_run_finished()
                return False

    def selected_device_has_error(self):
        if self.selected_device != None:
            return self.selected_device.has_error()
        else:
            return False
        
    def clear_events(self):
        """
        Clear events from buffer and device.
        """
        if self.selected_device is not None:
            if self.selected_device.is_running():
                print("Warning: Trying to clear running device")
                return
            
            self.selected_device.clear_events()
        
        self.record_info = None
        
    def change_device_index(self, index:int):
        """
        Change the current device index.
        
        Returns success (boolean) or None.
        """
        newdevice = self.active_devices[index]
        if newdevice != self.selected_device:
            if self.selected_device is not None:
                self.selected_device_unselect()
            self.__set_device(newdevice)
            success = self.__init_device()
            if newdevice.internal_memory:
                if self.record_info is not None:
                    self.new_snapshot()
                    self.record_info = None
                if newdevice.initial_record_info is not None:
                    self.record_info = newdevice.initial_record_info
                newdevice.initial_record_info = None
                
            if not success:
                self.load_error_selected_device()
            
            self.callbacks_device_changed.call()
            return success
        return None
                
    def __set_device(self, device):
        """
        Sets selected device to current record info and manager.
        Note: Call self.callbacks_device_changed.call() after success!
        """
        if self.record_info is not None:
            self.record_info.device = device
        self.selected_device = device
        
        
    def __init_device(self):
        success = not self.selected_device.error and self.selected_device.init()
        
        if success:
            if self.record_info != None:
                self.record_info.new_channel_count(self.selected_device.channel_count)
            
            if self.selected_device.is_running():
                self.__init_record_info()
                self.record_info.restart()
                self.tick_selected_device()

        return success
        
    def get_selected_device_description(self):
        """
        Returns current device description.
        """
        if self.selected_device != None:
            return self.selected_device.description
        return None
        
    def get_selected_device_state(self):
        """
        Returns current device state.
        """
        if self.selected_device is None:
            return DeviceState.nonexistent
        return self.selected_device.state
        
    def set_log_selected_device(self, enabled:bool):
        """
        Activates/Deactivates logging for selected device.
        """
        if self.selected_device is not None:
            self.selected_device.setLog(enabled)
            return enabled
        return False
        
    def get_log_selected_device(self):
        """
        Returns current state of log for selected device.
        """
        return self.selected_device._log
        
    def get_selected_device_properties(self):
        """
        Returns properties of selected device.
        """
        return self.selected_device.properties
        
    def is_active_snapshot_live(self):
        return self.active_snapshot == True or (self.active_snapshot is None and self.record_info.events is not None)
        
    def get_record_info(self):
        """
        Getter method for record info. Returns None if not available.
        """
        return self.record_info
        
    def new_snapshot(self, name:str=None):
        """
        Append new snapshot to snapshots list.
        
        Parameters:
            name: Label of the snapshot, defaults to current date and time.
        """
        snapshot = self.record_info.get_snapshot()
        snapshot.set_name(name)
        self.snapshots.append(snapshot)
        self.__backup_snapshots()
        
        self.callbacks_snapshots_changed.call()
        return True
        
    def remove_snapshot_by_id(self, _id:int):
        """
        Remove a snapshot from snapshots list.
        """
        snapshots = self.get_snapshots()
        if _id >= len(snapshots):
            print("Warning: Trying to remove a snapshot that is not available. " +
                  "Id:", _id, "Length of snapshots:", len(snapshots))
            return
        snapshot = snapshots[_id]

        if self.active_snapshot is snapshot:
            self.active_snapshot = True
        self.snapshots.remove(snapshot)
        if snapshot in self.visible_snapshots:
            self.visible_snapshots.remove(snapshot)
        
        self.__backup_snapshots()
        self.callbacks_snapshots_changed.call()
        
    def remove_all_snapshots(self):
        """
        Remove all snapshots from snapshots list.
        """
        self.active_snapshot = True
        self.snapshots.clear()
        self.visible_snapshots.clear()
        
        self.__backup_snapshots()
        self.callbacks_snapshots_changed.call()
        
    def set_active_snapshot_id(self, id:int):
        """
        Sets the active snapshot by id.
        """
        if id == -2:
            self.active_snapshot = True
        else:
            self.active_snapshot = self.snapshots[id]
    
    def toggle_visibility_snapshot_by_id(self, _id:int):
        snapshots = self.get_snapshots()
        if _id >= len(snapshots):
            print("Warning: Trying to toggle the visibility of a snapshot " +
                  "that is not available. Id:", _id, "Length of snapshots:", 
                  len(snapshots))
            return
        snapshot = snapshots[_id]

        if snapshot in self.visible_snapshots:
            self.visible_snapshots.remove(snapshot)
        else:
            self.visible_snapshots.append(snapshot)
        
        self.callbacks_snapshots_changed.call()
        
    def get_visibility_snapshot(self, snapshot):
        if snapshot not in self.visible_snapshots:
            return False
        
        return self.visible_snapshots.index(snapshot)+1
        
    def get_active_snapshot(self):
        """
        Returns active snapshot or live if no active snapshot available.
        """
        if self.is_active_snapshot_live():
            return self.record_info
        else:
            return self.active_snapshot
            
    def get_snapshots(self):
        """
        Get Snapshots.
        """
        self.__make_snapshot_names_unique()
        return self.snapshots
        
    def get_fit_info(self):
        """
        Get Fit Info. Returns None if not available.
        """
        return self.fit_info
    
    def get_visible_snapshots(self):
        """
        Get visible snapshots.
        """
        return self.visible_snapshots
        
    def create_fit_info(self, fitfunction, region, snapshot, fitcounts):
        """
        Creates Fit Info.
        """
        self.fit_info = FitInfo(fitfunction, region, snapshot, fitcounts)
        
    def unset_fit_info(self):
        """
        Unsets fit info to None.
        """
        self.fit_info = None
        
    def set_last_region(self, region):
        """
        Set last region.
        """
        self.last_region = region
        
    def get_last_region(self):
        """
        Get last region.
        """
        return self.last_region

    def __backup_record_info(self):
        if self.faultguard_data != None:
            self.faultguard_data["record_info"] = self.record_info
    
    def __backup_snapshots(self):
        snapshots = self.get_snapshots()
        if self.faultguard_data != None:
            if "snapshot_count" in self.faultguard_data:
                old_count = self.faultguard_data["snapshot_count"]
            else:
                old_count = 0
            new_count = len(snapshots)
            self.faultguard_data["snapshot_count"] = new_count

            # Remove unused entries
            for i in range(new_count, old_count):
                del self.faultguard_data[i]
            
            # Insert current data
            for i, snap in enumerate(snapshots):
                self.faultguard_data[i] = snap

    def __make_snapshot_names_unique(self):
        namelist = []
        for snapshot in self.snapshots:
            name = snapshot.get_name()
            unique_name_found = False
            name_prefix_id = 0
            while not unique_name_found:
                unique_name_found = True
                tempname = name
                if name_prefix_id > 0:
                    tempname = str(name_prefix_id) + " " + name
                for each in namelist:
                    if tempname == each:
                        name_prefix_id = name_prefix_id + 1
                        unique_name_found = False
            if name_prefix_id > 0:
                name = str(name_prefix_id) + " " + name
                snapshot.set_name(name)
            namelist.append(name)
