import os
import pickle
import random
import socket
import sys
import threading
import time

class TrackerNode:
    def __init__(self, host, port):
        """
        Initializes the TrackerNode with a host and port.
        
        Parameters:
        - host (str): The IP address of the node.
        - port (int): The port number on which the node listens for connections.
        """
        self.host = host
        self.port = port
        self.peer_dict = {} # key=filename, val=list of tuples (ip, port) that have the file available
        self.last_heartbeat = {}  # key=(host, port), value=last heartbeat timestamp

    def start(self):
        """
        Starts the peer node by launching a thread to listen for incoming connections.
        & Clean up stale peers
        """
        server_thread = threading.Thread(target=self.listen_for_connections)
        server_thread.start()
        cleanup_thread = threading.Thread(target=self.remove_stale_peers)
        cleanup_thread.start()

    def listen_for_connections(self):
        """
        Listens for incoming connections on the specified host and port.
        When a connection is received, it starts a new thread to handle the client.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"Tracker node listening on {self.host}:{self.port}")
            
            while True:
                client_socket, address = server_socket.accept()
                print(f"Connection from peer at {address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        """
        Handles communication with a connected peer. 
        Receives requests from the peer and responds appropriately.
        
        Parameters:
        - client_socket (socket): The socket object for the connected client.
        """
        with client_socket:
            header = client_socket.recv(4096).rstrip(b"\0") # strip padding bytes
            if not header:
                print("requests must include a 4096 byte header with the request type")
                sys.exit(1)
                
            request_type = header.decode().strip()
            print("request_type: " + request_type)
            message = b''
            
            if request_type != "view_available": #view_available has no additional data to be sent
                data = client_socket.recv(4096)
                message += data
                print(threading.get_ident())
                
            if request_type == "register": #register ownership of a file to a node, making it available for peer downloads
                host, _ = client_socket.getpeername()
                str_message = message.decode().split(",") # message is sent in format filename,host_port (since client port is random, not server port)
                filename = str_message[0]
                port = int(str_message[1])
                if filename not in self.peer_dict:
                    self.peer_dict[filename] = []
                self.peer_dict[filename].append((host, port))
                self.last_heartbeat[(host, port)] = time.time()
                print("Filename " + filename + " registered to " + host + ", " + str(port))
                
            elif request_type == "view_available": #view which files have been registered by nodes and are available to download
                client_socket.sendall(str.encode(str(list(self.peer_dict.keys()))))
                
            if request_type == "get": # coordinate a file download
                str_message = message.decode().split(",") # message is sent in format filename,host_port (since client port is random, not server port)
                filename = str_message[0]
                host, _ = client_socket.getpeername()
                port = int(str_message[1])
                if filename not in self.peer_dict:
                    print("The requested file has no peers registered to it")
                else:
                    peerlist = self.peer_dict[filename]
                    client_socket.sendall(pickle.dumps(peerlist))
                    print("Peerlist for file " + filename + " sent to " + host + ":" + str(port))
                    
            if request_type in ["register", "view_available", "get"]:
                host, port = client_socket.getpeername()
                self.last_heartbeat[(host, port)] = time.time()
                print(f"Heartbeat received from {host}:{port}")
    
    def remove_stale_peers(self):
        """
        Periodically removes peers that have not sent a heartbeat within a certain time.
        """
        while True:
            time.sleep(10) # Check every 10 seconds
            current_time = time.time()
            timeout = 300 # The time a peer waits to be stale
            for filename in list(self.peer_dict.keys()):
                updated_peers = []
                removed_peers = []
                for host, port in self.peer_dict[filename]:
                    # Check if the peer's last heartbeat is within the timeout
                    last_heartbeat = self.last_heartbeat.get((host, port), 0)
                    if current_time - last_heartbeat <= timeout:
                        updated_peers.append((host, port))
                    else:
                        removed_peers.append((host, port))
                
                self.peer_dict[filename] = updated_peers
                if removed_peers:
                    print(f"Removed stale peers for '{filename}': {removed_peers}")
            
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
        self.files = {} # key=filename, value=path, filename is any string identifier for the file which should be globally constant, while path is specific to the node's host machine

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
            print(f"Peer node listening on {self.host}:{self.port}")
            print("Commands:")
            print("REGISTER <filename> <src_filepath> <host> <port>: register ownership of the file with the identifier filename and path filepath to yourself with the tracker at the specified IP and port")
            print("VIEW_AVAILABLE <host> <port>: view files that have been registered with the tracker and are available to be downloaded")
            print("GET <filename> <dst_filepath> <host> <port>: ask tracker at host and port to coordinate a download of filename from a peer to local path filepath")
            
            threading.Thread(target=self.handle_user_input).start()
            while True:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
    
    def handle_user_input(self):
        """
        Allows the user to input commands to a peer node's CLI, and handles those commands appropriately.
        """
        while True:
            command = input("What would you like to do?\n").strip().lower()
            command_split = command.split(" ")
            if command_split[0] == "register":
                filename = command_split[1]
                filepath = os.path.abspath(command_split[2])
                host = command_split[3]
                port = int(command_split[4])
                if os.path.isfile(filepath):
                    self.register_with_tracker(filename, host, port)
                    self.files[filename] = filepath
                else:
                    print("The filepath you provided (" + filepath + ") does not correspond with a file.")
            elif command_split[0] == "view_available":
                host = command_split[1]
                port = int(command_split[2])
                self.get_available_files(host, port)
            elif command_split[0] == "get":
                filename = command_split[1]
                filepath = os.path.abspath(command_split[2])
                if not os.path.isdir(os.path.dirname(filepath)):
                    print("The specified directory does not exist")
                elif os.path.exists(filepath):
                    print("There is already a file at this path. Delete it if you want to download another")
                else:
                    host = command_split[3]
                    port = int(command_split[4])
                    peerlist = self.get_peerlist_from_tracker(filename, host, port)
                    self.download_file_from_peer(peerlist, filename, filepath)
    
    def download_file_from_peer(self, peerlist, filename, filepath):
        """
        Initiates a peer-to-peer download.
        Pick a peer from the peerlist, request that peer to send the file filename, and download it to dst filepath.
        
        Parameters:
        - peerlist (list(tuple(str, int))): A list of peers with the file filename.
        - filename (str): The filename to be downloaded
        - filepath (str): The dst path to download the file to.
        """
        host, ip = random.choice(peerlist) # choose a random peer (this should be more sophisticated)
        peer_socket = self.connect_to_node(host, ip)
        header = b"file_request"
        header += b"\0" * (4096-len(header)) #padding
        peer_socket.send(header)
        peer_socket.send(str.encode(filename))
        
        response_header = peer_socket.recv(4096).decode()
        if response_header != "file_response":
            print("response header malformed, should be file_response")
        else:
            file_bytes = b""
            with peer_socket:
                while True:
                    data = peer_socket.recv(4096)
                    if not data:  # Exit if no data is received
                        break
                    file_bytes += data
        with open(filepath, 'wb') as downloaded_file:
            downloaded_file.write(file_bytes)
        print("file downloaded successfully")
        

    def register_with_tracker(self, filename, host, port):
        """
        Registers the file represented by filename with the tracker at host and port.
        This signals to the tracker that the client possesses ownership of the file and can be counted on to distribute it to peers.
        
        Parameters:
        - filename (str): The filename being registered
        - host (str): The IP of the tracker.
        - port (int): The port of the tracker.
        """
        header = b"register"
        header += b"\0" * (4096-len(header)) #padding
        tracker_socket = self.connect_to_node(host, port)
        tracker_socket.sendall(header)
        tracker_socket.sendall(str.encode(filename+","+str(self.port))) #necessary to pass along server port since client port is different and randomly allocated
    
    def get_available_files(self, host, port):
        """
        Requests a list of available files currently being tracked by the tracker and prints it.
        
        Parameters:
        - host (str): The IP of the tracker.
        - port (int): The port of the tracker.
        """
        header = b"view_available"
        header += b"\0" * (4096-len(header)) #padding
        tracker_socket = self.connect_to_node(host, port)
        tracker_socket.sendall(header)
        available_files = b""
        with tracker_socket:
            while True:
                data = tracker_socket.recv(4096)
                if not data:  # Exit if no data is received
                    break
                available_files += data
        print("Available files: " + available_files.decode())
    
    def get_peerlist_from_tracker(self, filename, host, port):
        """
        Requests a list of peers registered to a filename from the tracker and returns it.
        
        Parameters:
        - filename (str): The filename we want the peers for.
        - host (str): The IP of the tracker.
        - port (int): The port of the tracker.

        Returns:
        - peerlist (list(tuple(str, int))): The peerlist of (host, port) tuples registered to the requested filename.
        """
        header = b"get"
        header += b"\0" * (4096-len(header)) #padding
        tracker_socket = self.connect_to_node(host, port)
        tracker_socket.sendall(header)
        tracker_socket.sendall(str.encode(filename+","+str(self.port)))
        message = b""
        with tracker_socket:
            while True:
                data = tracker_socket.recv(4096)
                if not data:  # Exit if no data is received
                    break
                message += data
        peerlist = pickle.loads(message)
        print(peerlist)
        return peerlist

    def handle_client(self, client_socket):
        """
        Handles communication with a connected client. 
        Receives messages from the client. If the message is a file_request, send a file_response with send_file().
        
        Parameters:
        - client_socket (socket): The socket object for the connected client.
        """
        with client_socket:
            while True:
                data = client_socket.recv(4096)
                if not data:  # Exit if no data is received
                    break
                decoded = data.rstrip(b"\0").decode()
                print(f"Received: {decoded}")
                if decoded == 'file_request':
                    filename = client_socket.recv(4096).decode()
                    print(filename)
                    self.send_file(filename, client_socket)
                    break #necessary since socket is closed in send_file, rerunning the loop would try to recv from closed socket

    def connect_to_node(self, host, port):
        """
        Connects to another node in the network.
        
        Parameters:
        - host (str): The IP address of the node to connect to.
        - port (int): The port number of the port to connect to.

        Returns:
        - node_socket (socket): the node socket with an open connection.
        """
        node_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        node_socket.connect((host, port))
        print(f"Connected to node {host}:{port}")
        return node_socket

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

    def send_file(self, filename, client_socket):
        """
        Sends a file to client_socket.
        
        Parameters:
        - filename (str): The file to be sent.
        - client_socket (socket): The socket to send the connection to.
        """
        chunk_number = 0
        client_socket.sendall(b"file_response")
        if filename not in self.files:
            client_socket.sendall("file not owned by this peer!") # this shouldn't happen if the tracker has an up to date peerlist
        filepath = self.files[filename]
        try:
            file = open(filepath, 'rb')
            data = file.read(4096)
            print("about to send file")
            while data:
                print("sending chunk number " + str(chunk_number))
                chunk_number += 1
                client_socket.sendall(data)
                data = file.read(4096)
            print("file send complete")
            file.close()
            client_socket.close()
        except Exception as e:
            print("error when sending file: " + str(e))

