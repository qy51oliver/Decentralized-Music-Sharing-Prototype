# Decentralized Music Sharing Prototype

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Implementation Details](#code-details)
- [Testing](#testing)
- [Comments](#comments)

---

## Overview

The **Decentralized Music Sharing Prototype** is a peer-to-peer (P2P) file-sharing system focused on creating a basic, decentralized network for music sharing. This prototype uses P2P networking principles to allow nodes (peers) to connect, communicate, and share data with each other without relying on a central server. 

### Goals

- **Peer Connections**: Set up a network where peers can connect directly to each other, without a central server.

- **Basic File Sharing**: Let peers share music files with each other directly. The idea is to keep it simple but effective in sending files between connected users.

- **Consistency Across Peers**: Make sure files are consistent across the network so everyone has the same version. This might mean adding some checks to keep everything in sync.

- **Easy Network Expansion**: New users should be able to join the network smoothly, and the network should still work well as more people connect.

- **Reliable Connections**: Add basic checks for handling errors, like dropped connections or failed messages, so the network keeps running smoothly.

## Features

### Implemented Features (not tested)

1. **Peer-to-Peer Connections**: Nodes can connect directly to other peers using an IP address and port.
2. **Basic Message Exchange**: Nodes can send and receive simple messages from other connected peers.
3. **Dynamic Node Addition**: New nodes can join the network and connect to existing peers.

### To-do (add here)

1. **File Sharing**: Extend functionality to support the transfer of music files directly between peers.
2. **Data Consistency**: Ensure files remain consistent across nodes, so each peer has the latest versions.
3. **Improved Scalability**: Optimize the network to maintain performance as more nodes join and the network grows.
4. **Basic Error Handling**: Implement simple error-handling to manage connection issues or message failures, making the network more resilient.

## Project Structure (current, subject to change)

The project structure is currently organized as follows:

```plaintext
Decentralized-Music-Sharing-Prototype/
├── src/
│   ├── networking.py         # Currently, PeerNode inside this file.
│   └── main.py               
├── README.md                 
├── .gitignore                
```

## Getting Started

### Install Dependencies

1. Please save the installed depenencies to requirements.txt (Currently, there are no external libraries required beyond Python's standard library.
)


### Start running

```plaintext
python src/main.py <host> <port>
```

### Connecting to Other Nodes:



## Implementation Details


## Testing



## Comments