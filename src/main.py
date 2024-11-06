from networking import PeerNode
import sys
import time

def main():
    """
    Main function to initialize a peer node and optionally connect to another peer.
    """
    # Check if the user provided the required arguments
    if len(sys.argv) != 3:
        print("Usage: python main.py <host> <port>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])

    # Initialize and start the peer node
    node = PeerNode(host, port)
    node.start()

    # Optionally connect to a peer
    peer_host = input("Enter peer host to connect (or press Enter to skip): ")
    if peer_host:
        peer_port = int(input("Enter peer port to connect: "))
        node.connect_to_peer(peer_host, peer_port)
        
        # Send a test message to connected peer
        time.sleep(1)  # Ensure connection is established
        node.send_message(f"Hello from new peer at host {host} port {port}!")

if __name__ == "__main__":
    main()
