# Decentralized Music Sharing Prototype

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Comments](#comments)

---

## Overview

The **Decentralized Music Sharing Prototype** is a peer-to-peer (P2P) file-sharing system inspired by the BitTorrent protocol. Initially focused on music sharing, it evolved into a framework for sharing files of any format. The system leverages a tracker node to facilitate peer discovery and decentralized file sharing, ensuring data consistency and reliability.

The system uses a central tracker node to maintain a registry of files and their associated peers. Peers can:

- Register files they host.
- Query the tracker for peers hosting a requested file.
- Download files in chunks from multiple peers simultaneously.

## Features

### Implemented Features

1. **Tracker Nodes**:
  - Maintains a centralized registry of files and associated peers.
  - Validates file integrity using hash checks during registration.
  - Removes stale peers using a heartbeat mechanism.
2. **Peer-to-Peer File Sharing**:
  - Supports downloading files in 4KB chunks from multiple peers simultaneously.
  - Reattempts failed chunk downloads up to three times to ensure fault tolerance.
3. **Concurrency:**:
  - Multi-threaded download pools to enhance efficiency.
4. **Dynamic Node Management**:
  - Allows peers to join or leave the network dynamically.

### Planned Features

1. **File Prioritization**:
  - Introduce incentives mechanisms, such as tit-for-tat.
2. **Scalability**:
  - Optimize performance for larger networks.

## Project Structure

The project structure is currently organized as follows:

```plaintext
Decentralized-Music-Sharing-Prototype/
├── src/
│   ├── networking.py
│   └── main.py               
├── README.md                 
├── .gitignore                
```

## Getting Started


### Starting a Node

```plaintext
python src/main.py <host> <port> <peer/tracker>
```

- < host >: The IP address of the node.
- < port >: The port number to bind the node.
- < peer / tracker >: Specify whether the node acts as a peer or a tracker.

### Commands for a Peer Node

Register a file:
```plaintext
REGISTER <filename> <src_filepath> <tracker_host> <tracker_port>
```
Register a file with the tracker, providing the filename and its path.

View available files:
```plaintext
VIEW_AVAILABLE <tracker_host> <tracker_port>
```
List all files currently registered with the tracker.

Download a file:
```plaintext
GET <filename> <dst_filepath> <tracker_host> <tracker_port>
```
Download a file from peers listed by the tracker.


## Comments
