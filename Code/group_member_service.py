import socket
import threading
from abc import abstractmethod
import pandas
import pickle
from uuid import uuid4
import time

import utils
import config as cfg
import pandas as pd


class group_member_service:
    def __init__(self, IP_ADDRESS: str,
                 iD,
                 UDP_PORT):
        self.id = iD
        self.IP_ADDRESS = IP_ADDRESS
        self.UDP_PORT = UDP_PORT
        self.TIM_PORT = UDP_PORT + 1
        self.ELE_PORT = UDP_PORT + 2
        self.GMS_PORT = UDP_PORT + 3
        self.server_list = None
        self.BUFFER_SIZE = cfg.attr['BUFFER_SIZE']
        self.HEARTBEAT_RATE = cfg.attr['HEARTBEAT_RATE']
        self.TERMINATE = False

    @staticmethod
    def add_instance(iD, addr, port, df: pd.DataFrame):
        tmp = pd.DataFrame({'ADDRESS': addr, 'PORT': port}, index=[iD])
        df = pd.concat([df, tmp], ignore_index=False)
        return df

    @abstractmethod
    def heartbeat_send(self):
        pass
        
    def heartbeat_listen(self, content: dict):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.IP_ADDRESS, self.GMS_PORT))
        while not self.TERMINATE:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                message = pickle.loads(data)
                # don't listen to yourself!
                if isinstance(message, pandas.DataFrame):
                    # if the datatype is pandas df, it will be a synchronize of serverlist
                    self.server_list = message
                else:
                    # if message['CONTENT']['ID'] == self.id:
                    #     continue
                    method = message['METHOD']
                    if method == 'HEAREQUEST':
                        reply = utils.create_message(self.id, 'HEAREPLY', content)
                        utils.udp_send_without_response(address, reply)
                    else:
                        print('Warning: Inappropriate message at heartbeat port.')

    def start_thread(self):
        self.threads = [self.heartbeat_listen, self.heartbeat_send]
        for th in self.threads:
            t = threading.Thread(target=th, daemon=True)
            t.start()

    def close(self):
        self.TERMINATE = True

class group_member_service_server(group_member_service):
    def __init__(self, IP_ADDRESS: str, iD, UDP_PORT, is_MAIN: bool):
        super().__init__(IP_ADDRESS, iD, UDP_PORT)
        self.TYPE = 'SERVER'
        self.is_main = is_MAIN
        self.server_list = \
            pd.DataFrame(columns=['ADDRESS', 'PORT', 'number_of_client', 'time_stamp']).astype(
                {'number_of_client': 'int32'}) if self.TYPE == 'SERVER' else None
        self.client_list = pd.DataFrame(columns=['ADDRESS', 'PORT', 'time_stamp']) if self.TYPE == 'SERVER' else None
        self.start_thread()

    def heartbeat_listen(self):
        content = {'ID': self.id,'CLIENTS': self.client_size()}
        return super().heartbeat_listen(content)

    def heartbeat_send(self):
        while not self.TERMINATE:
            message = utils.create_message(self.id, 'HEAREQUEST', {'ID': self.id, 'CLIENTS': self.client_size()})

            for address in self.get_server_address('UDP'):
                try:
                    response = utils.udp_send(utils.get_port(address, 'GMS'), message)

                    if response == None:
                        # our heartbeat request timed out, so we need to remove the server from our list
                        self.remove_server(self.address_to_id(self.server_list, address))
                        # TODO: Elect new main if the removed server was main
                    elif response['METHOD'] == 'HEAREPLY':
                        # we got exactly the response we expected, so we don't need to do anything
                        # and at the same time we update the number of clients
                        if self.is_main:
                            self.server_list['number_of_client'] = response['CONTENT']['CLIENTS']
                    else:
                        print('Warning: Inappropriate message at heartbeat port.')
                except ConnectionResetError:
                    # our heartbeat request crashed because the socket subsystem realised to server is gone, so we need to remove the server from our list
                    self.remove_server(self.address_to_id(self.server_list, address))
                    # TODO: Elect new main if the removed server was main
                    
            for address in self.get_client_address('UDP'):
                try:
                    response = utils.udp_send(utils.get_port(address, 'GMS'), message)

                    if response == None:
                        # our heartbeat request timed out, so we need to remove the client from our list
                        self.remove_client(self.address_to_id(self.client_list, address))
                    elif response['METHOD'] == 'HEAREPLY':
                        # we got exactly the response we expected, so we don't need to do anything
                        pass
                    else:
                        print('Warning: Inappropriate message at heartbeat port.')
                except ConnectionResetError:
                    # our heartbeat request crashed because the socket subsystem realised to client is gone, so we need to remove the client from our list
                    self.remove_client(self.address_to_id(self.client_list, address))

            # is the proccess is main, it will update all the server list in this function
            if self.is_main:
                self.group_synchronise()

            time.sleep(self.HEARTBEAT_RATE)
        
    def form_ring(self):
        # server list is a list of tuples (ip, port)
        # add uuid to each server(ip, port, uuid)
        # sort the list based on uuid
        # the end remove uuid
        ids, server_list = self.get_server_id()
        ring = [None] * len(server_list)
        for i in range(len(server_list)):
            server_list[i] = server_list[i] + (ids[i],)
        server_list.sort(key=lambda x: x[2])

        ring_uuid = server_list
        # remove uuid
        for i in range(len(ring_uuid)):
            ring[i] = server_list[i][:-1]
        return ring_uuid, ring

    def get_neighbour(self, ring, direction: bool = True):
        # get the neighbour of current node
        # direction can be left or right
        # return the neighbour ip and port
        # direction: True = Left
        current_node_ip = (self.IP_ADDRESS, self.UDP_PORT)
        current_node_index = ring.index(current_node_ip) if current_node_ip in ring else -1

        if current_node_index != -1:
            if direction:
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

    def LCR(self):
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
        ring_uuid, ring = self.form_ring()
        neighbour = self.get_neighbour(ring)
        neighbour = utils.get_port(neighbour, PORT='ELE')
        time.sleep(0.1)
        MY_IP = self.IP_ADDRESS
        ELE_PORT = self.ELE_PORT
        iD = ring_uuid[0][2]

        leader_uid = ""
        participant = False
        members = [...]

        ring_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ring_socket.bind((MY_IP, ELE_PORT))
        new_election_message = {"mid": iD, "isLeader": False}
        utils.udp_send_without_response(neighbour, new_election_message)

        while not self.TERMINATE:
            data, _ = ring_socket.recvfrom(self.BUFFER_SIZE)
            election_message = pickle.loads(data)
            print(election_message)
            if election_message["isLeader"]:
                leader_uid = election_message["mid"]
                # ring_socket.sendto(pickle.dumps(election_message), neighbour)
                utils.udp_send_without_response(neighbour, election_message)
                break
            if election_message["mid"] < iD and not participant:
                new_election_message = {"mid": iD, "isLeader": False}
                participant = True
                # send received election message to left neighbour
                # ring_socket.sendto(pickle.dumps(new_election_message), neighbour)
                utils.udp_send_without_response(neighbour, new_election_message)
            elif election_message["mid"] > iD:
                # send received election message to left neighbour
                participant = True
                # ring_socket.sendto(pickle.dumps(election_message), neighbour)
                utils.udp_send_without_response(neighbour, election_message)
            elif election_message["mid"] == iD:
                leader_uid = iD
                new_election_message = {"mid": iD, "isLeader": True}
                # send new election message to left neighbour
                participant = False
                # ring_socket.sendto(pickle.dumps(new_election_message), neighbour)
                utils.udp_send_without_response(neighbour, new_election_message)
        return leader_uid
        
    def address_to_id(self, node_list, address : tuple) -> int:
        for index, row in node_list.iterrows():
            if (row['ADDRESS'], row['PORT']) == address:
                return index
                
        return None

    def set_udp_port(self, address: tuple):
        self.UDP_PORT = address

    def add_server(self, iD, addr: tuple, **kwargs):
        self.server_list = self.add_instance(iD, addr[0], addr[1], self.server_list)
        self.server_list.loc[iD, 'number_of_client'] = 0
        for ele in kwargs:
            self.server_list.loc[iD, ele] = kwargs[ele]
        self.group_synchronise()

    def add_client(self, iD, addr: tuple, **kwargs):
        self.client_list = self.add_instance(iD, addr[0], addr[1], self.client_list)
        for ele in kwargs:
            self.client_list.loc[iD, ele] = kwargs[ele]
        # increase the number of clients in server
        self.server_list.loc[self.id, 'number_of_client'] += 1

    def remove_server(self, iD):
        self.server_list = self.server_list.drop(iD, axis=0)

    def remove_client(self, iD):
        self.client_list = self.client_list.drop(iD, axis=0)

    def print_server(self):
        with pd.option_context('display.max_rows', None, 'display.max_columns',
                               None):
            print(self.server_list)

    def print_client(self):
        with pd.option_context('display.max_rows', None, 'display.max_columns',
                               None):
            print(self.client_list)

    def client_size(self):
        return len(self.client_list)

    def server_size(self):
        return len(self.server_list)

    def get_client_address(self, TYPE: str = 'UDP') -> list:
        """
        HELPER FUNCTION
        Get all the addresses of clients that store in the gms
        :param TYPE: specify the port you want to get
        :return: a list of tuple address
        """
        tmp = []
        for _, row in self.client_list.iterrows():
            result = (row['ADDRESS'], row['PORT'])
            tmp.append(utils.get_port(result, TYPE))
        return tmp

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

    def get_server_id(self):
        """
        HELPER FUNCTION
        Get all the id of servers that store in the gms
        :return: a list of tuple id
        """
        return self.server_list.index.tolist(), self.get_server_address()

    def get_all_address(self, TYPE: str = 'UDP'):
        return self.get_server_address(TYPE) + self.get_client_address(TYPE)

    def is_member(self, iD, TYPE: str = 'SERVER') -> bool:
        """
        HELPER FUNCTION
        determine whether the iD appears in the dataframe
        :param iD: the iD string of the process
        :param TYPE: either 'SERVER' or 'CLIENT'
        :return:
        """
        if TYPE == 'SERVER':
            return iD in self.server_list.index
        elif TYPE == 'CLIENT':
            return iD in self.client_list.index
        else:
            raise ValueError('TYPE can only be "SERVER" or "CLIENT"!')

    def assign_clients(self) -> tuple:
        """
        HELPER FUNCTION
        return the server address with the least number of clients
        :return:
        """
        num = self.server_list['number_of_client'].argmin()
        iD = self.server_list.index[num]
        addr = tuple(self.server_list.loc[iD, ['ADDRESS', 'PORT']])
        return iD, addr

    def remote_synchronise(self, address: tuple) -> None:
        """
        HELPER FUNCTION
        synchronize the pandas dataframe with the object address
        :param address: the address of the process you want to sync with
        :return:
        """
        utils.udp_send_without_response(address, self.server_list)

    def group_synchronise(self) -> None:
        """
        HELPER FUNCTION
        synchronize with all the servers
        :return:
        """
        for member in self.get_server_address('GMS'):
            utils.udp_send_without_response(member, self.server_list)


class group_member_service_client(group_member_service):
    def __init__(self, IP_ADDRESS: str, iD, UDP_PORT):
        super().__init__(IP_ADDRESS, iD, UDP_PORT)
        self.TYPE = 'CLIENT'
        self.CONTACT_SERVER = None
        self.start_thread()

    def heartbeat_send(self):
        while not self.TERMINATE:
            message = utils.create_message(self.id, 'HEAREQUEST', {'ID': self.id})

            # todo

            time.sleep(self.HEARTBEAT_RATE)
    
    def heartbeat_listen(self):
        content = {'ID': self.id}
        return super().heartbeat_listen(content)


def main():
    iD = str(uuid4())
    gms = group_member_service_server('192.168.0.200', iD, 123)
    gms.add_server(str(uuid4()), ('192.168.0.200', 123), time_stamp='asdf')
    gms.add_server(str(uuid4()), ('123.123.123.111', 1111), number_of_client=3)
    gms.add_server(str(uuid4()), ('123.123.123.222', 2222), time_stamp='a123')
    gms.add_server(str(uuid4()), ('123.123.123.123', 3333))
    gms.add_server(str(uuid4()), ('123.123.123.112', 4444))
    gms.print_server()
    ring_with_id, ring = gms.form_ring()
    print(ring_with_id)
    neighbour = gms.get_neighbour(ring=ring, direction=False)
    print(neighbour)
    gms.LCR()


if __name__ == '__main__':
    main()
