from ctypes import addressof
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

class StaticSlicingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(StaticSlicingController, self).__init__(*args, **kwargs)
        self.load_topology('/topology.json')
        self.add_nodes_to_dns('/etc/hosts')
        
        wsgi = kwargs['wsgi']
        wsgi.register(SlicingRestApi, {api_instance_name: self})
        self.logger.info("Static Slicing Controller Ready.")
        self.datapaths = {}
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

    def add_nodes_to_dns(self, filepath):
        try:
            with open(filepath, 'a') as f:
                for node, data in self.net.nodes(data=True):
                    address = data["device_address"]
                    f.write(f"{address} {node}\n")

                self.logger.info("DNS nodes written")
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

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        self.logger.info("Sending a FLOW_MOD to switch")
        datapath.send_msg(mod)

    def delete_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        mod = parser.OFPFlowMod(datapath=datapath, match=match, command=ofproto.OFPFC_DELETE, 
                                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY)
        self.logger.info("Deleting a path")
        datapath.send_msg(mod)


    def instruct_switches(self, path, src_ip, dst_ip):
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
                continue

            in_port = self.net.edges[prev_node, current_node]["ports"][current_node]
            out_port = self.net.edges[current_node, next_node]["ports"][current_node]

            if in_port is None or out_port is None:
                self.logger.error(f"Missing port link data for {current_node}")
                continue

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
            
            self.add_flow(datapath, 100, match, actions)
            self.logger.info(f"Installed flow on {current_node}: in={in_port} -> out={out_port}")

    def reinstruct_switches(self, path, src_ip, dst_ip):
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

            self.delete_flow(datapath, match)
            self.logger.info(f"Deleting path on {current_node}")



    def reserve_slice(self, src, dst, bandwidth):
        valid_links = nx.subgraph_view(self.net, filter_edge=lambda u, v: self.net.edges[u, v]["capacity"] > bandwidth)

        try:
            path = nx.shortest_path(valid_links, source=src, target=dst)

            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                self.net.edges[u, v]['capacity'] -= bandwidth

            self.instruct_switches(path, self.net.nodes[src]["device_address"], self.net.nodes[dst]["device_address"])
            self.slices[(src, dst)] = (path, bandwidth)

            return path
        except nx.NetworkXNoPath:
            return []
    
    def delete_slice(self, src, dst):
        if((src, dst) in self.slices):
            (path, bandwidth) = self.slices[(src, dst)]
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                self.net.edges[u, v]['capacity'] += bandwidth
            self.reinstruct_switches(path, self.net.nodes[src]["device_address"], self.net.nodes[dst]["device_address"])
            del self.slices[(src, dst)]
            return True
        else:
            return False
        



class SlicingRestApi(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SlicingRestApi, self).__init__(req, link, data, **config)
        self.app = data[api_instance_name]

    @route('hello-world', '/hello-world', methods=['GET'])
    def hello_world(self, req, **kwargs):
        return Response(status=200, body="hello, world!")

    @route('slicing', '/slice/request', methods=['POST'])
    def request_slice(self, req, **kwargs):
        try:
            data = json.loads(req.body)
            path = self.app.reserve_slice(
                data['src'], data['dst'],
                data['bandwidth']
            )

            if path:
                return Response(status=200, json_body={"status": "Provisioned", "path": path})
            else:
                return Response(status=503, json_body={"status": "Denied", "reason": "Insufficient Bandwidth"})
        except Exception as e:
            return Response(status=400, json_body={"error": str(e)})

    @route('slicing', '/slice/request', methods=['DELETE'])
    def request_delete_slice(self, req, **kwargs):
        try:
            data = json.loads(req.body)
            deleted = self.app.delete_slice(data["src"], data["dst"])
            if deleted:
                return Response(status=200, json_body={"status": "Deleted"})
            else:
                return Response(status=400, json_body={"status": "Denied", "reason": "Inexistent path"})
        except Exception as e:
            return Response(status=400, json_body={"error": str(e)})