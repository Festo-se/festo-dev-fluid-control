# Fluid Control

`festo-dev-fluid-control` is a Python library enabling control and programmatic operation of Festo's modular pipetting and dispensing modules.  


## Installation

### From Codebase

Navigate to the directory where the code is stored and, using pip, type in the following command:

```
pip install . -e
```

This will package the library locally and can be used as regular imports

### Official Packaged Releases

The lastest released version of this package can be found on the package registry of this project
Install using pip:

```
pip install festo-dev-fluid-control --index-url <private index URL with auth>
```

### From Git Repository

If installation via PyPI does not work, the festo-dev-fluid-control python driver source code can be installed directly from Github. Access the repository here: [festo-dev-fluid-control Github repo](https://github.com/Festo-se/festo-dev-fluid-control)

```
pip install git+https://github.com/Festo-se/festo-dev-fluid-control.git
```

Or as an editable dependency with a local copy of the source code: 

1. Clone the repository

```
git clone https://github.com/Festo-se/festo-dev-fluid-control.git <destination-directory>
```

2. Navigate to the clone destination directory

```
cd <destination>
```

3. Install with pip

```
pip install . -e
```

### Installation Within Virtual Environment

To install within a virtual environment, either create one by using the following command

```
python -m venv <virtual environment name> 
```

Or if one already exists, activate using:

```
<virtual environment name>\Scripts\activate.bat
```

Once activated, use the instructions from the [Release](#release) section to install the package

### Installation With uv By Astral

If your software environment utilizes uv or if you wish to begin using uv for everything python follow the instructions below.  
If uv is not already installed on the host PC or device, it can be installed following the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/), or by using pip or pipx.  
For pip:

```
pip install uv
```

For pipx:

```
pipx install uv
```

Once uv is installed or if uv is already installed on the host PC or device, use the following command to install the VAEM package into an existing virtual environment.

```
uv pip install festo-dev-fluid-control
```

To add the fluid control library to an existing project

```
uv add festo-dev-fluid-control
```

## Pymodbus Dependency
The `festo-dev-fluid-control` library uses the Festo `VAEM` and `PGVA` as its core dependencies for controlling the Festo subcomponents necessary to implement a fluidic control module. More information about the VAEM library can be found here, and it can be installed directly via `pip` with `pip install festo-vaem`. Similarly, the PGVA library can be found here, and it can be installed directly via `pip` with `pip install festo-pgva`.