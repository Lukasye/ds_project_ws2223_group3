import socket
import pickle
import os
import heapq
from tqdm import tqdm
import time
from uuid import uuid4
import threading
from abc import abstractmethod
# from rich.console import Console
# from rich import print

import utils
import config as cfg


class element:
    """
    A class to pack the message for the hold_back queue
    """
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
        # init()
        self.BROADCAST_PORT = cfg.attr['BROADCAST_PORT']
        self.MY_HOST = socket.gethostname()
        self.MY_IP = utils.get_ip_address()
        self.BROADCAST_IP = utils.get_broadcast_address()
        self.BUFFER_SIZE = cfg.attr['BUFFER_SIZE']
        self.ENCODING = 'utf-8'
        self.UDP_PORT = UDP_PORT
        self.HEARTBEAT_RATE = cfg.attr['HEARTBEAT_RATE']
        self.TIM_PORT = UDP_PORT + 1
        self.ELE_PORT = UDP_PORT + 2
        self.GMS_PORT = UDP_PORT + 3
        self.TYPE = TYPE
        self.SYS = os.name
        self.MAIN_SERVER = None
        self.TERMINATE = False
        if TYPE == 'CLIENT':
            self.CONTACT_SERVER = None
        self.hold_back_queue = []
        self.id = str(uuid4())
        self.threads = []
        self.multicast_hist = []
        self.sequence_counter = 1  # the initial sequence number for all the participants
        self.highest_bid = 0  # The highest bid that everyone agreed on
        self.winner = None  # winner of this round
        self.intercept = 0
        self.update = False
        # self.console = Console()
        self.TERMINATE = False
        self.headless = False
        self.in_auction = False

    @abstractmethod
    def logic(self, request: dict) -> None:
        """
        handle the request that has been DELIVERED to the object
        :param request: dictionary includes the request
        :return: whether the function get a positive result
        """
        pass

    @abstractmethod
    def report(self):
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
    def udp_send_without_response(address: tuple, message: dict):
        utils.udp_send_without_response(address, message)

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
        print('Message sent from {}\n'
              'ID: {} METHOD:{} SEQ:{} CONTENT:{}'.format(message['SENDER_ADDRESS'], message['ID'],
                                                          message['METHOD'], message['SEQUENCE'],
                                                          message['CONTENT']))

    def warm_up(self, ts: list, headless: bool = False) -> None:
        """
        HELPER FUNCTION:
        for initializing all the process and save them into a thread manager
        :param headless: whether the interface should be initialized
        :param ts: all the function you need to run
        :return: None
        """
        for th in ts:
            t = threading.Thread(target=th, daemon=True)
            t.start()
            # t.join()
            self.threads.append(t)
        if not headless:
            t = threading.Thread(target=self.interface)
            t.start()

    def create_message(self, METHOD: str, CONTENT: dict, SEQUENCE: int = 0):
        return utils.create_message(iD=self.id,
                                    METHOD=METHOD,
                                    CONTENT=CONTENT,
                                    SEQUENCE=SEQUENCE)

    def udp_send(self, address: tuple, message: dict, receive: bool = False) -> dict:
        """
        normal udp send function
        :param address: the address of the recipient
        :param message: standard message format in dict
        :param receive: boolean variable to set whether the message should be passed to the self.receive() function
        :return: standard message format in dict
        """
        data = utils.udp_send(address, message)
        if receive:
            self.receive(data)
        return data

    def receive(self, message: dict) -> None:
        """
        categorize all the information and distribute them to the right request dealers
        :param message: standard dict format request
        :return: None
        """
        # if message['ID'] == self.id and message['SEQUENCE'] == 0:
        #     # I don't want to listen to myself (normal messages)
        #     pass
        if message['SEQUENCE'] != 0:
            if self.intercept:
                # just for testing! skip the next message!
                self.intercept -= 1
                return
            seq = message['SEQUENCE']
            # Reliable ordered needed!
            if seq < self.sequence_counter:
                # this message has already delivered!
                pass
            else:
                # push the message into the hold_back_queue
                heapq.heappush(self.hold_back_queue, element(message))
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
                    # simultaneously record the message
                    self.multicast_hist.append(ele.get_info())
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
        """
        Once a function is in the delivery queue, create a new thread to deal with it.
        ATTENTION: the delivery queue is only for the message from the udp_port!!
        :param message: dict format standard message
        :return:
        """
        t = threading.Thread(target=self.logic, args=(message,))
        t.start()

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
        while not self.TERMINATE:
            data, address = listen_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                message = pickle.loads(data)
                message['SENDER_ADDRESS'] = address
                self.receive(message)

    def udp_listen(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.MY_IP, self.UDP_PORT))
        while not self.TERMINATE:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                message = pickle.loads(data)
                message['SENDER_ADDRESS'] = address
                self.receive(message)

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
        :param inform_all: boolean variable whether broadcast is used
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
            message = self.create_message('RMI', SEQUENCE=SEQUENCE, CONTENT={'METHODE': methode})
            self.udp_send_without_response(tuple(address), message)

    def remote_para_set(self, group: list, SEQUENCE: int = 0, **kwargs):
        for address in group:
            message = self.create_message('SET', SEQUENCE=SEQUENCE, CONTENT=kwargs)
            self.udp_send_without_response(tuple(address), message)

    def multicast_send_without_response(self, group: list,
                                        message: dict,
                                        record: bool = True,
                                        test: int = -1,
                                        skip: int = -1):
        """
        HELPER FUNCTION
        send out multicast to a group
        :param record: whether the message should be added into the multicast_hist
        :param group: list of tuple address of a group
        :param message: standard dict message format
        :param test: the chosen index of process will be blocked for 10 seconds (only for testing)
        :param skip: the chosen index of process will be skipped (only for testing)
        :return:
        """
        assert test < len(group)
        assert skip < len(group)
        # if message['SEQUENCE'] > 0 and record:
        #     # if it is a sequence relevant message, append it to the history
        #     self.multicast_hist.append(message)
        #     self.sequence_counter += 1
        count = 0
        for member in tqdm(group):
            if count == test:
                time.sleep(10)
            if count == skip:
                continue
            self.udp_send_without_response(tuple(member), message)
            count += 1

    def negative_acknowledgement(self):
        # if the sequence number is already actuel ???
        message = self.create_message('GET', {'SEQ': self.sequence_counter})
        if self.TYPE == 'CLIENT' and self.CONTACT_SERVER is not None:
            self.udp_send(self.CONTACT_SERVER, message, receive=True)
        elif self.MAIN_SERVER is not None:
            self.udp_send(self.MAIN_SERVER, message, receive=True)


if __name__ == '__main__':
    auction_component('SERVER', 12345)
