# PyInstaller Executable Building

This directory contains the configuration for building standalone executables using PyInstaller.

## Prerequisites

### Linux
Before building, install the required XCB libraries:

```bash
sudo apt-get install -y \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-render-util0 \
  libxcb-xinerama0 \
  libxcb-xkb1 \
  libxcb-shape0 \
  libxkbcommon-x11-0
```

### Windows
No additional system dependencies required.

## Building

1. Install PyInstaller and imcar:
```bash
pip install pyinstaller
pip install .
```

2. Run the build script:
```bash
cd pyinstaller
pyinstaller imcar.spec
```

The executable will be created in `dist/imcar/`.

## Known Limitations

- **Linux**: The executable requires GLIBC 2.31 or newer (compatible with Ubuntu 20.04+, Debian 11+, and similar). For maximum compatibility, CI builds use Ubuntu 20.04 Docker containers to ensure GLIBC 2.31 compatibility. Systems with older GLIBC versions may encounter errors like `GLIBC_2.31' not found`.
- **Both platforms**: The executable bundles all dependencies, resulting in large file sizes (100-200MB).

## CI/CD Build Process

The GitHub Actions workflows build executables using:
- **Linux**: Ubuntu 20.04 Docker container on ubuntu-latest runners (maintains GLIBC 2.31 compatibility)
- **Windows**: windows-latest runners with Python 3.10

## Recommended Installation for End Users

For most users, pip installation is simpler and more reliable:

```bash
pip install imcar
```

Or install from source:

```bash
pip install --upgrade setuptools
python setup.py install
```

For more details, see the [main README](../README.md).
