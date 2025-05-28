# Adding unlisted devices

This software automatically lists all devices that it can access. Under different operating systems, different preparations have to be done to connect a device. Some devices may require additional preparation steps that are further explained.

## Operating Systems

### Linux

Under Linux, you will need to set permission to access your USB MCA. How this is done depends on your specific distribution. On the debian-based Kubuntu the following worked:

Add a file /etc/udev/rules.d/50-imcar.rules including the following content (vendor and product ids are listed in the table below).

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0547", ATTRS{idProduct}=="1002", MODE="0666"
```

Then, run the following two commands:

```
sudo udevadm control --reload
sudo udevadm trigger
```

For further information see e.g. <https://stackoverflow.com/a/31994168>. Note that you have to use the MCA specific product and vendor ids that can be found in the README.md tab or using 'lsusb'.

### Windows

Under Windows, every accessable USB device needs a driver. Dependent on your system configuration, even for each USB port-device combination a driver has to be installed. You therefore need to install a minimalistic driver. This is most conveniently done by plugging the device in the USB port of your choise and using Zadig to install **"libusb-win32"**: <https://zadig.akeo.ie>
