import utils
import socket
import uuid
import json

BUFFER_SIZE = 4096

def get_server_address(self, TYPE: str = 'UDP') -> list:
        """
        HELPER FUNCTION
        Get all the addresses of servers that store in the gms
        :param TYPE: specify the port you want to get
        :return: a list of tuple address
        """
        tmp = []
        for _, row in self.server_list.iterrows():
            result = (row['ADDRESS'], row['PORT'])
            tmp.append(utils.get_port(result, TYPE))
        return tmp

def form_ring(server_list):

    # leader election with ring formation
    # server_list is a list of tuples (ip, port)
    # add uuid to each server (ip, port, uuid)
    # sort the list by uuid
    # remove uuid

    for i in range(len(server_list)):
        server_list[i] = server_list[i] + (uuid.uuid4(),)
    server_list.sort(key=lambda x: x[2])
    # remove uuid
    for i in range(len(server_list)):
        server_list[i] = server_list[i][:-1]

    print("Ring formed:", server_list)
    return server_list

def get_neighbours(ring, current_node_ip, direction='left'):
    # get the neighbours of current node
    # direction: left or right
    # return the neighbour ip and port

    current_node_index = ring.index(current_node_ip) if current_node_ip in ring else -1 
    if current_node_index != -1:
        if direction == 'left':
            if current_node_index + 1 == len(ring):
                return ring[0] 
            else:
                return ring[current_node_index + 1] 
        else:
            if current_node_index == 0: 
                return ring[len(ring) - 1]
            else:
                return ring[current_node_index - 1] 
    else:
        return None

def LCR(ring_uuid, neighbour):
    # LCR algorithm
    # ring_uuid is the ring with uuid
    # neighbour is the neighbour of current node
    # return the leader
 
    # leader election with LaLann-Chang-Roberts algorithm
    # return the leader ip and port
 
    # each node broadcast the uuid to the neighbour
    # if the neighbour uuid is greater than the current node uuid, then node send a pass message to the neighbour,
    # else node send a stop message to the neighbour
    # if the node receive a stop message, then node stop sending its own uuid to the neighbour,
    # else receive a pass message, then node continue sending(broadcast) its own uuid to the neighbour
    # eventually the node with the largest uuid will be the leader
 
    # my_ip = "183.38.223.1"
    # id = "aed937ea-33f3-11eb-adc1-0242ac120002"  (my_id)
    # ring_port = 10001
 
    MY_IP = get_ip_adress()
    BROADCAST_PORT = 5972
    id = ring_uuid[0]
 
    leader_uid = ""
    participant = False
    members = [...]
    ring_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ring_socket.bind((MY_IP, BROADCAST_PORT))
    print("Node is up and running at {}:{}".format(MY_IP, BROADCAST_PORT))
 
    print("\nWaiting to receive election message...\n")
    data, address = ring_socket.recvfrom(BUFFER_SIZE)
    election_message = json.loads(data.decode())
    if election_message["isLeader"]:
        leader_uid = election_message["mid"]
        # forward received election message to left neighbour
        participant = False
        ring_socket.sendto(json.dumps(election_message), neighbour)
    if election_message["mid"] < id and not participant:
        new_election_message = {"mid": id, "isLeader ": False}
        participant = True
        # send received election message to left neighbour
        ring_socket.sendto(json.dumps(new_election_message), neighbour)
    elif election_message["mid"] > id:
        # send received election message to left neighbour
        participant = True
        ring_socket.sendto(json.dumps(election_message), neighbour)
    elif election_message["mid"] == id:
        leader_uid = id
        new_election_message = {"mid": id, "isLeader ": True}
    # send new election message to left neighbour
    participant = False
    ring_socket.sendto(json.dumps(new_election_message), neighbour)
    print("Leader is: {}".format(leader_uid))
 
    return leader_uid




def main():
    server_list = [('192.168.0.0', 5766), ('192.168.0.1', 5750), ('192.168.0.2', 5780), ('192.170.0.24', 5700)]
    ring = form_ring(server_list)
    neighbour = get_neighbours(ring, ('192.170.0.24', 5700), 'left')
    print(neighbour)
    neighbour2 = get_neighbours(ring, ('192.168.0.1', 5750), 'right')
    print(neighbour2)
    neighbour3 = get_neighbours(ring, ('192.168.0.1', 5750), 'left')
    print(neighbour3)
    neighbour4 = get_neighbours(ring, ('192.168.0.2', 5780), 'left')
    print(neighbour4)
    # LCR(ring, neighbour)
   

if __name__ == '__main__':
    main()