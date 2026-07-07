import argparse
import json
import socket
import subprocess
import sys
import os

# python3 host/run-iperf.py --ip 'destination_name' --bitrate 1M --time 5

# The Control Port must match the temporary server's port
CONTROL_PORT = 9999

def run_test(target_name, bitrate, duration):
    src_name = os.environ.get('NAME')
    controller_ip = os.environ.get('CONTROLLER_ADDRESS')

    # Before running the test, check if a network slice is active.
    command = ["curl", "-X", "GET", f"{controller_ip}:8080/slice/{src_name}/{target_name}"]

    try:
        result = subprocess.run(
            command, 
            capture_output=True, # Captures stdout and stderr
            text=True,           # Returns output as a string instead of bytes
            check=True           # Raises an exception if non-zero exit code
        )
        
        raw_output = result.stdout

        if not raw_output or raw_output == "null":
            print(f"[-] No response received from the controller for slice check.")
            sys.exit(1)
        else:
            slice_data = json.loads(raw_output)
            if slice_data.get("error") is None:
                print(f"[+]Slice found - Path: {slice_data['path']}, Bandwidth: {slice_data['bandwidth']}")
            else:
                print(f"[-] No active network slice between {src_name} and {target_name} found. Please create a slice before running the test.")
                sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Failed to parse the response as JSON.")
        sys.exit(1)


    try:
        # Create a TCP socket
        control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Connect to the Target Host's IP on the Control Port (9999)
        print(f"[*] Step 1: Connecting to Agent at {target_name} on PORT {CONTROL_PORT}...")
        control_socket.connect((target_name, CONTROL_PORT))
        
        # Tell the Agent to spin up its iperf3 server
        print("[*] Step 2: Sending 'START_SERVER' command...")
        control_socket.sendall(b"START_SERVER")
        
        # Wait for the Agent to respond with "SERVER_READY"
        response = control_socket.recv(1024).decode().strip()
        # Control channel not needed anymore after receiving response
        control_socket.close()
        
        if response == "SERVER_READY":
            print("[+] Step 3: Permission granted! Target iperf3 is live.")
            print(f"[*] Step 4: Flooding {target_name} on default iperf3 PORT 5201 with bitrate {bitrate} for {duration}s...")
            
            # Run the actual iperf3 data test.
            client_cmd = ["iperf3", "-c", target_name, "-b", str(bitrate),"-t", str(duration)]
            result = subprocess.run(client_cmd, capture_output=True, text=True)
            # This traffic goes to TARGET_IP on PORT 5201.
            
            print("\n================== IPERF3 TEST RESULTS ==================")
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
            print("=========================================================")
        else:
            print(f"[-] Target refused to start server. Response received: {response}")
            
    except Exception as e:
        print(f"[-] Network/Orchestration error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger remote iperf3 server and run client test.")
    
    # Command line arguments
    parser.add_argument("--ip", type=str, required=True,
                        help="The IP address of the target host running the agent.")
    parser.add_argument("--bitrate", type=str, default="1M",
                        help="Bitrate for the iperf3 test (default: 1M).")
    parser.add_argument("--time", type=int, default=10,
                        help="Duration of the test in seconds (default: 10).")

    args = parser.parse_args()
    run_test(args.ip, args.bitrate, args.time)