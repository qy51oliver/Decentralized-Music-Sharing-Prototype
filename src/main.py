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

    if sys.argv[3] == "peer":
        start_peer()
    else:
        start_tracker()

def start_peer():
    host = sys.argv[1]
    port = int(sys.argv[2])

    # Initialize and start the peer node
    node = PeerNode(host, port)
    node.start()

    # # Optionally connect to a peer
    # peer_host = input("Enter peer host to connect (or press Enter to skip): ")
    # if peer_host:
    #     peer_port = int(input("Enter peer port to connect: "))
    #     node.connect_to_peer(peer_host, peer_port)
        
    #     # Send a test message to connected peer
    #     time.sleep(1)  # Ensure connection is established
    #     node.send_message("Hello from new peer!")

def start_tracker():
    host = sys.argv[1]
    port = int(sys.argv[2])

    # Initialize and start the tracker node
    node = TrackerNode(host, port)
    node.start()

    # # Optionally connect to a peer
    # peer_host = input("Enter peer host to connect (or press Enter to skip): ")
    # if peer_host:
    #     peer_port = int(input("Enter peer port to connect: "))
    #     node.connect_to_peer(peer_host, peer_port)
        
    #     # Send a test message to connected peer
    #     time.sleep(1)  # Ensure connection is established
    #     node.send_message("Hello from new peer!")

if __name__ == "__main__":
    main()
