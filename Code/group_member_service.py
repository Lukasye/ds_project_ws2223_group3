import random
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
    def __init__(self, origin,
                 IP_ADDRESS: str,
                 iD,
                 UDP_PORT):
        self.id = iD
        self.IP_ADDRESS = IP_ADDRESS
        self.MULTICAST_PORT = cfg.attr['MULTICAST_PORT']
        self.UDP_PORT = UDP_PORT
        self.TIM_PORT = UDP_PORT + 1
        self.ELE_PORT = UDP_PORT + 2
        self.GMS_PORT = UDP_PORT + 3
        self.ORIGIN = origin
        self.MAIN_SERVER = None
        self.server_list = None
        self.BUFFER_SIZE = cfg.attr['BUFFER_SIZE']
        self.HEARTBEAT_RATE = cfg.attr['HEARTBEAT_RATE']
        self.TERMINATE = False
        self.is_member = False
        self.threads = []
        self.sequencer = 0

    @staticmethod
    def add_instance(iD, addr, port, df: pd.DataFrame):
        tmp = pd.DataFrame({'ADDRESS': addr, 'PORT': port}, index=[iD])
        df = pd.concat([df, tmp], ignore_index=False)
        return df

    @abstractmethod
    def heartbeat_send(self):
        pass

    @abstractmethod
    def heartbeat_listen(self) -> None:
        pass

    def start_thread(self):
        self.threads = [self.heartbeat_listen, self.heartbeat_send]
        for th in self.threads:
            t = threading.Thread(target=th, daemon=True)
            t.start()

    def close(self):
        self.TERMINATE = True


class group_member_service_server(group_member_service):
    def __init__(self, origin, IP_ADDRESS: str, iD, UDP_PORT, is_MAIN: bool, MAIN_SERVER: tuple):
        super().__init__(origin, IP_ADDRESS, iD, UDP_PORT)
        self.TYPE = 'SERVER'
        self.is_main = is_MAIN
        self.MAIN_SERVER = MAIN_SERVER
        if self.is_main:
            self.is_member = True
        self.server_list = \
            pd.DataFrame(columns=['ADDRESS', 'PORT', 'number_client']).astype(
                {'number_client': 'int32'}) if self.TYPE == 'SERVER' else None
        self.client_list = pd.DataFrame(columns=['ADDRESS', 'PORT']) if self.TYPE == 'SERVER' else None
        self.in_election = False
        self.hungury = 0
        self.isolated = False
        self.test_intercept = False
        self.start_thread()

    def heartbeat_listen(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.IP_ADDRESS, self.GMS_PORT))
        while not self.TERMINATE:
            # if we're disconnected we want the servers to realize that 
            # if self.is_member:
            if True:
                data, address = server_socket.recvfrom(self.BUFFER_SIZE)
                if data:
                    message = pickle.loads(data)
                    t = threading.Thread(target=self.heartbeat_listen_logic, args=(message, address), daemon=True)
                    t.start()
                    # self.heartbeat_listen_logic(message=message, address=address)

    def heartbeat_listen_logic(self, message: dict, address):
        # don't listen to yourself!
        if isinstance(message, pandas.DataFrame):
            # if the datatype is pandas df, it will be a synchronized of serverlist
            self.server_list = message
        else:
            method = message['METHOD']
            if method == 'HEAREQUEST':
                if self.is_listed(message['ID'], 'UNKNOWN') or not self.is_member:
                    content = {'ID': self.id, 'CLIENTS': self.client_size(),
                                'MAIN_SERVER': self.MAIN_SERVER}
                    reply = utils.create_message(self.id, 'HEAREPLY', content)
                    utils.udp_send_without_response(address, reply)
            elif method == 'UPDATE':
                # now id the only for clients feature, to update the MAIN_SERVER
                self.MAIN_SERVER = message['CONTENT']['MAIN_SERVER']
            else:
                # print('Warning: Inappropriate message at heartbeat port.')
                utils.colorful_print('Warning: Inappropriate message at heartbeat port.', 'FAIL')


    def handle_disconnect(self, address) -> None:
        """
        HELPER FUNCTION:
        If the process leave the system, delete it from the gms list. If it is the main server
        run the election algorithm to get a new leader
        :param address: the id of the disconnected server. There maybe a naming error
        :return: None
        """
        self.ORIGIN.logging.warning(f'Lose connection with {address}')
        try:
            self.remove_server(self.address_to_id(self.server_list, address))
        except:
            print('Remove failed!')
        print(address, ' Has disconnected with the group!')
        # self.isolation_check()
        if self.MAIN_SERVER == address:
            print('Main server lose!')
            if self.server_size() == 1 and self.client_size() > 0:
                # if we only know of a single existing server, ourselves, we need to take over as the main server
                self.MAIN_SERVER = (self.IP_ADDRESS, self.UDP_PORT)
                self.is_main = True
                self.is_member = True
                self.update_state()
            else:
                self.MAIN_SERVER = None
                # if the election fails, runn the election again, until we get the result
                counter = 0
                while self.MAIN_SERVER is None:
                # while self.MAIN_SERVER is None and not self.in_election:
                    self.election()
                    time.sleep(random.random())
                    counter += 1
                    if counter >= 6:
                        utils.colorful_print('System failure! Leave the system!', 'FAIL')
                        self.leave_main()
                        return

    def isolation_check(self) -> bool:
        # if there is also no clients in the server, there is a great chance that the server is isolated
        # So it needs to find a new group again.
        flag = self.server_size() == 1 and self.client_size() == 0
        if flag:
            self.leave_main()
        return flag

    def election(self):
        if self.isolated:
            utils.colorful_print('Isolation checked! Election cannot be invoked!', 'FAIL')
            # print('Isolation checked! Election cannot be invoked!')
            # self.leave_main()
            return False
        self.group_synchronise()
        command = 'self.gms.LCR();self.gms.update_state();'
        self.ORIGIN.remote_methode_invocation(self.get_server_address(), command, multicast=True, result=False)

    def leave_main(self):
        self.MAIN_SERVER = None
        self.is_member = False
        self.is_main = False

    def declare_main(self):
        command = f'self.is_main=False;self.MAIN_SERVER={tuple(self.MAIN_SERVER)};'
        self.ORIGIN.remote_methode_invocation(self.get_server_address(), command, multicast=True, result=False)

    def heartbeat_send(self):
        while not self.TERMINATE:
            message = utils.create_message(self.id, 'HEAREQUEST', {'ID': self.id, 'CLIENTS': self.client_size(),
                                                                   'ADDRESS': (self.IP_ADDRESS, self.UDP_PORT)})
            # If the process is isolated, just send out the dynamic discovery
            # if self.isolated:
            #     self.leave_main()
            #     self.ORIGIN.find_others()
            #     return

            # if the process don't have a main_server, find one
            if self.MAIN_SERVER is None:
                self.ORIGIN.find_others()
                if self.hungury == 0:
                    self.hungury = time.time()
                elif time.time() - self.hungury > 3 * self.HEARTBEAT_RATE:
                    # we assumed that there is no main server in the group
                    self.election()
                    if self.MAIN_SERVER is not None:
                        self.declare_main()
            else:
                self.hungury = 0
            
            inverse_trigger = True

            for address in self.get_server_address('UDP', without=[self.id]):
                try:
                    response = utils.udp_send(utils.get_port(address, 'GMS'), message)
                    inverse_trigger = False

                    if response is None:
                        # our heartbeat request timed out, so we need to remove the server from our list
                        self.handle_disconnect(address)
                    elif response['METHOD'] == 'HEAREPLY':
                        # we got exactly the response we expected, so we don't need to do anything
                        # and at the same time we update the number of clients
                        if self.is_main:
                            iD = self.address_to_id(self.server_list, address=address)
                            self.server_list.loc[iD, 'number_client'] = response['CONTENT']['CLIENTS']
                    else:
                        # print('Warning: Inappropriate message at heartbeat port.')
                        utils.colorful_print('Warning: Inappropriate message at heartbeat port.', 'FAIL')
                except ConnectionResetError:
                    # our heartbeat request crashed because the socket subsystem realised to server is gone,
                    # so we need to remove the server from our list
                    self.handle_disconnect(address)

            for address in self.get_client_address('UDP'):
                try:
                    response = utils.udp_send(utils.get_port(address, 'GMS'), message)
                    inverse_trigger = False

                    if response is None:
                        # our heartbeat request timed out, so we need to remove the client from our list
                        self.remove_client(self.address_to_id(self.client_list, address))
                    elif response['METHOD'] == 'HEAREPLY':
                        # we got exactly the response we expected, so we don't need to do anything
                        pass
                    else:
                        # print('Warning: Inappropriate message at heartbeat port.')
                        utils.colorful_print('Warning: Inappropriate message at heartbeat port.', 'FAIL')
                except ConnectionResetError:
                    # our heartbeat request crashed because the socket subsystem realised to client is gone,
                    # so we need to remove the client from our list
                    self.remove_client(self.address_to_id(self.client_list, address))

            self.isolated = inverse_trigger
            # print(self.isolated)
            self.ORIGIN.check_semaphore()

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
        """
        HELPER FUNCTION
        get the neighbour of current node
        :param ring: list of nodes
        :param direction: True = Left. Boolean variable to show the direction of neighbour in a ring
        :return: the neighbour ip and port
        """
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

    def LCR(self, timeout: int = 5):
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
        # print('Election started!')
        utils.colorful_print('Election started!', 'FAIL')
        if self.in_election:
            return None
        self.in_election = True
        ring_uuid, ring = self.form_ring()
        # print(ring_uuid)
        neighbour = self.get_neighbour(ring)
        neighbour = utils.get_port(neighbour, PORT='ELE')
        # print('Neighbour', neighbour)
        time.sleep(0.1)
        MY_IP = self.IP_ADDRESS
        ELE_PORT = self.ELE_PORT
        iD = ring_uuid[0][2]

        leader_uid = ""
        participant = False

        ring_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ring_socket.bind((MY_IP, ELE_PORT))
        new_election_message = {"mid": iD, "isLeader": False}
        utils.udp_send_without_response(neighbour, new_election_message)
        ring_socket.settimeout(timeout)

        while not self.TERMINATE:
            try:
                data, _ = ring_socket.recvfrom(self.BUFFER_SIZE)
            except socket.timeout:
                # print('Elction timeout!')
                utils.colorful_print('Elction timeout!', 'FAIL')
                self.in_election = False
                return None
            # used for testing, block the whole ring
            if self.test_intercept:
                self.test_intercept = False
                continue
            election_message = pickle.loads(data)
            # print(election_message)
            if election_message["isLeader"]:
                leader_uid = election_message["mid"]
                utils.udp_send_without_response(neighbour, election_message)
                break
            if election_message["mid"] < iD and not participant:
                new_election_message = {"mid": iD, "isLeader": False}
                participant = True
                utils.udp_send_without_response(neighbour, new_election_message)
            elif election_message["mid"] > iD:
                participant = True
                utils.udp_send_without_response(neighbour, election_message)
            elif election_message["mid"] == iD:
                leader_uid = iD
                new_election_message = {"mid": iD, "isLeader": True}
                participant = False
                utils.udp_send_without_response(neighbour, new_election_message)
        self.MAIN_SERVER = self.id_to_address(leader_uid)
        self.is_main = self.id == leader_uid
        self.is_member = True
        self.sequencer = self.ORIGIN.sequence_counter - 1
        self.in_election = False
        print('Election result: ', leader_uid)
        ring_socket.close()
        return leader_uid

    @staticmethod
    def address_to_id(node_list, address: tuple):
        for index, row in node_list.iterrows():
            if (row['ADDRESS'], row['PORT']) == address:
                return index
        return None

    def id_to_address(self, iD: str):
        if iD in self.server_list.index:
            return self.server_list.loc[iD, 'ADDRESS'], self.server_list.loc[iD, 'PORT']
        return None

    def set_udp_port(self, address: tuple):
        self.UDP_PORT = address

    def add_server(self, iD, addr: tuple, synch=True, **kwargs):
        # if the server already exists, ignore it
        if self.is_listed(iD, TYPE='SERVER'):
            return
        self.server_list = self.add_instance(iD, addr[0], addr[1], self.server_list)
        self.server_list.loc[iD, 'number_client'] = 0
        for ele in kwargs:
            self.server_list.loc[iD, ele] = kwargs[ele]
        if synch:
            self.group_synchronise()

    def add_client(self, iD, addr: tuple, **kwargs):
        if self.is_listed(iD, TYPE='CLIENT'):
            return
        self.client_list = self.add_instance(iD, addr[0], addr[1], self.client_list)
        for ele in kwargs:
            self.client_list.loc[iD, ele] = kwargs[ele]
        # increase the number of clients in server
        self.server_list.loc[self.id, 'number_client'] += 1

    def remove_server(self, iD):
        self.server_list = self.server_list.drop(iD, axis=0)
        print(f'Server {iD} has been removed from the group!')

    def remove_client(self, iD):
        self.client_list = self.client_list.drop(iD, axis=0)
        self.server_list.loc[self.id, 'number_client'] -= 1
        print(f'Client {iD} has been removed from the group!')

    def print_server(self):
        with pd.option_context('display.max_rows', None, 'display.max_columns',
                               None):
            print(self.server_list)
        print('')

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

    def get_server_address(self, TYPE: str = 'UDP', without: list = None) -> list:
        """
        HELPER FUNCTION
        Get all the addresses of servers that store in the gms
        :param without: indicate that the server list won't contain the list of servers
        :param TYPE: specify the port you want to get
        :return: a list of tuple address
        """
        if without is None:
            without = []
        tmp = []
        for iD, row in self.server_list.iterrows():
            if iD in without:
                continue
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

    def is_listed(self, iD, TYPE: str = 'SERVER') -> bool:
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
        elif TYPE == 'UNKNOWN':
            return iD in self.server_list.index.tolist() + self.client_list.index.tolist()
        else:
            raise ValueError('TYPE can only be "SERVER" or "CLIENT"!')

    def assign_clients(self) -> tuple:
        """
        HELPER FUNCTION
        return the server address with the least number of clients
        :return:
        """
        num = self.server_list['number_client'].argmin()
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
        if self.in_election:
            return
        for member in self.get_server_address('GMS'):
            utils.udp_send_without_response(member, self.server_list)

    def set_main_server(self, MAIN_SERVER: tuple) -> None:
        """
        HELPER FUNCTION:
        set the main server
        :return:
        """
        self.MAIN_SERVER = MAIN_SERVER

    def update_state(self):
        if self.MAIN_SERVER is not None:
            message = utils.create_message(self.id, 'UPDATE', {'MAIN_SERVER': self.MAIN_SERVER})
            for member in self.get_client_address('GMS'):
                utils.udp_send_without_response(member, message)

    def empty(self) -> bool:
        """
        HELPER FUNCTION:
        return: True if the server hasn't connected to any other processes
        """
        return self.client_size() == 0 and self.server_size() == 1


class group_member_service_client(group_member_service):
    def __init__(self, origin, IP_ADDRESS: str, iD, UDP_PORT):
        super().__init__(origin, IP_ADDRESS, iD, UDP_PORT)
        self.TYPE = 'CLIENT'
        self.CONTACT_SERVER = None
        self.start_thread()

    def heartbeat_send(self):
        while not self.TERMINATE:
            message = utils.create_message(self.id, 'HEAREQUEST', {'ID': self.id})

            if self.CONTACT_SERVER is not None:
                try:
                    response = utils.udp_send(utils.get_port(self.CONTACT_SERVER, 'GMS'), message)

                    if response is None:
                        # our heartbeat request timed out, so we need to reset the contact server
                        # the client class will detect this change and automatically try to reconnect
                        self.CONTACT_SERVER = None
                        if self.CONTACT_SERVER == self.MAIN_SERVER:
                            self.MAIN_SERVER = None
                    elif response['METHOD'] == 'HEAREPLY':
                        # we got exactly the response we expected, so we don't need to do anything
                        pass
                    else:
                        # print('Warning: Inappropriate message at heartbeat port.')
                        utils.colorful_print('Warning: Inappropriate message at heartbeat port.', 'FAIL')
                except ConnectionResetError:
                    # our heartbeat request timed out, so we need to reset the contact server
                    # the client class will detect this change and automatically try to reconnect
                    self.CONTACT_SERVER = None
                    self.handle_disconnect()
            else:
                self.handle_disconnect()

            time.sleep(self.HEARTBEAT_RATE)

    def heartbeat_listen(self):
        """
        create a socket to listen on the heartbeat port of the process
        :return: None
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.IP_ADDRESS, self.GMS_PORT))
        while not self.TERMINATE:
            # if we're disconnected we want the servers to realize that 
            if self.is_member:
                data, address = server_socket.recvfrom(self.BUFFER_SIZE)
                if data:
                    message = pickle.loads(data)
                    # don't listen to yourself!
                    self.heartbeat_listen_logic(message=message, address=address)

    def heartbeat_listen_logic(self, message: dict, address):
        if isinstance(message, pandas.DataFrame):
            # if the datatype is pandas df, it will be a synchronized of serverlist
            self.server_list = message
        else:
            method = message['METHOD']
            if method == 'HEAREQUEST':
                # we only respond to our contact server
                if message['CONTENT']['ADDRESS'] == self.CONTACT_SERVER:
                    reply = utils.create_message(self.id, 'HEAREPLY', {'ID': self.id})
                    utils.udp_send_without_response(address, reply)
            elif method == 'UPDATE':
                # now id the only for clients feature, to update the MAIN_SERVER
                self.MAIN_SERVER = message['CONTENT']['MAIN_SERVER']
            else:
                # print('Warning: Inappropriate message at heartbeat port.')
                utils.colorful_print('Warning: Inappropriate message at heartbeat port.', 'FAIL')


    def handle_disconnect(self) -> None:
        self.is_member = False
        self.ORIGIN.logging.warning('Client lose MAIN/CONTACT server!')
        self.ORIGIN.find_others()


def test():
    iD = str(uuid4())
    gms = group_member_service_server(None, '192.168.0.200', iD, 123, True, ('192.168.0.200', 1234))
    iD_spe = str(uuid4())
    gms.add_server(iD_spe, ('192.168.0.200', 123), time_stamp='asdf')
    gms.add_server(str(uuid4()), ('123.123.123.111', 1111), number_client=3)
    gms.add_server(str(uuid4()), ('123.123.123.222', 2222), time_stamp='a123')
    gms.add_server(str(uuid4()), ('123.123.123.123', 3333))
    gms.add_server(str(uuid4()), ('123.123.123.112', 4444))
    print(gms.id_to_address(iD_spe))
    # gms.print_server()
    # ring_with_id, ring = gms.form_ring()
    # print(ring_with_id)
    # neighbour = gms.get_neighbour(ring=ring, direction=False)
    # print(neighbour)
    # gms.LCR()


if __name__ == '__main__':
    test()
