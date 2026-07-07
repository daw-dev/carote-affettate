# Sliced Carrots

## Usage

### 1. Build the Docker images (Platform Independent)

**This step has to be done only the first time**

1. Build the controller image:

```bash
docker build -t slicing-controller slicing-controller
```

2. Build the host image:

```bash
docker build -t slicing-host slicing-host
```

Or through one of the build scripts `build.sh`, `build.nu`, `build.ps1` or `build.bat`

### 2. Running the simulation

#### 2.1. Cd into the kathara simulation 

```bash
cd kathara-simulation
```

#### 2.2. Sync the python virtual environment:

```bash
uv sync
```

#### 2.3. Activate the python virtual environment:
On Linux (bash):
```bash
./.venv/bin/activate
```
On Linux (nushell):
```nushell
overlay use .venv/bin/activate.nu
```
On Windows (PowerShell):
```pwsh
.\.venv\Scripts\activate.ps1
```

#### 2.4. Start the simulation

```bash
python start-simulation.py
```

#### 2.5. Stopping the simulation

To stop the simulation just press enter.

If for some reason you closed the program without pressing enter, `kathara wipe` can still forcibly stop the simulation.

### 3. Connecting to a device

To connect to a specific device, you have to run bash on the relative container, to make it easier,
the repository provides some simple helper commands. To activate them:

In nushell:
```nushell
source helpers/konnect.nu
```

In bash:
```bash
source helpers/konnect.sh
```

In PowerShell:
```pwsh
. .\helpers\konnect.ps1
```

And then you can just run:
```bash
konnect <device-name>
```

### 4. What to do in the simulation

To play around with the simulation, you should connect to a **host** (use `konnect host[number]`).
At first, the host will only be able to communicate with the controller. Through this connection, the host
can manage slices that enable to communicate with the other hosts.
To do so, you can run the following commands:

To request a slice:
```bash
request-slice [source] destination bandwidth
```
If no source is provided, the requesting host is assumed

To update a slice:
```bash
update-slice [source] destination bandwidth
```
If no source is provided, the requesting host is assumed

To remove a slice:
```bash
remove-slice [source] [destination]
```
If only one argument is provided, the slice to be removed is the one between the requesting host and the 
specified host.
If no argument is provided, all the slices for which the requesting host is the source are removed.

To get information about an active slice:
```bash
slice-info [source] destination
```
If no source is provided, the requesting host is assumed

## The goal

## Our solution


