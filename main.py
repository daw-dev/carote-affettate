from Kathara.model.Lab import Lab
from Kathara.manager.Kathara import Kathara

lab = Lab("kathara network scenario")

pc1 = lab.new_machine("pc1")
pc2 = lab.new_machine("pc2")

lab.connect_machine_to_link(pc1.name, "A")
lab.connect_machine_to_link(pc2.name, "A")

Kathara.get_instance().deploy_lab(lab)

print(next(Kathara.get_instance().get_machines_stats(lab_name=lab.name)))
