# Sliced Carrots 🥕
A dynamic SDN slicing simulation built on Kathara and Ryu.

---

## 🚀 Getting Started

### 1. Build the Docker Image
Only the controller image needs to be built. The host containers run the base Kathara image and dynamically mount the host source files.

**Build the controller image:**
```bash
docker build -t slicing-controller slicing-controller
```
*(Or use one of the provided platform scripts: `build.sh`, `build.nu`, `build.ps1`, or `build.bat`.)*

### 2. Running the Simulation
1. **Navigate to the simulation directory:**
   ```bash
   cd kathara-simulation
   ```
2. **Synchronize dependencies** (using `uv`):
   ```bash
   uv sync
   ```
3. **Activate the virtual environment:**
   * **Linux/macOS (bash/zsh):**
     ```bash
     .venv/bin/activate
     ```
   * **Linux/macOS (Nushell):**
     ```nushell
     overlay use .venv/bin/activate.nu
     ```
   * **Windows (PowerShell):**
     ```powershell
     . .venv\Scripts\Activate.ps1
     ```
4. **Start the simulation:**
   ```bash
   python start-simulation.py
   ```
5. **Stop the simulation:**
   Press **Enter** in the terminal running the Python script. If terminated unexpectedly, clean up using:
   ```bash
   kathara wipe
   ```

### 3. Connecting to a Device
Helper scripts are provided to easily start a bash shell inside the simulation containers:

| Shell | Command to Activate Helpers | Command to Connect |
| :--- | :--- | :--- |
| **Bash** | `source helpers/konnect.sh` | `konnect <device-name>` |
| **Nushell** | `use helpers/konnect.nu *` | `konnect <device-name>` |
| **PowerShell** | `. .\helpers\konnect.ps1` | `konnect <device-name>` |

*Example:* `konnect host1`

---

## 🛠️ Interacting with the Simulation
Once connected to a **host** (e.g., `host1`), you can interact with the SDN controller using the following helper commands. 

> [!IMPORTANT]
> **Bandwidth Units:** Bandwidth values are specified in **kbps** (kilobits per second).
> 
> **Shifting Parameters:** The optional `[source]` parameter is positioned at the start. If omitted, the source defaults to the current host, shifting the argument positions.

### Slice Management Commands

| Command | Syntax (Implicit Source) | Syntax (Explicit Source) | Description |
| :--- | :--- | :--- | :--- |
| **Request Slice** | `request-slice <destination> <bandwidth>` | `request-slice <source> <destination> <bandwidth>` | Allocates a network slice with the specified bandwidth in **kbps**. |
| **Update Slice** | `update-slice <destination> <bandwidth>` | `update-slice <source> <destination> <bandwidth>` | Modifies the bandwidth allocation of an existing slice. |
| **Remove Slice** | `remove-slice [destination]` | `remove-slice <source> <destination>` | Removes the specified slice. If no arguments are passed, it removes all slices originating from the current host. |
| **Slice Info** | `slice-info <destination>` | `slice-info <source> <destination>` | Retrieves path and bandwidth details for an active slice. |

### Testing Connectivity and Bandwidth
Once a slice is created between two hosts, you can run tests to verify connectivity and bandwidth enforcement:

* **Basic Connectivity:**
  ```bash
  ping <other-host>
  ```
  *(Note: Hostname resolution is resolved dynamically by the controller's DNS server.)*
* **Bandwidth Test (iperf3):**
  ```bash
  run-iperf --ip <other-host> [--bitrate <bitrate>] [--time <duration>]
  ```
  * **`--ip`**: The hostname or IP address of the target host (e.g., `host2`).
  * **`--bitrate`**: Bitrate for the test (e.g., `100K`, `1M`). Default is `1M`.
  * **`--time`**: Duration of the test in seconds. Default is `10`.

---

## 🔍 Network Debugging (Wireshark)
The simulation deploys a web-accessible **Wireshark** container capturing traffic on the link between `host2` and `switch2`.
* **Access URL:** `http://localhost:3000`
* Use this to inspect OpenFlow control messages, ARP packets, NAT translation, and data traffic.

---

## 🎯 Project Architecture & Implementation Details

### The Goal
To simulate a Software-Defined Networking (SDN) controller that supports **dynamic slice provisioning**. 
The controller is **in-band**, meaning it resides within the network it controls. Hosts communicate with the controller by sending HTTP REST requests directly over the network to create, update, or destroy slices.

### Topology and Addressing
To enable host-to-controller communication without open paths between arbitrary hosts prior to slice creation:
1. **Host-to-Switch network:** Each host `host{i}` connects to its own switch `switch{i}` on a unique subnet: `10.{i}.0.0/16`.
2. **Switch-to-Controller network:** All switches connect to the controller on a shared management subnet: `10.254.0.0/16`.
3. **NAT Masquerading:** Each switch acts as the default gateway and performs Source NAT (masquerading) for its host. This allows any host to send HTTP requests to the controller (`10.0.0.254:8080`) while keeping hosts isolated from each other.
4. **Dynamic DNS:** The controller runs a `dnsmasq` server. Every host is configured to use the controller as its primary nameserver, allowing them to resolve names like `host2` dynamically.

### How Slices are Enforced
When a slice request is approved, the controller calculates the path using `networkx` and sends OpenFlow 1.3 rules to the switches:
* **FlowMODs:** Route traffic based on matching the source and destination IP. The final switch rewrites layer-2 MAC addresses to match the target host.
* **MeterMODs:** Enforce the maximum bandwidth limit. Both directions of a slice share the same meter to limit aggregate throughput.

### Custom iperf Test Implementation
To allow bandwidth testing, each host silently runs a custom daemon that listens for incoming TCP connections. When the `run-iperf` command is executed on the requesting host, it communicates with this remote daemon, which triggers an `iperf3` server instance on the target host. 

The client then runs an `iperf3` client to test the path. This test demonstrates that throughput on the reserved slice cannot exceed the configured limit. The daemon is designed in an extensible manner so that other types of connections or tests can be easily requested in the future.

