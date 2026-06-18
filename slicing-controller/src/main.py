import json
import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response

api_instance_name = 'slicing_api_app'

class StaticSlicingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(StaticSlicingController, self).__init__(*args, **kwargs)
        self.load_topology('/topology.json')
        
        wsgi = kwargs['wsgi']
        wsgi.register(SlicingRestApi, {api_instance_name: self})
        self.logger.info("Static Slicing Controller Ready.")
        self.datapaths = {}

    def load_topology(self, filepath):
        try:
            with open(filepath, 'r') as f:
                graph_data = json.load(f)
                self.net = nx.node_link_graph(graph_data)
                print(self.net)
            self.logger.info("Topology graph loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load topology: {e}")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        self.logger.info("bro mi è arrivato un pacchetto, non so che fare")

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

    def instruct_switches(self, path, src_ip, dst_ip):
        self.logger.info(f"creating path {path} from {src_ip} to {dst_ip}")
        self.logger.info(self.datapaths)
        for i in range(1, len(path) - 1):
            current_node = path[i]
            switch_id = self.net.nodes[current_node]["switch_id"]
            
            if not switch_id:
                continue
                
            prev_node = path[i-1]
            next_node = path[i+1]
            
            datapath = self.datapaths.get(switch_id)

            if not datapath:
                self.logger.warning(f"Switch {switch_id} is not connected to Ryu yet!")
                continue

            in_port = self.net.edges[prev_node][current_node]["target_port"]
            out_port = self.net.edges[current_node][next_node]["source_port"]

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
            
            actions = [parser.OFPActionOutput(out_port)]
            
            self.add_flow(datapath, 100, match, actions)
            self.logger.info(f"Installed flow on {current_node}: in={in_port} -> out={out_port}")

    def reserve_slice(self, src, dst, bandwidth):
        valid_links = nx.subgraph_view(self.net, filter_edge=lambda u, v: self.net.edges[u, v]["capacity"] > bandwidth)

        try:
            path = nx.shortest_path(valid_links, source=src, target=dst)

            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                self.net.edges[u, v]['capacity'] -= bandwidth

            self.instruct_switches(path, self.net.nodes[src]["interfaces"]["eth0"], self.net.nodes[dst]["interfaces"]["eth0"])

        except nx.NetworkXNoPath:
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
            
            if success:
                return Response(status=200, json_body={"status": "Provisioned", "path": path})
            return Response(status=503, json_body={"status": "Denied", "reason": "Insufficient Bandwidth"})
        except Exception as e:
            return Response(status=400, json_body={"error": str(e)})
