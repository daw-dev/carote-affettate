# ignore annoying warning
import warnings

warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara
import networkx as nx
import json
import math
import random

G = nx.Graph()

CONTROLLER_ADDRESS = "10.0.0.254"

G.add_node(
        "controller",
        image="slicing-controller",
        startup="scripts/controller-startup.sh",
        volume="../slicing-controller/src|/controller|ro",
        device_address=CONTROLLER_ADDRESS,
    )

for i in range(1, 5):
    G.add_node(
            f"host{i}",
            image="kathara/base",
            startup="scripts/host-startup.sh",
            volume="../slicing-host/src|/host|ro",
            device_address=f"10.{i}.0.2",
            default_gateway=f"10.{i}.0.1",
            mac_address=f"00:00:00:00:00:{i:02x}",
        )

for i in range(1, 5):
    G.add_node(
            f"switch{i}",
            image="kathara/sdn",
            startup="scripts/switch-startup.sh",
            device_address=f"10.{i}.0.1",
            hidden_address=f"10.0.0.{i}",
            connected_host=f"10.{i}.0.2",
            switch_id=i,
            port_count=0,
        )
    G.add_edge(f"switch{i}", "controller")
    G.add_edge(f"switch{i}", f"host{i}")

for i in range(1, 5):
    for j in range(1, i):
        G.add_edge(f"switch{i}", f"switch{j}", capacity=random.randrange(5, 25))

def switch_port(node):
    if not "port_count" in G.nodes[node]:
        return
    
    G.nodes[node]["port_count"] += 1
    return G.nodes[node]["port_count"] - 1

for u, v in G.edges():
    u_if = switch_port(u)
    v_if = switch_port(v)
    ports = {}
    if u_if:
        ports[u] = u_if
    if v_if:
        ports[v] = v_if

    G.edges[u, v]["ports"] = ports

# edges_list = list(G.edges())
# switch_count = {f"switch{i}": 0 for i in range(1, 5)}  # conta le interfacce già usate
# switch_links = {f"switch{i}": [] for i in range(1, 5)}

# for u, v in edges_list:
#     # Connessioni controller
#     if u == "controller" or v == "controller":
#         sw = v if u == "controller" else u
#         if sw in switch_count:
#             switch_count[sw] += 1
#         continue

#     # Connessioni host
#     if u.startswith("host") or v.startswith("host"):
#         sw = v if u.startswith("host") else u
#         if sw in switch_count:
#             switch_count[sw] += 1
#         continue

#         # Connessioni switch-switch
#     if u in switch_count and v in switch_count:
#         cap = G[u][v]['capacity']          # capacità dell'arco
#         iface_u = f"eth{switch_count[u]}"  # prossima interfaccia libera su u
#         iface_v = f"eth{switch_count[v]}"  # prossima interfaccia libera su v
#         switch_links[u].append((iface_u, cap))
#         switch_links[v].append((iface_v, cap))
#         switch_count[u] += 1
#         switch_count[v] += 1

# switch_links_env = {}

# for sw in switch_links:
#     if switch_links[sw]:
#         link_str = ",".join([f"{iface}:{cap}" for iface, cap in switch_links[sw]])
#         switch_links_env[sw] = link_str
#     else:
#         switch_links_env[sw] = ""

topology_json = json.dumps(nx.node_link_data(G), indent=4)

print(topology_json)

lab = Lab("carote affettate")

def switch_capacities(switch_name):
    capacities = {}
    for _, _, data in G.edges(switch_name, data=True):
        if "capacity" in data:
            interface = f"eth{data["ports"][switch_name]}"
            capacities[interface] = data["capacity"]
    
    return ",".join([f"{iface}:{cap}" for iface, cap in capacities.items()])

for node, data in G.nodes(data=True):
    machine = lab.new_machine(node, image=data["image"])
    lab.create_startup_file_from_path(machine, data["startup"])
    if "volume" in data:
        machine.add_meta("volume", data["volume"])
    machine.add_meta("env", f"CONTROLLER_ADDRESS={CONTROLLER_ADDRESS}")
    machine.add_meta("env", f"DEVICE_ADDRESS={data["device_address"]}")
    machine.add_meta("env", f"NAME={node}")
    if "switch_id" in data:
        machine.add_meta("env", f"SWITCH_ID={data["switch_id"]}")
        machine.add_meta("env", f"HIDDEN_IP={data["hidden_address"]}")
        machine.add_meta("env", f"CONNECTED_HOST={data["connected_host"]}")
        caps = switch_capacities(node)
        machine.add_meta("env", f"SWITCH_CAPACITIES={caps}")
    if "default_gateway" in data:
        machine.add_meta("env", f"DEFAULT_GATEWAY={data["default_gateway"]}")

lab.machines["controller"].create_file_from_string(topology_json, "/topology.json")

lab.connect_machine_to_link("controller", "CONTROLLER")

for u, v in G.edges():
    if u == "controller":
        lab.connect_machine_to_link(v, "CONTROLLER")
        continue
    if v == "controller":
        lab.connect_machine_to_link(u, "CONTROLLER")
        continue

    lab.connect_machine_to_link(u, f"{u}__to__{v}", mac_address=G.nodes[u].get("mac_address"))
    lab.connect_machine_to_link(v, f"{u}__to__{v}", mac_address=G.nodes[v].get("mac_address"))

wireshark = lab.new_machine(
        "wireshark",
        image="lscr.io/linuxserver/wireshark",
        port="3000:3000",
        # bridged=True,
    )

lab.connect_machine_obj_to_link(wireshark, "host2__to__switch2")

print("Deploying Lab...")
Kathara.get_instance().deploy_lab(lab)

print("Simulation running. Press Enter to stop and clean up.")
_ = input()

Kathara.get_instance().undeploy_lab(lab.hash)
