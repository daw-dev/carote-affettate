# ignore annoying warning
import warnings

warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara
import ipaddress
import networkx as nx
import json

network = ipaddress.IPv4Network("10.0.0.0/16")
hidden_network = ipaddress.IPv4Network("10.1.0.0/16")
ip_generator = network.hosts()
hidden_ip_generator = hidden_network.hosts()

G = nx.Graph()

CONTROLLER_ADDRESS = str(next(hidden_ip_generator))

G.add_node(
        "controller",
        image="slicing-controller",
        startup="scripts/controller-startup.sh",
        volume="../slicing-controller/src|/controller|ro",
        device_address=CONTROLLER_ADDRESS,
    )

for i in range(4):
    G.add_node(
            f"host{i}",
            image="kathara/base",
            startup="scripts/host-startup.sh",
            volume="../slicing-host/src|/host|ro",
            device_address=str(next(ip_generator)),
        )

for i in range(4):
    G.add_node(
            f"switch{i}",
            image="kathara/sdn",
            startup="scripts/switch-startup.sh",
            device_address=str(next(ip_generator)),
            hidden_address=str(next(hidden_ip_generator)),
            switch_id=i + 1,
        )
    G.add_edge(f"switch{i}", "controller", capacity=5)
    G.add_edge(f"switch{i}", f"host{i}", capacity=5)

for i in range(4):
    for j in range(4):
        if i == j:
            continue
        G.add_edge(f"switch{i}", f"switch{j}", capacity=5)

def add_ip_to_node(node):
    if node == "controller":
        return
    if "port_count" in G.nodes[node]:
        G.nodes[node]["port_count"] += 1
        return G.nodes[node]["port_count"]
    else:
        G.nodes[node]["port_count"] = 1
        return G.nodes[node]["port_count"]

for u, v in G.edges():
    u_if = add_ip_to_node(u)
    v_if = add_ip_to_node(v)
    if u_if:
        G.edges[u, v]["source_port"] = u_if
    if v_if:
        G.edges[u, v]["target_port"] = v_if

topology_json = json.dumps(nx.node_link_data(G), indent=4)

print(topology_json)

lab = Lab("carote affettate")

for node, data in G.nodes(data=True):
    machine = lab.new_machine(node, image=data["image"])
    lab.create_startup_file_from_path(machine, data["startup"])
    machine.add_meta("env", f"CONTROLLER_ADDRESS={CONTROLLER_ADDRESS}")
    if "volume" in data:
        machine.add_meta("volume", data["volume"])
    machine.add_meta("env", f"DEVICE_ADDRESS={data["device_address"]}")
    machine.add_meta("env", f"NAME={node}")
    if "switch_id" in data:
        machine.add_meta("env", f"SWITCH_ID={data["switch_id"]}")
        machine.add_meta("env", f"HIDDEN_IP={data["hidden_address"]}")

lab.machines["controller"].create_file_from_string(topology_json, "/topology.json")

lab.connect_machine_to_link("controller", "CONTROLLER")

for u, v in G.edges():
    if u == "controller":
        lab.connect_machine_to_link(v, "CONTROLLER")
        continue
    if v == "controller":
        lab.connect_machine_to_link(u, "CONTROLLER")
        continue

    lab.connect_machine_to_link(u, f"{u}__to__{v}")
    lab.connect_machine_to_link(v, f"{u}__to__{v}")

print("Deploying Lab...")
Kathara.get_instance().deploy_lab(lab)

print("Simulation running. Press Enter to stop and clean up.")
_ = input()

Kathara.get_instance().undeploy_lab(lab.hash)
