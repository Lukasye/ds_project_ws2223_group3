import socket
import pickle
import os
import heapq
from tqdm import tqdm
import time
from uuid import uuid4
import threading
from abc import abstractmethod
from colorama import init, Fore, Style


class element:
    def __init__(self, info: dict):
        self.info = info
        self.SEQ = info['SEQUENCE']

    def get_seq(self):
        return self.SEQ

    def get_info(self):
        return self.info

    def __eq__(self, other):
        return self.SEQ == other.SEQ

    def __lt__(self, other):
        return self.SEQ < other.SEQ

    def __str__(self):
        return str(self.info)


class auction_component:
    def __init__(self, TYPE, UDP_PORT):
        # User interface and logic
        init()
        self.BROADCAST_PORT = 5972
        self.MY_HOST = socket.gethostname()
        self.MY_IP = self.get_ip_address()
        self.BROADCAST_IP = self.get_broadcast_address(self.MY_IP, "255.255.224.0")  # "172.17.127.255"
        self.BUFFER_SIZE = 4096
        self.ENCODING = 'utf-8'
        # self.TOKEN_LENGTH = 16
        self.UDP_PORT = UDP_PORT
        self.BRO_PORT = UDP_PORT + 1
        self.ELE_PORT = UDP_PORT + 2
        self.HEA_PORT = UDP_PORT + 3
        self.TYPE = TYPE
        self.MAIN_SERVER = None
        if TYPE == 'CLIENT':
            self.CONTACT_SERVER = None
        self.hold_back_queue = []
        # self.delivery_queue = delivery_queue()
        # self.id = token_urlsafe(self.TOKEN_LENGTH)
        self.id = str(uuid4())
        self.threads = []
        self.multicast_hist = []
        self.sequence_counter = 1  # the initial sequence number for all the participants
        self.highest_bid = 0  # The highest bid that everyone agreed on
        self.winner = None  # winner of this round
        self.intercept = False
        self.update = False
        self.HEARTBEAT_RATE = 5
        self.TERMINATE = False

    @abstractmethod
    def logic(self, request: dict) -> None:
        """
        handle the request that has been DELIVERED to the object
        :param request: dictionary includes the request
        :return: whether the function get a positive result
        """
        pass

    @abstractmethod
    def report(self) -> None:
        """
        print the informant information of the class
        :return: None
        """
        pass

    @abstractmethod
    def interface(self) -> None:
        """
        provide an interface to interact with the user
        :return: None
        """
        pass

    @abstractmethod
    def state_update(self) -> None:
        """
        HELPER FUNCTION:
        part of SET request to regularly update states
        :return: None
        """
        pass

    @staticmethod
    def get_ip_address():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    @staticmethod
    def udp_send_without_response(address: tuple, message: dict):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # udp_socket.sendto(str.encode(json.dumps(message)), tuple(address))
        udp_socket.sendto(pickle.dumps(message), address)

    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def print_message(message: dict) -> None:
        """
        HELPER FUNCTION:
        print the massage on the interface screen
        :param message: dict, standard message format
        :return:
        """
        print()
        if message['SENDER_ADDRESS'] is not None:
            print(Fore.LIGHTGREEN_EX + 'Message sent from {}'.format(message['SENDER_ADDRESS']))
        print('ID: {} METHOD:{} SEQ:{} CONTENT:{}'.format(message['ID'], message['METHOD'],
                                                          message['SEQUENCE'], message['CONTENT']) + Style.RESET_ALL)

    @staticmethod
    def get_broadcast_address(ip, netmask):
        """
        calculate broadcast address
        :param ip:
        :param netmask:
        :return:
        """
        ip = ip.split('.')
        netmask = netmask.split('.')
        broadcast = []
        for i in range(3):
            broadcast.append(str(int(ip[i]) | (255 - int(netmask[i]))))
        broadcast.append("255")
        return '.'.join(broadcast)

    @staticmethod
    def get_port(MAIN_SERVER: tuple, PORT: str = 'SEQ') -> tuple:
        addr = MAIN_SERVER[0]
        port = MAIN_SERVER[1]
        if PORT == 'BRO':
            port += 1
        elif PORT == 'ELE':
            port += 2
        elif PORT == 'HEA':
            port += 3
        elif PORT == 'SEQ':
            port += 4
        else:
            raise ValueError('Input argument PORT not found!')
        return tuple([addr, port])

    @staticmethod
    def extract_address(client_list: list) -> list:
        tmp = []
        for ele in client_list:
            tmp.append(ele['ADDRESS'])
        return tmp

    def warm_up(self, ts: list) -> None:
        """
        HELPER FUNCTION:
        for initializing all the process and save them into a thread manager
        :param ts: all the function you need to run
        :return: None
        """
        for th in ts:
            t = threading.Thread(target=th, daemon=True)
            t.start()
            # t.join()
            self.threads.append(t)
        t = threading.Thread(target=self.interface)
        t.start()

    def create_message(self, METHOD: str, CONTENT: dict, SEQUENCE: int = 0):
        """
        HELPER FUNCTION:
        pack the info to generate as dict file for the transmitting
        :param SEQUENCE: the sequence number of the message
        :param METHOD: type of request
        :param CONTENT: body
        :return: dict object
        """
        return {'ID': self.id,
                'METHOD': METHOD,
                'SEQUENCE': SEQUENCE,
                'CONTENT': CONTENT}

    def udp_send(self, address: tuple, message: dict, receive: bool = False) -> dict:
        """
        normal udp send function
        :param address: the address of the recipient
        :param message: standard message format in dict
        :param receive: boolean variable to set whether the message should be passed to the self.receive() function
        :return: standard message format in dict
        """
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # udp_socket.sendto(str.encode(json.dumps(message)), address)
        message_byte = pickle.dumps(message)
        if len(message_byte) > self.BUFFER_SIZE:
            raise ValueError('Message too large')
        udp_socket.sendto(message_byte, address)
        data, addr = udp_socket.recvfrom(self.BUFFER_SIZE)
        if data:
            # message = json.loads(data.decode())
            data = pickle.loads(data)
            data['SENDER_ADDRESS'] = addr
            if receive:
                self.receive(data)
            return data

    def receive(self, message: dict):
        # TODO: function requirement
        if message['ID'] == self.id and message['SEQUENCE'] == 0:
            # I don't want to listen to myself (normal messages)
            pass
        elif message['SEQUENCE'] != 0:
            if self.intercept:
                # just for testing! skip the next message!
                self.intercept = True
                return
            seq = message['SEQUENCE']
            # Reliable ordered needed!
            if seq < self.sequence_counter:
                # this message has already delivered!
                pass
            else:
                # push the message into the hold_back_queue
                heapq.heappush(self.hold_back_queue, element(message))
            # if seq == self.sequence_counter:
            #     self.deliver(message)
            #     time.sleep(0.01)
            #     self.sequence_counter += 1
            #     # check whether the next (few) messages can be delivered
            #     if bool(self.hold_back_queue):
            #         if self.sequence_counter == self.hold_back_queue[0].get_seq():
            #             self.receive(heapq.heappop(self.hold_back_queue).get_info())
            # elif seq > self.sequence_counter:
            #     heapq.heappush(self.hold_back_queue, element(message))
            #     self.negative_acknowledgement()
            # else:
            #     # This message has already delivered!
            #     pass
        else:
            # deliver direct all the normal messages
            self.deliver(message)

    def check_hold_back_queue(self):
        timestamp = time.time()
        while not self.TERMINATE:
            if bool(self.hold_back_queue):
                # if the hold_back queue isn't empty
                if self.sequence_counter == self.hold_back_queue[0].get_seq():
                    # if the next message can be delivered
                    ele = heapq.heappop(self.hold_back_queue)
                    self.deliver(ele.get_info())
                    self.sequence_counter += 1
                    time.sleep(0.01)
                else:
                    # if not, send out the negative acknowledgement
                    cmp = time.time()
                    if cmp - timestamp > self.HEARTBEAT_RATE:
                        self.negative_acknowledgement()
                        timestamp = time.time()

    def deliver(self, message: dict) -> None:
        # p = Process(target=self.logic, args=message)
        # p.start()
        # p.join()
        t = threading.Thread(target=self.logic, args=(message,))
        t.start()
        # self.logic(message)

    def broadcast_send(self, message: dict) -> None:
        """
        broadcast the message with the predefined broadcast port.
        Better use with multi_process
        :param message: dictionary of request
        :return: None
        """
        print('Broadcast sent out on address: {}:{}'.format(self.BROADCAST_IP,
                                                            self.BROADCAST_PORT))
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # broadcast_socket.sendto(str.encode(json.dumps(message), encoding=self.ENCODING),
        #                         (self.BROADCAST_IP, self.BROADCAST_PORT))
        message_byte = pickle.dumps(message)
        if len(message_byte) > self.BUFFER_SIZE:
            raise ValueError('Message too large')
        broadcast_socket.sendto(message_byte,
                                (self.BROADCAST_IP, self.BROADCAST_PORT))

    def broadcast_listen(self) -> None:
        """
        use the predefined broadcast port to listen the reply and handle it to the receipt section
        :return: None
        """
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind((self.MY_IP, self.BROADCAST_PORT))
        # print("Listening to broadcast messages")
        while not self.TERMINATE:
            data, address = listen_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                # message = json.loads(data.decode())
                message = pickle.loads(data)
                message['SENDER_ADDRESS'] = address
                self.receive(message)

    def udp_listen(self):
        # print('UDP listening on port {}'.format(self.UDP_PORT))
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.MY_IP, self.UDP_PORT))
        while not self.TERMINATE:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                # message = json.loads(data.decode())
                message = pickle.loads(data)
                message['SENDER_ADDRESS'] = address
                self.receive(message)
                # t = threading.Thread(target=self.receive, args=(message,))
                # t.start()
                # p.join()

    def print_hold_back_queue(self):
        for ele in self.hold_back_queue:
            print(ele.get_info())

    def find_others(self) -> None:
        """
        HELPER FUNCTION:
        send the broadcast message to the  other object
        :return: None
        """
        message = self.create_message('DISCOVERY', {'TYPE': self.TYPE, 'UDP_ADDRESS': (self.MY_IP, self.UDP_PORT)})
        self.broadcast_send(message)

    def join(self, address, inform_all: bool = False) -> None:
        """
        HELPER FUNCTION:
        ask to join a server group
        :param inform_all: boolean variable whether use broadcast
        :param address: the address of the main server
        :return: None
        """
        message = self.create_message('JOIN', {'TYPE': self.TYPE, 'UDP_ADDRESS': (self.MY_IP, self.UDP_PORT)})
        if inform_all:
            self.broadcast_send(message)
        else:
            self.udp_send_without_response(address, message)

    def forward(self, address, request) -> None:
        """
        redirect the message to new address. The information will contain
        the address and content of the original sender
        :param address: original sender
        :param request: the request that you've received
        :return:
        """
        message = self.create_message('REDIRECT', {'TARGET': request['SENDER_ADDRESS'],
                                                   'MESSAGE': request})
        self.udp_send_without_response(address, message)

    def remote_methode_invocation(self, group: list, methode: str, SEQUENCE: int = 0):
        for address in group:
            message = self.create_message('RMI',SEQUENCE=SEQUENCE, CONTENT={'METHODE': methode})
            self.udp_send_without_response(tuple(address), message)

    def remote_para_set(self, group: list, SEQUENCE: int = 0, **kwargs):
        for address in group:
            message = self.create_message('SET', SEQUENCE=SEQUENCE, CONTENT=kwargs)
            self.udp_send_without_response(tuple(address), message)

    def multicast_send_without_response(self, group: list, message: dict, test: int = -1):
        assert test < len(group)
        if message['SEQUENCE'] > 0:
            # if it is a sequence relevant message, append it to the history
            self.multicast_hist.append(message)
        count = 0
        for member in tqdm(group):
            if count == test:
                time.sleep(10)
            self.udp_send_without_response(tuple(member), message)
            count += 1

    def negative_acknowledgement(self):
        message = self.create_message('GET', {'info': self.sequence_counter})
        if self.TYPE == 'CLIENT':
            # self.udp_send(self.CONTACT_SERVER, message, True)
            self.udp_send_without_response(self.CONTACT_SERVER, message)
        else:
            self.udp_send(self.MAIN_SERVER, message, True)


if __name__ == '__main__':
    auction_component('SERVER', 12345)
