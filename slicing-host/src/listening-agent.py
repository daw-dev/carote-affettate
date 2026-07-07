import argparse
import socket
import subprocess
import time
import sys

# The Control Port used to organize the iperf test
CONTROL_PORT = 9999 

def run_agent():
    # Create a standard TCP Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Bind to PORT 9999 on all local network interfaces
        server_socket.bind(("0.0.0.0", CONTROL_PORT))
        server_socket.listen(5)
        print(f"[*] Control Agent listening on PORT {CONTROL_PORT}...")
    except Exception as e:
        print(f"[-] Failed to bind to port {CONTROL_PORT}: {e}")
        sys.exit(1)

    while True:
        try:
            # Accept incoming control connection from the Client Host
            conn, addr = server_socket.accept()
            client_ip = addr[0]
            
            # Read the message sent by the Client
            message = conn.recv(1024).decode().strip()
            
            if message == "START_SERVER":
                print(f"[*] Trigger received from Client ({client_ip}). Spawning iperf3...")
                
                # Launch the local iperf3 server.
                subprocess.Popen(["iperf3", "-s", "-1"])
                # This automatically opens the default iperf3 data port: 5201
                # '-1' forces the server to exit right after this single test finishes
                
                # Give iperf3 1 second to successfully bind to PORT 5201
                time.sleep(1)
                
                # Send confirmation back to the Client over the control channel
                print(f"[+] iperf3 is listening on PORT 5201. Permitting client to start.")
                conn.sendall(b"SERVER_READY")
            
            conn.close()
            
        except KeyboardInterrupt:
            print("\n[*] Stopping Control Agent.")
            break
        except Exception as e:
            print(f"[-] Error: {e}")

if __name__ == "__main__":
    run_agent()
