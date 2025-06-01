infos = []

test_infos = []

def register_device(dev, test=False):
    if test:
        test_infos.append(dev)
    else:
        infos.append(dev)

def all_drivers(tests=False):
    """Returns all found device infos."""
    import mca_api.drivers

    devices = list(infos)
    if tests:
        devices.extend(test_infos)
    
    return devices
