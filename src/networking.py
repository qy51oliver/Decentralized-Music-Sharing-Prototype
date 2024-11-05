import socket
import threading

class PeerNode:
    """
    PeerNode class that represents a single peer in the P2P network.
    Each peer can connect to other peers, send messages, and listen for incoming connections.
    """
    
    def __init__(self, host, port):
        """
        Initializes the PeerNode with a host and port.
        
        Parameters:
        - host (str): The IP address of the node.
        - port (int): The port number on which the node listens for connections.
        """
        self.host = host
        self.port = port
        self.peers = []  # List of connected peers

    def start(self):
        """
        Starts the peer node by launching a thread to listen for incoming connections.
        """
        server_thread = threading.Thread(target=self.listen_for_connections)
        server_thread.start()

    def listen_for_connections(self):
        """
        Listens for incoming connections on the specified host and port.
        When a connection is received, it starts a new thread to handle the client.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"Node listening on {self.host}:{self.port}")
            
            while True:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        """
        Handles communication with a connected client. 
        Receives messages from the client and sends a confirmation.
        
        Parameters:
        - client_socket (socket): The socket object for the connected client.
        """
        with client_socket:
            while True:
                data = client_socket.recv(4096)
                if not data:  # Exit if no data is received
                    break
                print(f"Received: {data.decode()}")
                client_socket.sendall(b"Message received")  # Send confirmation to client

    def connect_to_peer(self, peer_host, peer_port):
        """
        Connects to another peer in the network.
        
        Parameters:
        - peer_host (str): The IP address of the peer to connect to.
        - peer_port (int): The port number of the peer to connect to.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
            try:
                peer_socket.connect((peer_host, peer_port))
                print(f"Connected to {peer_host}:{peer_port}")
                self.peers.append((peer_host, peer_port))  # Add peer to list
            except ConnectionRefusedError:
                print(f"Failed to connect to {peer_host}:{peer_port}")

    def send_message(self, message):
        """
        Sends a message to all connected peers.
        
        Parameters:
        - message (str): The message to be sent to each peer.
        """
        for peer_host, peer_port in self.peers:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                peer_socket.connect((peer_host, peer_port))
                peer_socket.sendall(message.encode())
