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

### 2. Run the simulation

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

#### 2.5. To stop the simulation just press enter.

If for some reason you closed the program without pressing enter, `kathara wipe` can still forcibly stop the simulation.

### 4. Connect to a device

To connect to a specific device, you have to run bash on the relative container, to make it easier,
the repository provides some simple helper commands. To activate them:

```nushell
source helpers/konnect.nu
```

```bash
source helpers/konnect.sh
```

And then you can just run:
```bash
konnect <device-name>
```

## The goal

## Our solution


