import time
import subprocess
from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara

lab = Lab("kathara network scenario")

pc1 = lab.new_machine("pc1")
pc2 = lab.new_machine("pc2")

lab.connect_machine_to_link(pc1.name, "A")
lab.connect_machine_to_link(pc2.name, "A")

print("🚀 Deploying Lab...")
Kathara.get_instance().deploy_lab(lab)

print("\n✅ Simulation running. Press Enter to stop and clean up.")
_ = input()

Kathara.get_instance().undeploy_lab(lab.hash)
