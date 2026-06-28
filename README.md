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
python main.py
```

#### 2.5. Stopping the simulation

To stop the simulation just press enter.

If for some reason you closed the program without pressing enter, `kathara wipe` can still forcibly stop the simulation.

### 4. Connecting to a device

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

### 5. What to do in the simulation

To play around with the simulation, you should connect to a **host** (use `konnect host[number]`), then if you take a look
at the `/host/` folder, you'll see that there are some scripts to play around with.

The main one is `/host/request-slice.py` that is used to request a slice to the controller. The usage is ...

The other ones are small applications like `/host/web-server.py`, `/host/web-client.py`, ...

```bash
curl --json '{"src": "host1", "dst": "host2", "bandwidth": 2}' $CONTROLLER_ADDRESS:8080/slice/request
curl --json '{"src": "host2", "dst": "host1", "bandwidth": 2}' $CONTROLLER_ADDRESS:8080/slice/request
curl -X DELETE --json '{"src": "host1", "dst": "host2"}' $CONTROLLER_ADDRESS:8080/slice/request
```

### _BONUS:_ How to personalize the network



## The goal

## Our solution


