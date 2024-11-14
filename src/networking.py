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
            print(f"Tracker node listening on {self.host}:{self.port}")
            
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
            header = client_socket.recv(4096).rstrip(b"\0") # strip padding bytes
            if not header:
                print("requests must include a 4096 byte header with the request type")
                sys.exit(1)
            request_type = header.decode().strip()
            print("request_type: " + request_type)
            message = b''
            if request_type != "view_available": #view_available has no additional data to be sent
                data = client_socket.recv(4096)
                # if not data:  # Exit if no data is received
                #     break
                message += data
                print(f"Received: {data.decode()}")
                print(threading.get_ident())
                # client_socket.sendall(b"Message received")  # Send confirmation to client
            print("out of loop")
            if request_type == "register": #register ownership of a file to a node, making it available for peer downloads
                host, _ = client_socket.getpeername()
                str_message = message.decode().split(",") # message is sent in format filename,host_port (since client port is random, not server port)
                filename = str_message[0]
                port = int(str_message[1])
                if filename not in self.peer_dict:
                    self.peer_dict[filename] = []
                self.peer_dict[filename].append((host, port))
                print("filename " + filename + " registered to " + host + ", " + str(port))
            elif request_type == "view_available": #view which files have been registered by nodes and are available to download
                client_socket.sendall(str.encode(str(list(self.peer_dict.keys()))))
            print("before get")
            if request_type == "get": # coordinate a file download
                print("got to get")
                str_message = message.decode().split(",") # message is sent in format filename,host_port (since client port is random, not server port)
                filename = str_message[0]
                print("get start")
                port = int(str_message[1])
                if filename not in self.peer_dict:
                    print("the requested file has no peers registered to it")
                else:
                    # header = b"peerlist"
                    # header += b"\0" * (4096-len(header)) #padding
                    # client_socket.sendall(header)
                    peers = self.peer_dict[filename]
                    client_socket.sendall(pickle.dumps(peers))
                print("get sent")
        client_socket.close()
                

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
            print("REGISTER <filename> <filepath> <host> <port>: register ownership of the file with the identifier filename and path filepath to yourself with the tracker at the specified IP and port")
            print("VIEW_AVAILABLE <host> <port>: view files that have been registered with the tracker and are available to be downloaded")
            print("GET <filename> <filepath> <host> <port>: ask tracker at host and port to coordinate a download of filename from a peer to local path filepath")
            
            threading.Thread(target=self.handle_user_input).start()
            while True:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            # while True:
            #     client_socket, address = server_socket.accept()
            #     print(f"Connection from {address}")
            #     # threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            #     threading.Thread(target=self.handle_client_file, args=(client_socket,)).start()
    
    def handle_user_input(self):
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
        host, ip = random.choice(peerlist) # choose a random peer (this should be more sophisticated)
        peer_socket = self.connect_to_node(host, ip)
        header = b"file_request"
        header += b"\0" * (4096-len(header)) #padding
        peer_socket.send(header)
        peer_socket.send(str.encode(filename))
        
        response_header = peer_socket.recv(4096).decode()
        print(response_header)
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
        

    def register_with_tracker(self, filename, host, port):
        header = b"register"
        header += b"\0" * (4096-len(header)) #padding
        tracker_socket = self.connect_to_node(host, port)
        tracker_socket.sendall(header)
        tracker_socket.sendall(str.encode(filename+","+str(self.port))) #necessary to pass along server port since client port is different and randomly allocated
    
    def get_available_files(self, host, port):
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
        Receives messages from the client and sends a confirmation.
        
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

    
    def handle_client_file(self, client_socket):
        """
        Handles communication with a connected client. 
        Receives messages from the client and sends a confirmation.
        
        Parameters:
        - client_socket (socket): The socket object for the connected client.
        """
        print("here")
        header = client_socket.recv(4096).rstrip(b"\0") # strip padding bytes
        print(header.decode().strip())
        if not header or header.decode().strip() != "peerlist":
            print("peerlist responses must include a 4096 byte header with the word peerlist")
            sys.exit(1)
        message = b""
        while True:
            data = client_socket.recv(4096)
            if not data:  # Exit if no data is received
                break
            message += data
        peerlist = pickle.loads(message)
        print(peerlist)


    def connect_to_node(self, host, port):
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
        Sends a file to all connected peers.
        
        Parameters:
        - filename (str): The file to be sent to each peer.
        """
        client_socket.sendall(b"file_response")
        if filename not in self.files:
            client_socket.sendall("file not owned by this peer!") # this shouldn't happen if the tracker has an up to date peerlist
        filepath = self.files[filename]
        try:
            file = open(filepath)
            data = file.read(4096)
            print("about to send file")
            while data:
                print("sending file!")
                client_socket.sendall(data.encode())
                data = file.read(4096)
            file.close()
            client_socket.close()
        except Exception as e:
            print("error when sending file: " + str(e))

