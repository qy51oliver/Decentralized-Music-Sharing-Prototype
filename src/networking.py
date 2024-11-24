import math
import os
import pickle
import random
import socket
import sys
import threading
import time
import hashlib

HEARTBEAT_INTERVAL_SECONDS = 20
DOWNLOAD_POOL_SIZE = 4 # attempt to download 4kb chunks of the file in concurrent pools of this size

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
        self.peer_dict = {} # key=filename, val=set of tuples (ip, port) that have the file available
        self.file_data = {} # key=filename, val=(hash, size)
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
                print(message.decode())

            if request_type == "register": #register ownership of a file to a node, making it available for peer downloads
                host, _ = client_socket.getpeername()
                str_message = message.decode().split(",") # message is sent in format filename,host_port (since client port is random, not server port)
                filename = str_message[0]
                hash = str_message[1]
                size = int(str_message[2])
                port = int(str_message[3])
                if filename not in self.file_data:
                    self.file_data[filename] = (hash, size)
                elif self.file_data[filename] != (hash, size):
                    client_socket.sendall(b"err: there is already a file registered under this filename that has different contents")
                    return
            
                if filename not in self.peer_dict:
                    self.peer_dict[filename] = set()
                elif (host, port) in self.peer_dict[filename]:
                    client_socket.sendall(b"err: this client has already registered ownership of this file with the tracker")
                    return
                
                self.peer_dict[filename].add((host, port))
                self.last_heartbeat[(host, port)] = time.time()
                client_socket.sendall(str.encode("Filename " + filename + " registered to " + host + ", " + str(port)))         
            elif request_type == "view_available": #view which files have been registered by nodes and are available to download
                client_socket.sendall(str.encode(str(list(self.peer_dict.keys()))))   
            elif request_type == "get": # coordinate a file download
                str_message = message.decode().split(",") # message is sent in format filename,host_port (since client port is random, not server port)
                filename = str_message[0]
                host, _ = client_socket.getpeername()
                port = int(str_message[1])
                if filename not in self.peer_dict:
                    print("The requested file has no peers registered to it")
                else:
                    peerlist = list(self.peer_dict[filename])
                    client_socket.sendall(pickle.dumps(peerlist))
                    print("Peerlist for file " + filename + " sent to " + host + ":" + str(port))
            elif request_type == "heartbeat":
                port = int(message.decode())
                host, _ = client_socket.getpeername()
                self.last_heartbeat[(host, port)] = time.time()
                print(f"Heartbeat received from {host}:{port}")
            elif request_type == "size":
                filename = message.decode()
                client_socket.sendall(str(self.file_data[filename][1]).encode())
    
    def remove_stale_peers(self):
        """
        Periodically removes peers that have not sent a heartbeat within a certain time.
        """
        while True:
            time.sleep(10) # Check every 10 seconds
            current_time = time.time()
            timeout = HEARTBEAT_INTERVAL_SECONDS * 2 # consider a peer to be dropped if it doesn't send a heartbeat within 2x the interval
            for filename in list(self.peer_dict.keys()):
                updated_peers = set()
                removed_peers = set()
                for host, port in self.peer_dict[filename]:
                    # Check if the peer's last heartbeat is within the timeout
                    last_heartbeat = self.last_heartbeat.get((host, port), 0)
                    if current_time - last_heartbeat <= timeout:
                        updated_peers.add((host, port))
                    else:
                        removed_peers.add((host, port))
                if len(updated_peers) == 0:
                    del self.peer_dict[filename]
                else:
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
        self.files = {} # key=filename, value=path, filename is any string identifier for the file which should be globally constant, while path is specific to the node's host machine
        self.trackers = set() # trackers this peer has registered a file with
        self.lock = threading.Lock() # lock for what would otherwise be thread-unsafe operations (as of right now, only adding to tracker set)

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
            print("REGISTER <filename> <src_filepath> <host> <port>\n\tregister ownership of the file with the identifier filename and path filepath to yourself with the tracker at the specified IP and port")
            print("VIEW_AVAILABLE <host> <port>\n\tview files that have been registered with the tracker and are available to be downloaded")
            print("GET <filename> <dst_filepath> <host> <port>\n\task tracker at host and port to coordinate a download of filename from a peer to local path filepath")
            
            threading.Thread(target=self.handle_user_input).start()
            threading.Thread(target=self.send_heartbeats).start()
            while True:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
    
    def send_heartbeats(self):
        while True:
            offline_trackers = set()
            for host, port in self.trackers:
                try:
                    tracker_socket = self.connect_to_node(host, port)
                    header = b"heartbeat"
                    header += b"\0" * (4096-len(header)) #padding
                    tracker_socket.sendall(header)
                    tracker_socket.sendall(str.encode(str(self.port)))
                    tracker_socket.close()
                except:
                    offline_trackers.add((host, port))
            if len(offline_trackers) > 0:
                with self.lock:
                    self.trackers.difference_update(offline_trackers)
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    def handle_user_input(self):
        """
        Allows the user to input commands to a peer node's CLI, and handles those commands appropriately.
        """
        while True:
            command = input("\nWhat would you like to do?\n").strip().lower()
            command_split = command.split(" ")
            if command_split[0] == "register":
                filename = command_split[1]
                filepath = os.path.abspath(command_split[2])
                host = command_split[3]
                port = int(command_split[4])
                if os.path.isfile(filepath):
                    hash = hashlib.md5(open(filepath,'rb').read()).hexdigest()
                    size = os.path.getsize(filepath)
                    self.register_with_tracker(filename, filepath, hash, size, host, port)
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
                    self.download_file_from_peer(peerlist, filename, filepath, host, port)

    def get_file_size(self, filename, tracker_host, tracker_port):
        tracker_socket = self.connect_to_node(tracker_host, tracker_port)
        header = b"size"
        header += b"\0" * (4096-len(header)) #padding
        tracker_socket.sendall(header)
        tracker_socket.sendall(filename.encode())
        resp = tracker_socket.recv(4096).decode()
        size = int(resp)
        return size
    
    def download_chunk_from_peer(self, peer_host, peer_port, filename, downloaded_chunks, current_chunk, error):
        offset = current_chunk * 4096
        print("downloading chunk offset " + str(offset))
        try:
            peer_socket = self.connect_to_node(peer_host, peer_port)
            header = b"file_request"
            header += b"\0" * (4096-len(header)) #padding
            peer_socket.send(header)
            peer_socket.send(str.encode(filename+","+str(offset)))
            resp_header = peer_socket.recv(4096).rstrip(b"\0").decode()
            if resp_header != "file_response":
                raise Exception("file response header is malformed")
            chunk = peer_socket.recv(4096)
            downloaded_chunks[current_chunk] = chunk
        except:
            with self.lock:
                error.add(current_chunk)
    
    def download_file_from_peer(self, peerlist, filename, filepath, tracker_host, tracker_port):
        """
        Initiates a peer-to-peer download.
        Pick a peer from the peerlist, request that peer to send the file filename, and download it to dst filepath.
        
        Parameters:
        - peerlist (list(tuple(str, int))): A list of peers with the file filename.
        - filename (str): The filename to be downloaded
        - filepath (str): The dst path to download the file to.
        """
        
        file_size = self.get_file_size(filename, tracker_host, tracker_port)
        num_chunks = math.ceil(file_size / 4096)
        downloaded_chunks = [b""] * num_chunks
        pool_size = min(DOWNLOAD_POOL_SIZE, len(peerlist)) # try and download in batches
        for starting_chunk in range(0, num_chunks, pool_size):
            curr_pool_size = min(pool_size, num_chunks-starting_chunk)
            peer_pool = random.sample(peerlist, curr_pool_size)
            error = set()
            thread_pool = [threading.Thread(target=self.download_chunk_from_peer, args=(peer_pool[chunk_number-starting_chunk][0], peer_pool[chunk_number-starting_chunk][1], filename, downloaded_chunks, chunk_number, error)) for chunk_number in range(starting_chunk, starting_chunk+curr_pool_size)]
            for thread in thread_pool:
                thread.start()
            for thread in thread_pool:
                thread.join()
            if len(error) > 0:
                attempts = 0
                print(len(error), " chunks failed to download, retrying...")
                while attempts < 3 and len(error) > 0:
                    print("attempt ", attempts, " to download ", len(error), " erroring chunks")
                    new_error = set()
                    thread_pool = [threading.Thread(target=self.download_chunk_from_peer, args=(peer_pool[chunk_number-starting_chunk][0], peer_pool[chunk_number-starting_chunk][1], filename, downloaded_chunks, chunk_number, new_error)) for chunk_number in error]
                    for thread in thread_pool:
                        thread.start()
                    for thread in thread_pool:
                        thread.join()
                    attempts += 1
                    error = new_error
                if len(error) > 0:
                    print("failed to download the file: some chunks are unreachable")
                    return
        with open(filepath, 'wb') as downloaded_file:
            for chunk in downloaded_chunks:
                downloaded_file.write(chunk)

        hash = hashlib.md5(open(filepath,'rb').read()).hexdigest()
        size = os.path.getsize(filepath)
        self.register_with_tracker(filename, filepath, hash, size, tracker_host, tracker_port)

    def register_with_tracker(self, filename, filepath, hash, size, host, port):
        """
        Registers the file represented by filename with the tracker at host and port.
        This signals to the tracker that the client possesses ownership of the file and can be counted on to distribute it to peers.
        
        Parameters:
        - filename (str): The filename being registered
        - hash (str): A MD5 hash of the contents of the file
        - size (int): the size of the file in bytes
        - host (str): The IP of the tracker.
        - port (int): The port of the tracker.
        """
        header = b"register"
        header += b"\0" * (4096-len(header)) #padding
        tracker_socket = self.connect_to_node(host, port)
        tracker_socket.sendall(header)
        tracker_socket.sendall(str.encode(filename+","+hash+","+str(size)+","+str(self.port))) #necessary to pass along server port since client port is different and randomly allocated
        resp = tracker_socket.recv(4096).decode()
        if "err" in resp:
            print("There was an error while attempting to register the file: " + resp)
        else:
            print(resp)
            with self.lock:
                self.files[filename] = filepath
                self.trackers.add((host, port))
    
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
                    filename, offset = client_socket.recv(4096).decode().split(",")
                    offset = int(offset)
                    self.send_file_chunk(filename, client_socket, offset)
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
            except ConnectionRefusedError:
                print(f"Failed to connect to {peer_host}:{peer_port}")

    def send_file_chunk(self, filename, client_socket, offset):
        """
        Sends a 4KB chunk of file filename to client_socket.
        
        Parameters:
        - filename (str): The file to be sent.
        - client_socket (socket): The socket to send the connection to.
        - offset(int): the byte offset to read the chunk from
        """
        header = b"file_response"
        header += b"\0" * (4096-len(header))
        client_socket.sendall(header)
        info_offset = str(offset).encode()
        info_offset += b"\0" * (4096-len(info_offset))
        if filename not in self.files:
            client_socket.sendall(b"file not owned by this peer!") # this shouldn't happen if the tracker has an up to date peerlist
        filepath = self.files[filename]
        try:
            file = open(filepath, 'rb')
            file.seek(offset)
            data = file.read(4096)
            client_socket.sendall(data)
            # while data:
            #     client_socket.sendall(data)
            #     data = file.read(4096)
            file.close()
            client_socket.close()
        except Exception as e:
            print("error when sending file: " + str(e))

