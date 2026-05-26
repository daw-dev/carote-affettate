# ignore annoying warning
from textwrap import indent
import warnings

warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara
import ipaddress
import networkx as nx
import json

network = ipaddress.IPv4Network("10.0.0.0/16")
connection_port = "6653"
ip_generator = network.hosts()

def new_ip():
    # return f"{next(ip_generator)}/{network.prefixlen}"
    # return f"{next(ip_generator)}:{connection_port}"
    return f"{next(ip_generator)}"

G = nx.Graph()

CONTROLLER_ADDRESS = new_ip()

G.add_node(
        "controller",
        image="slicing-controller",
        interfaces={"eth0": CONTROLLER_ADDRESS},
        startup="scripts/controller-startup.sh",
        volume="../slicing-controller/src|/controller|ro",
    )

for i in range(4):
    G.add_node(
            f"host{i}",
            image="kathara/base",
            interfaces={},
            startup="scripts/host-startup.sh",
            volume="../slicing-host/src|/host|ro",
        )

for i in range(4):
    G.add_node(
            f"switch{i}",
            image="kathara/sdn",
            interfaces={},
            startup="scripts/switch-startup.sh",
        )
    G.add_edge(f"switch{i}", "controller", weight=5)
    G.add_edge(f"switch{i}", f"host{i}", weight=5)

for i in range(4):
    for j in range(4):
        if i == j:
            continue
        G.add_edge(f"switch{i}", f"switch{j}", weight=5)

def add_ip_to_node(node):
    if node == "controller":
        return
    new_if = len(G.nodes[node]["interfaces"])
    G.nodes[node]["interfaces"][f"eth{new_if}"] = new_ip()

for u, v in G.edges():
    add_ip_to_node(u)
    add_ip_to_node(v)

topology_json = json.dumps(nx.node_link_data(G), indent=4)

print(topology_json)

lab = Lab("carote affettate")


for node, data in G.nodes(data=True):
    machine = lab.new_machine(node, image=data["image"])
    lab.create_startup_file_from_path(machine, data["startup"])
    machine.add_meta("env", f"CONTROLLER_ADDRESS={CONTROLLER_ADDRESS}")
    if "volume" in data:
        machine.add_meta("volume", data["volume"])
    interfaces = " ".join(f"{interface}={ip}" for interface, ip in data["interfaces"].items())
    machine.add_meta("env", f"DEVICE_INTERFACES={interfaces}")

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
