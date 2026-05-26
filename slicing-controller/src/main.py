import json
import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib
from webob import Response

api_instance_name = 'slicing_api_app'

class StaticSlicingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(StaticSlicingController, self).__init__(*args, **kwargs)
        self.switches = {}
        self.net = nx.Graph()
        
        # 1. Load the pre-calculated graph
        self.load_topology('/topology.json')
        
        # 2. Start the REST API
        wsgi = kwargs['wsgi']
        wsgi.register(SlicingRestApi, {api_instance_name: self})
        self.logger.info("Static Slicing Controller Ready.")

    def load_topology(self, filepath):
        try:
            with open(filepath, 'r') as f:
                graph_data = json.load(f)
                self.net = nx.node_link_graph(graph_data)
                print(self.net)
            self.logger.info("Topology graph loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load topology: {e}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.switches[datapath.id] = datapath
        self.logger.info(f"Switch {datapath.id} connected (Network is Dark).")

    def provision_slice(self, src_ip, dst_ip, src_dpid, dst_dpid, bw_req):
        """Finds a path with enough bandwidth, reserves it, and pushes flows."""
        try:
            # Create a subgraph of links that can support the requested bandwidth
            def valid_link(u, v, d):
                return d['available_capacity'] >= bw_req

            valid_subgraph = nx.subgraph_view(self.net, filter_edge=valid_link)
            
            # Calculate shortest path on the filtered graph
            path = nx.shortest_path(valid_subgraph, src_dpid, dst_dpid)
            self.logger.info(f"Path calculated for {src_ip}->{dst_ip}: {path}")

            # Push OpenFlow rules and update capacity
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                
                # Get the physical port from the graph
                out_port = self.net[u][v]['port']
                
                # Push the rule to the switch
                self.add_ip_flow(u, src_ip, dst_ip, out_port)
                
                # Deduct the bandwidth
                self.net[u][v]['available_capacity'] -= bw_req
                
            return True, path

        except nx.NetworkXNoPath:
            self.logger.error("Slice Denied: No path with sufficient bandwidth.")
            return False, []

    def add_ip_flow(self, dpid, src_ip, dst_ip, out_port):
        if dpid not in self.switches:
            return
        
        datapath = self.switches[dpid]
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        mod = parser.OFPFlowMod(datapath=datapath, priority=100, match=match, instructions=inst)
        datapath.send_msg(mod)


class SlicingRestApi(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SlicingRestApi, self).__init__(req, link, data, **config)
        self.app = data[api_instance_name]

    @route('slicing', '/slice/request', methods=['POST'])
    def request_slice(self, req, **kwargs):
        try:
            data = json.loads(req.body)
            success, path = self.app.provision_slice(
                data['src_ip'], data['dst_ip'], 
                data['src_dpid'], data['dst_dpid'], 
                data['bandwidth']
            )
            
            if success:
                return Response(status=200, json_body={"status": "Provisioned", "path": path})
            return Response(status=503, json_body={"status": "Denied", "reason": "Insufficient Bandwidth"})
        except Exception as e:
            return Response(status=400, json_body={"error": str(e)})
