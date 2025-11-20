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
- **Linux**: Custom Docker image built from `.github/Dockerfile.ubuntu20.04` (Ubuntu 20.04 base with Python 3.10 and all XCB dependencies pre-installed)
- **Windows**: windows-latest runners with Python 3.10

### Building with Docker (Linux)

For reproducible builds matching the CI environment:

```bash
# Build the Docker image
docker build -t imcar-builder:ubuntu20.04 -f .github/Dockerfile.ubuntu20.04 .

# Build the executable
docker run --rm -v $(pwd):/workspace -w /workspace imcar-builder:ubuntu20.04 bash -c "
  python3.10 -m pip install pyinstaller && \
  python3.10 -m pip install . && \
  cd pyinstaller && \
  python3.10 -m PyInstaller imcar.spec
"
```

The executable will be created in `pyinstaller/dist/imcar/`.

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
