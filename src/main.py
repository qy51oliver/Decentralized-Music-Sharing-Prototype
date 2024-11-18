from networking import PeerNode, TrackerNode
import sys
import time

def main():
    """
    Main function to initialize a peer node and optionally connect to another peer.
    """
    # Check if the user provided the required arguments
    if len(sys.argv) != 4:
        print("Usage: python main.py <host> <port> tracker/peer")
        sys.exit(1)
    # Parse input arguments    
    host = sys.argv[1]
    try:
        port = int(sys.argv[2])
        if not (0 < port < 65536):
            raise ValueError("Port must be in range 1-65535.")
    except ValueError as e:
        print(f"Invalid port: {e}")
        sys.exit(1)
    
    node_type = sys.argv[3].lower()
    if node_type == "peer":
        start_peer(host, port)
    elif node_type == "tracker":
        start_tracker(host, port)
    else:
        print("Invalid node type. Use 'tracker' or 'peer'.")
        sys.exit(1)

def start_peer(host, port):
    # Initialize and start the peer node
    try:
        print(f"Starting peer node on {host}:{port}...")
        node = PeerNode(host, port)
        node.start()
    except Exception as e:
        print(f"Error starting peer node: {e}")
        sys.exit(1)

def start_tracker(host, port):
    # Initialize and start the tracker node
    try:
        print(f"Starting tracker node on {host}:{port}...")
        node = TrackerNode(host, port)
        node.start()
    except Exception as e:
        print(f"Error starting tracker node: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
