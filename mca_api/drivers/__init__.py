# Statically installed drivers
import mca_api.drivers.caen_n957
import mca_api.drivers.software_devices

# Dynamically installed drivers
from mca_api.utils import user_data_dir

import os
import sys
import glob

import importlib.util
import sys
driver_path = os.path.join(user_data_dir("imcar"), "drivers")
modules = glob.glob(os.path.join(driver_path, "*.py"))
sys.path.append(driver_path)

for module_script in modules:
    module_name = "mca_api.drivers.external." + module_script.split("/")[-1][:-3]
    spec = importlib.util.spec_from_file_location(module_name, module_script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
