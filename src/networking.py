import os
import time
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
        self.messages = []
        self.files = {}

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
            # Receive initial command to determine whether it's a file or a message
            command = client_socket.recv(1024).decode()
            if command == "SEND_FILE":
                # Handle file reception (as in the previous example)
                file_name = client_socket.recv(1024).decode()
                file_path = f"received_{file_name}"
                print(f"Receiving file: {file_name}")
                
                # Receive and save file
                with open(file_path, "wb") as file:
                    while True:
                        data = client_socket.recv(4096)
                        if not data:
                            break
                        file.write(data)
                
                # Store the file reference in self.files
                self.files[file_name] = file_path
                print(f"HERE: peer node at host {self.host} port {self.port} files {self.files}")
                client_socket.sendall(b"File received successfully")

            else:
                # Assume it's a message if not a file command
                self.messages.append(command)  # Store the message
                print(f"Received message: {command}")
                print(f"HERE: peer node at host {self.host} port {self.port} messages", self.messages)
                client_socket.sendall(b"Message received")

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
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                    peer_socket.connect((peer_host, peer_port))
                    peer_socket.sendall(message.encode())
                    print(f"Message sent to {peer_host}:{peer_port}")
            except ConnectionRefusedError:
                print(f"Failed to send message to {peer_host}:{peer_port}")
    
    def send_direct_message(self, peer_host, peer_port, message):
        """
        Sends a message to a specific peer.
        
        Parameters:
        - peer_host (str): The IP address of the peer.
        - peer_port (int): The port number of the peer.
        - message (str): The message to send.
        - message (str): The message to be sent to each peer.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
            try:
                peer_socket.connect((peer_host, peer_port))
                peer_socket.sendall(message.encode())
                print(f"Direct message sent to {peer_host}:{peer_port}")
            except ConnectionRefusedError:
                print(f"Failed to send direct message to {peer_host}:{peer_port}")
    
    def send_file(self, peer_host, peer_port, file_path):
        """
        Sends a file to a specific peer.
        
        Parameters:
        - peer_host (str): The IP address of the peer to send the file to.
        - peer_port (int): The port number of the peer to send the file to.
        - file_path (str): The path to the file to be sent.
        """
        file_name = os.path.basename(file_path)
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
            try:
                peer_socket.connect((peer_host, peer_port))
                
                # Send a command to indicate a file transfer
                peer_socket.sendall(b"SEND_FILE")
                
                # Send the file name
                peer_socket.sendall(file_name.encode())
                
                # Send the file data in chunks
                with open(file_path, "rb") as file:
                    while chunk := file.read(4096):  # Read the file in 4 KB chunks
                        try:
                            peer_socket.sendall(chunk)
                            time.sleep(0.01) # add 0.01s delay to prevent network buffer overflow by pacing the file transfer
                        except BrokenPipeError:
                            print(f"Connection lost while sending {file_name}")
                            return
                
                print(f"File {file_name} sent to {peer_host}:{peer_port}")
                
                # Wait for confirmation from the receiving peer
                confirmation = peer_socket.recv(1024).decode()
                if confirmation == "File received successfully":
                    print(f"File {file_name} confirmed received by {peer_host}:{peer_port}")
                else:
                    print(f"Failed to confirm file reception from {peer_host}:{peer_port}")
                    
            except ConnectionRefusedError:
                print(f"Failed to send file to {peer_host}:{peer_port}")
            except BrokenPipeError:
                print("BrokenPipeError: Connection closed by peer unexpectedly.")


# Example Usage with Multiple Peer Nodes
if __name__ == "__main__":
    # Initialize two nodes for demonstration (they could be run in separate scripts for a real test)
    peer1 = PeerNode('localhost', 8001)
    peer2 = PeerNode('localhost', 8002)
    peer3 = PeerNode('localhost', 8003)
    peer4 = PeerNode('localhost', 8004)
    peer5 = PeerNode('localhost', 8005)
    
    # Start listening for connections on both peers
    peer1.start()
    peer2.start()
    peer3.start()
    peer4.start()
    peer5.start()

    # Connect peer1 to other peers
    peer1.connect_to_peer('localhost', 8002)
    peer1.connect_to_peer('localhost', 8003)
    peer1.connect_to_peer('localhost', 8004)
    peer1.connect_to_peer('localhost', 8005)

    # # Send a message from peer1 to all other peers and verify that they got the message
    peer1.send_message("Hello from peer1!")
    
    # Send a targetted message from peer1 to peer2
    peer1.send_direct_message('localhost', 8002, "Special message for peer2!")
    
    # Send a music from peer1 to peer3
    peer1.send_file('localhost', 8003, "/Users/ednazhang/Decentralized-Music-Sharing-Prototype/nocopyright-music/AlbertBeger-Shasha.mp3")
    ##TO DO: debug Connection lost while sending AlbertBeger-Shasha.mp3 error