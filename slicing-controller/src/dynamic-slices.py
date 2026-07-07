import json
import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import subprocess
import os

api_instance_name = 'slicing_api_app'
DEFAULT_TOPOLOGY_PATH = '/topology.json'
DEFAULT_HOSTS_PATH = '/etc/hosts'

class DynamicSlices(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(DynamicSlices, self).__init__(*args, **kwargs)
        self.load_topology(DEFAULT_TOPOLOGY_PATH)
        self.configure_hosts_file(DEFAULT_HOSTS_PATH)
        
        wsgi = kwargs['wsgi']
        wsgi.register(DynamicSlicesApi, {api_instance_name: self})
        self.logger.info("Static Slicing Controller Ready.")
        self.datapaths = {}
        self.meter_ids = {}
        self.slices = {}

    def load_topology(self, filepath):
        try:
            with open(filepath, 'r') as f:
                graph_data = json.load(f)
                self.net = nx.node_link_graph(graph_data)
                print(self.net)
            self.logger.info("Topology graph loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load topology: {e}")

    def configure_hosts_file(self, filepath):
        try:
            with open(filepath, 'a') as f:
                for node, data in self.net.nodes(data=True):
                    address = data["device_address"]
                    f.write(f"{address} {node}\n")

                self.logger.info("DNS nodes written to hosts file")
                address = os.environ.get("DEVICE_ADDRESS")
                subprocess.Popen(["dnsmasq", f"--listen-address={address}", "--bind-interfaces"])
        except Exception as e:
            self.logger.error(f"Failed to write dns nodes: {e}")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        self.logger.info(f"Switch with id {ev.msg.datapath.id} asks for help")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[int(datapath.id)] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()

        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)

        datapath.send_msg(mod)

    def add_flow(self, datapath, priority, match, actions, bandwidth=None, meter_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if meter_id is not None:
            inst.append(parser.OFPInstructionMeter(meter_id))
        elif bandwidth is not None: 
            meter_id = self.meter_ids.get(datapath.id, 1)
            self.meter_ids[datapath.id] = meter_id + 1

            self.add_meter(datapath, meter_id, bandwidth)

            inst.append(parser.OFPInstructionMeter(meter_id))

        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)

        self.logger.info("Sending a FLOW_MOD to switch")

        datapath.send_msg(mod)

    def remove_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        mod = parser.OFPFlowMod(datapath=datapath, match=match, command=ofproto.OFPFC_DELETE, 
                                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY)
        self.logger.info("Deleting a path")
        datapath.send_msg(mod)

    def add_meter(self, datapath, meter_id, bandwidth, command=None):
        if command is None:
            command = datapath.ofproto.OFPMC_ADD
        parser = datapath.ofproto_parser
        bands = [parser.OFPMeterBandDrop(rate=bandwidth)]
        meter_mod = parser.OFPMeterMod(
            datapath=datapath,
            command=command,
            flags=datapath.ofproto.OFPMF_KBPS,
            meter_id=meter_id,
            bands=bands
        )
        datapath.send_msg(meter_mod)

    def remove_meter(self, datapath, meter_id):
        parser = datapath.ofproto_parser
        meter_mod = parser.OFPMeterMod(
            datapath=datapath,
            command=datapath.ofproto.OFPMC_DELETE,
            flags=datapath.ofproto.OFPMF_KBPS,
            meter_id=meter_id,
            bands=[]
        )
        datapath.send_msg(meter_mod)


    def add_path_flows(self, path, bandwidth, meters=None):
        src_ip = self.net.nodes[path[0]]["device_address"]
        dst_ip = self.net.nodes[path[-1]]["device_address"]

        self.logger.info(f"creating path {path} from {src_ip} to {dst_ip}")
        for i in range(1, len(path) - 1):
            current_node = path[i]
            switch_id = self.net.nodes[current_node].get("switch_id")
            
            if not switch_id:
                continue

            self.logger.info(f"sending flow to {switch_id}")
                
            prev_node = path[i-1]
            next_node = path[i+1]
            
            datapath = self.datapaths.get(switch_id)

            if not datapath:
                self.logger.warning(f"Switch {switch_id} is not connected to Ryu yet!")
                return False

            in_port = self.net.edges[prev_node, current_node]["ports"][current_node]
            out_port = self.net.edges[current_node, next_node]["ports"][current_node]

            if in_port is None or out_port is None:
                self.logger.error(f"Missing port link data for {current_node}")
                return False

            parser = datapath.ofproto_parser
            
            match = parser.OFPMatch(
                in_port=in_port,
                eth_type=0x0800,
                ipv4_src=src_ip,
                ipv4_dst=dst_ip
            )
            
            actions = []
            if i == len(path) - 2:
                switch_gateway_mac = datapath.ports[datapath.ofproto.OFPP_LOCAL].hw_addr
                actions.append(parser.OFPActionSetField(eth_src=switch_gateway_mac))
                actions.append(parser.OFPActionSetField(eth_dst=self.net.nodes[path[-1]]["mac_address"]))
            actions.append(parser.OFPActionOutput(out_port))
            
            if meters and switch_id in meters:
                self.add_flow(datapath, 100, match, actions, meter_id=meters[switch_id])
            else:
                self.add_flow(datapath, 100, match, actions, bandwidth=bandwidth)
            self.logger.info(f"Installed flow on {current_node}: in={in_port} -> out={out_port}")

        return True

    def remove_path_flows(self, path):
        src_ip = self.net.nodes[path[0]]["device_address"]
        dst_ip = self.net.nodes[path[-1]]["device_address"]

        self.logger.info(f"deleting path {path} from {src_ip} to {dst_ip}")
        for i in range(1, len(path) - 1):
            current_node = path[i]
            switch_id = self.net.nodes[current_node].get("switch_id")
            if not switch_id:
                continue

            self.logger.info(f"deleting flow to {switch_id}")
            
            datapath = self.datapaths.get(switch_id)

            if not datapath:
                self.logger.warning(f"Switch {switch_id} is not connected to Ryu yet!")
                continue

            parser = datapath.ofproto_parser
            
            match = parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=src_ip,
                ipv4_dst=dst_ip
            )

            self.remove_flow(datapath, match)
            self.logger.info(f"Deleting path on {current_node}")

    def capacity_filter(self, capacity):
        def enough_capacity(u, v):
            return "capacity" not in self.net.edges[u, v] or self.net.edges[u, v]["capacity"] >= capacity
        
        return enough_capacity

    def reserve_slice(self, src, dst, bandwidth):
        valid_links = nx.subgraph_view(self.net, filter_edge=self.capacity_filter(bandwidth))

        try:
            path = nx.shortest_path(valid_links, source=src, target=dst)

            meters = {}
            for i in range(1, len(path) - 1):
                current_node = path[i]
                switch_id = self.net.nodes[current_node].get("switch_id")
                if not switch_id:
                    continue
                datapath = self.datapaths.get(switch_id)
                if not datapath:
                    self.logger.warning(f"Switch {switch_id} is not connected to Ryu yet!")
                    return []
                
                meter_id = self.meter_ids.get(datapath.id, 1)
                self.meter_ids[datapath.id] = meter_id + 1
                meters[switch_id] = meter_id
                
                self.add_meter(datapath, meter_id, bandwidth)
                self.logger.info(f"Created shared meter {meter_id} on switch {switch_id} with rate {bandwidth}")

            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                if "capacity" in self.net.edges[u, v]:
                    self.net.edges[u, v]['capacity'] -= bandwidth

            if not self.add_path_flows(path, bandwidth, meters):
                return []
            if not self.add_path_flows(path[::-1], bandwidth, meters):
                return []

            self.slices[(src, dst)] = (path, bandwidth, meters)

            return path
        except nx.NetworkXNoPath:
            return []
    
    def remove_slice(self, src, dst):
        if((src, dst) in self.slices):
            path, bandwidth, meters = self.slices[(src, dst)]
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                if "capacity" in self.net.edges[u, v]:
                    self.net.edges[u, v]['capacity'] += bandwidth
            self.remove_path_flows(path)
            self.remove_path_flows(path[::-1])

            for switch_id, meter_id in meters.items():
                datapath = self.datapaths.get(switch_id)
                if datapath:
                    self.remove_meter(datapath, meter_id)
                    self.logger.info(f"Deleted meter {meter_id} from switch {switch_id}")

            del self.slices[(src, dst)]
            return True
        else:
            return False
        
    def slice_exists(self, src, dst):
        if not src or not dst:
            return False
        return (src, dst) in self.slices
    
    def slice_info(self, src, dst):
        if(src, dst) in self.slices:
            path, bandwidth, _ = self.slices[(src, dst)]
            return {"path": path, "bandwidth": bandwidth}
        return None
    
    def remove_all_slices(self, src):
        keys_to_delete = [key for key in self.slices.keys() if key[0] == src]
        if not keys_to_delete:
            return 0
        
        for s, d in keys_to_delete:
            self.remove_slice(s, d)
        
        return len(keys_to_delete)
        
    def update_slice(self, src, dst, new_bandwidth):
        if (src, dst) not in self.slices:
            return False, "Slice does not exist"
        
        path, current_bandwidth, meters = self.slices[(src, dst)]
        delta = new_bandwidth - current_bandwidth

        if delta > 0:
            for i in range(len(path)-1):
                u, v = path[i], path[i+1]
                if "capacity" in self.net.edges[u, v] and self.net.edges[u, v]['capacity'] < delta:
                    return False, "Insufficient bandwidth"
                
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            if "capacity" in self.net.edges[u, v]:
                self.net.edges[u, v]['capacity'] -= delta
            
        for switch_id, meter_id in meters.items():
            datapath = self.datapaths.get(switch_id)
            if not datapath:
                self.logger.warning(f"Switch {switch_id} is not connected to Ryu yet!")
                return False, f"Switch {switch_id} not connected"
            
            self.add_meter(datapath, meter_id, new_bandwidth, command=datapath.ofproto.OFPMC_MODIFY)
            self.logger.info(f"Modified meter {meter_id} on switch {switch_id} to new rate {new_bandwidth}")

        self.slices[(src, dst)] = (path, new_bandwidth, meters)
        return True, "Modified"



class DynamicSlicesApi(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(DynamicSlicesApi, self).__init__(req, link, data, **config)
        self.app = data[api_instance_name]

    @route('hello-world', '/hello-world', methods=['GET'])
    def hello_world(self, req, **kwargs):
        return Response(status=200, body="hello, world!")

    @route('slicing', '/slice/{src}/{dst}', methods=['POST'])
    def request_slice(self, req, **kwargs):
        try:
            src = kwargs.get('src')
            dst = kwargs.get('dst')
            
            try:
                data = json.loads(req.body)
            except ValueError:
                return Response(status=400, json_body={"error": "Invalid JSON body"})

            
            bandwidth = data.get('bandwidth')

            if bandwidth is None:
                return Response(status=400, json_body={"error": "Missing 'bandwidth' in JSON body"})
            
            try:
                bandwidth = int(bandwidth)
            except ValueError:
                return Response(status=400, json_body={"error": "Bandwidth must be a valid number"})
            
            if self.app.slice_exists(src, dst):
                return Response(status=409, json_body={"status": "Denied", "reason": "Slice already exists"})
            
            path = self.app.reserve_slice(src, dst, bandwidth)

            if path:
                return Response(status=200, json_body={"status": "Provisioned", "path": path})
            else:
                return Response(status=503, json_body={"status": "Denied", "reason": "Insufficient Bandwidth"})

        except Exception as e:
            self.app.logger.exception(e)
            return Response(status=400, json_body={"error": str(e)})



    @route('slicing', '/slice/{src}/{dst}', methods=['DELETE'])
    def request_remove_slice(self, req, **kwargs):
        try:
            src = kwargs.get('src')
            dst = kwargs.get('dst')
            removed = self.app.remove_slice(src, dst)
            if removed:
                return Response(status=200, json_body={"status": "Deleted"})
            else:
                return Response(status=400, json_body={"status": "Denied", "reason": "Inexistent path"})
        except Exception as e:
            self.app.logger.exception(e)
            return Response(status=400, json_body={"error": str(e)})
        
    @route('slicing', '/slice/{src}/{dst}', methods=['GET'])
    def slice_info(self, req, **kwargs):
        
        src = kwargs.get('src')
        dst = kwargs.get('dst')
        info = self.app.slice_info(src, dst)
        if info is None:
            return Response(status=404, json_body={"error": "Slice not found"})
        return Response(status=200, json_body={
            "status": "OK",
            "src": src,
            "dst": dst,
            "bandwidth": info["bandwidth"],
            "path": info["path"]
        })

    @route('slicing', '/slice/{src}', methods=['DELETE'])
    def remove_all_slices(self, req, **kwargs):
    
        src = kwargs.get('src')
        count = self.app.remove_all_slices(src)
        if count == 0:
            return Response(status=404, json_body={"error": "No slices found for source"})
        return Response(status=200, json_body={
            "status": "Deleted",
            "count": count,
            "source": src
        })
    
    @route('slicing', '/slice/{src}/{dst}', methods=['PUT'])
    def update_slice(self, req, **kwargs):
        try:
            src = kwargs.get('src')
            dst = kwargs.get('dst')

            try:
                data = json.loads(req.body)
            except ValueError:
                return Response(status=400, json_body={"error": "Invalid JSON body"})
            
            bandwidth = data.get('bandwidth')
            if bandwidth is None:
                return Response(status=400, json_body={"error": "Missing 'bandwidth' in JSON body"})
            
            try:
                bandwidth = int(bandwidth)
            except ValueError:
                return Response(status=400, json_body={"error": "Bandwidth must be a valid number"})
            
            if bandwidth <= 0:
                return Response(status=400, json_body={"error": "Bandwidth must be positive"})

            success, msg = self.app.update_slice(src, dst, bandwidth)
            if success:
                return Response(status=200, json_body={
                    "status": msg,
                    "new_bandwidth": bandwidth,
                    "path": self.app.slices[(src, dst)][0]
                })
            else:
                status_code = 404 if "does not exist" in msg else 409
                return Response(status=status_code, json_body={"status": "Denied", "reason": msg})
            
        except Exception as e:
            self.app.logger.exception(e)
            return Response(status=400, json_body={"error": str(e)})
        
