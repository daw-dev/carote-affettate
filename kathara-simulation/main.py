from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara

print("Loading scripts...")

controller_startup = open("controller-startup.sh").read()
host_startup = open("host-startup.sh").read()
switch_startup = open("switch-startup.sh").read()

lab = Lab("carote affettate")

controller = lab.new_machine("controller", image="kathara/ryu")

lab.connect_machine_to_link(controller.name, "A")

lab.create_startup_file_from_path(controller, "controller-startup.sh")

controller_address = "10.0.1.1/24"
controller.add_meta("env", f"CONTROLLER_ADDRESS={controller_address}")

for i in range(5):
    host = lab.new_machine(f"host{i}", image="kathara/base")

    lab.connect_machine_to_link(host.name, "A")

    lab.create_startup_file_from_path(host, "host-startup.sh")

    device_address = f"10.0.1.{i + 10}/24"
    host.add_meta("env", f"DEVICE_ADDRESS={device_address}")
    
print("Deploying Lab...")
Kathara.get_instance().deploy_lab(lab)

print("Simulation running. Press Enter to stop and clean up.")
_ = input()

Kathara.get_instance().undeploy_lab(lab.hash)
