# ignore annoying warning
import warnings

warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara
import importlib
import ipaddress

network = ipaddress.IPv4Network("10.0.0.0/16")
connection_port = "6653"
ip_generator = network.hosts()

def new_ip():
    # return f"{next(ip_generator)}/{network.prefixlen}"
    # return f"{next(ip_generator)}:{connection_port}"
    return f"{next(ip_generator)}"


lab = Lab("carote affettate")

controller = lab.new_machine("controller", image="slicing-controller")

lab.create_startup_file_from_path(controller, "scripts/controller-startup.sh")

controller_address = new_ip()
# For controller address/16 needed
controller.add_meta("env", f"CONTROLLER_ADDRESS={controller_address}/{network.prefixlen}")
controller.add_meta("bridged", "true")
controller.add_meta("volume", "../slicing-controller/src|/controller|ro")
lab.connect_machine_obj_to_link(controller, "CONTROLLER")

lab_specs = importlib.import_module("labs.lab1_spec")


for i in range(lab_specs.N_SWITCH):
    switch = lab.new_machine(f"switch{i}", image="kathara/sdn")

    ips = []

    lab.connect_machine_obj_to_link(switch, f"CONTROLLER")
    ips.append(new_ip())

    for link in lab_specs.switch_connections(i):
        lab.connect_machine_to_link(switch.name, link)
        ips.append(new_ip())

    lab.create_startup_file_from_path(switch, "scripts/switch-startup.sh")

    interfaces = " ".join(map(lambda i: f"eth{i}={ips[i]}/{network.prefixlen}", range(len(ips))))
    switch.add_meta("env", f"DEVICE_INTERFACES={interfaces}")
    # For switches address:6653 needed
    switch.add_meta("env", f"CONTROLLER_ADDRESS={controller_address}:{connection_port}")


for i in range(lab_specs.N_HOST):
    host = lab.new_machine(f"host{i}", image="kathara/base")

    ips = []

# TODO: un host ha un solo indirizzo ip
    for link in lab_specs.host_connections(i):
        lab.connect_machine_obj_to_link(host, link)
        ips.append(new_ip())

    lab.create_startup_file_from_path(host, "scripts/host-startup.sh")
    host.add_meta("volume", "../slicing-host/src|/host|ro")

    interfaces = " ".join(map(lambda i: f"eth{i}={ips[i]}/{network.prefixlen}", range(len(ips))))
    host.add_meta("env", f"DEVICE_INTERFACES={interfaces}")
    host.add_meta("env", f"CONTROLLER_ADDRESS={controller_address}:{connection_port}")

print("Deploying Lab...")
Kathara.get_instance().deploy_lab(lab)

print("Simulation running. Press Enter to stop and clean up.")
_ = input()

Kathara.get_instance().undeploy_lab(lab.hash)
