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

# importing README as recommended in https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    # Metadata
    name='imcar',
    version='1.0.4',
    author='2xB',
    author_email='2xB.coding@uni-muenster.de',
    long_description=long_description,
    long_description_content_type='text/markdown',
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
