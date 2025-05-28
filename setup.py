import sys
from setuptools import setup, __version__
from distutils.version import StrictVersion


if StrictVersion(__version__) < StrictVersion('38.2.0'):
    print('A setuptools version >= 38.2.0 is required to install this application. You should consider upgrading via the "pip3 install --upgrade setuptools" command.')
    sys.exit(1)

requirements = [
    "numpy",
    "matplotlib",
    "scipy",
    "uncertainties",
    "pyusb",
    "PyQt5<=5.15.5",
    "pyqtgraph==0.13.1",
    "markdown2",
    "faultguard>=1.1.1",
    ]

setup(
    # Metadata
    name='imcar',
    version='1.0.0',
    author='Benedikt Bieringer',
    author_email='2xB.coding@wwu.de',
    # Package info
    packages=['imcar', 'imcar.app', 'imcar.gui', 'mca_api', 'mca_api.drivers'],
    install_requires=requirements,
    include_package_data=True,

    entry_points = {
        'console_scripts': [
            'imcar = imcar.app.start:main',
        ]
    }
)
