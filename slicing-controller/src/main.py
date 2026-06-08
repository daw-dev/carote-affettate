import json
import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
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
        self.load_topology('/topology.json')
        
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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        self.logger.info("bro mi è arrivato un pacchetto, non so che fare")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 1. An empty match means "match every packet"
        match = parser.OFPMatch()

        # 2. The action is to output to the controller port
        # OFPCML_NO_BUFFER tells the switch to send the entire packet to the controller
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        # 3. Apply the actions
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        # 4. Construct the FlowMod message
        # priority=0 is crucial. It ensures this rule only hits if no higher-priority rules match.
        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)

        # 5. Send the rule to the switch
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

    def reserve_slice(self, src_ip, dst_ip, bandwidth):
        valid_link = nx.subgraph_view(self.net, filter_edge=lambda u, v: self.net.edges[u, v].get("capacity", 0) > bandwidth)


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
            success, path = self.app.reserve_slice(
                data['src_ip'], data['dst_ip'], 
                data['bandwidth']
            )
            
            if success:
                return Response(status=200, json_body={"status": "Provisioned", "path": path})
            return Response(status=503, json_body={"status": "Denied", "reason": "Insufficient Bandwidth"})
        except Exception as e:
            return Response(status=400, json_body={"error": str(e)})
