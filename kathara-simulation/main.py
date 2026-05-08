# ignore annoying warning
import warnings

warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara
import importlib

lab = Lab("carote affettate")

controller = lab.new_machine("controller", image="kathara/ryu")

lab.connect_machine_to_link(controller.name, "A")

lab.create_startup_file_from_path(controller, "controller-startup.sh")

controller_address = "10.0.0.1/16"
controller.add_meta("env", f"CONTROLLER_ADDRESS={controller_address}")
controller.add_meta("bridged", "true")

lab_specs = importlib.import_module("labs.lab1_spec")

for i in range(lab_specs.N_HOST):
    host = lab.new_machine(f"host{i}", image="kathara/base")

    for link in lab_specs.host_connections(i):
        lab.connect_machine_to_link(host.name, link)

    lab.create_startup_file_from_path(host, "host-startup.sh")

    device_address = f"10.0.1.{i + 1}/16"
    host.add_meta("env", f"DEVICE_ADDRESS={device_address}")
    host.add_meta("env", f"CONTROLLER_ADDRESS={controller_address}")

for i in range(lab_specs.N_SWITCH):
    switch = lab.new_machine(f"switch{i}", image="kathara/sdn")

    for link in lab_specs.switch_connections(i):
        lab.connect_machine_to_link(switch.name, link)

    lab.create_startup_file_from_path(switch, "switch-startup.sh")

    device_address = f"10.0.2.{i + 1}/16"
    switch.add_meta("env", f"DEVICE_ADDRESS={device_address}")
    switch.add_meta("env", f"CONTROLLER_ADDRESS={controller_address}")
    
print("Deploying Lab...")
Kathara.get_instance().deploy_lab(lab)

print("Simulation running. Press Enter to stop and clean up.")
_ = input()

Kathara.get_instance().undeploy_lab(lab.hash)
