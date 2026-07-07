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
request-slice [source] <destination> <bandwidth>
```
If no source is provided, the requesting host is assumed

To update a slice:
```bash
update-slice [source] <destination> <bandwidth>
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
slice-info [source] <destination>
```
If no source is provided, the requesting host is assumed

Once a slice is reserved between two hosts, they can communicate using all the requested bandwidth,
you can test this using:
```bash
ping <other-host>
```

To perform a more interesting test, you can also use: 
```bash
run-iperf --ip <other-host> [--bitrate <bitrate>] [--t <duration>]
```

## The goal

The main goal of the project is to simulate a sdn controller that allows for dynamic slices.

We also decided to implement the sdn controller as a in-band controller: meaning that the controller
itself is a node in the network like the others. Furthermore, the slices are indirectly managed by the 
hosts by simply sending http requests to the controller via the network.

Slices can be created, updated and destroyed.

## Our solution

<!-- qualcosa sulla simulazione -->

To make host-controller communication possible, the network structure had to be laid out in a specific manner:
- Every host is directly connected to exactly one switch with whom it shares a specific sub-network.
    - host{i} is connected to switch{i} inside the network 10.{i}.0.0/16
    - switch{i} is the default gateway of host{i}
- Every switch is directly connected to the controller on the 10.254.0.0/16 sub-network.
    - The virtual openflow switch br0 of switch{i} is assigned to the 10.254.0.{i} address
- Every switch performs Network Address Translation (from 10.{i}.0.1 to 10.254.0.{i}) to allow communication
    between host and controller 

The controller loads the topology from the static .json file so that it is aware of every information of the graph.
It also runs a http rest daemon so that it listens for http requests. When a slice request arrives, it uses the saved 
information about the graph to figure out a path to allow the communication between the two hosts with the desired 
bandwidth (if any), sends new rules to the switches, it updates the information in the graph and notifies the 
requesting host about the result of the operation. When a slice gets updated or removed, the same rules are updated 
or removed accordingly.

To achieve the communication, two kinds of MODs are sent to the switches:

FlowMOD:
It matches the source ip and destination ip of the ip packet and it forwards the packet to a specific port. It also 
includes information for the MeterMODs (explained later).
The last switch of the path also has the responsibility of changing the layer 2 addresses of the packet so that the 
destination host doesn't discard the incoming package.

MeterMOD:
It enforces a maximum bandwidth in a slice by dropping every packet that exceeds such limit. The two directions of 
the slice share the same meter, so that the maximum bandwidth is calculated assuming data flow in both directions 
simultaneously.

Every host silently runs a daemon that awaits for TCP connections and, when using the run-iperf command, it runs a 
iperf server instance to allow the requesting host to run the test. Such test can be used to show that, in fact, 
on the reserved slice it's not possible to exceed the set limit.

The daemon is scripted in such way that in future implementations other kinds of connections may be requested.
