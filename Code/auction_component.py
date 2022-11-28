import json
import socket
from message import *
from secrets import token_urlsafe
# from multiprocessing import Process
import threading
from abc import abstractmethod


class auction_component:
    def __init__(self, TYPE, UDP_PORT):
        # User interface and logic
        self.BROADCAST_IP = "172.17.31.255"
        self.BROADCAST_PORT = 5972
        self.MY_HOST = socket.gethostname()
        self.MY_IP = socket.gethostbyname(self.MY_HOST)
        self.BUFFER_SIZE = 4096
        self.ENCODING = 'utf-8'
        self.TOKEN_LENGTH = 16
        self.UDP_PORT = UDP_PORT
        self.TYPE = TYPE
        self.hold_back_queue = hold_back_queue()
        self.delivery_queue = delivery_queue()
        self.id = token_urlsafe(self.TOKEN_LENGTH)

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

    @staticmethod
    def udp_send_without_response(address, message: dict):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(str.encode(json.dumps(message)), address)

    @staticmethod
    def print_message(message: dict) -> None:
        if message['SENDER_ADDRESS'] is not None:
            print('Message sent from {}'. format(message['SENDER_ADDRESS']))
        print('ID: {} METHOD:{} SEQ:{} CONTENT:{}'.format(message['ID'], message['METHOD'],
                                                          message['SEQUENCE'], message['CONTENT']))

    def create_message(self, METHOD: str, CONTENT, SEQUENCE: int = 0):
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

    def udp_send(self, address, message: dict) -> None:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(str.encode(json.dumps(message)), address)
        data, addr = udp_socket.recvfrom(self.BUFFER_SIZE)
        if data:
            message = json.loads(data.decode())
            message['SENDER_ADDRESS'] = address
            self.receive(message)

    def receive(self, message: dict):
        # TODO: function requirement
        if message['SEQUENCE'] != 0:
            self.hold_back_queue.push(message)
        else:
            self.deliver(message)

    def deliver(self, message: dict) -> None:
        # p = Process(target=self.logic, args=message)
        # p.start()
        # p.join()
        self.logic(message)

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
        broadcast_socket.sendto(str.encode(json.dumps(message), encoding=self.ENCODING),
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
        print("Listening to broadcast messages")
        while True:
            data, address = listen_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                message = json.loads(data.decode())
                message['SENDER_ADDRESS'] = address
                self.receive(message)
                break

    def udp_listen(self):
        print('UDP listening on port {}'.format(self.UDP_PORT))
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.MY_IP, self.UDP_PORT))
        while True:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                message = json.loads(data.decode())
                message['SENDER_ADDRESS'] = address
                # self.receive(message)
                t = threading.Thread(target=self.receive, args=(message,))
                t.start()
                # p.join()

    def join(self, address) -> None:
        """
        HELPER FUNCTION:
        ask to join a server group
        :param address: the address of the main server
        :return: None
        """
        message = self.create_message('JOIN', {'TYPE': self.TYPE, 'UDP_ADDRESS': (self.MY_IP, self.UDP_PORT)})
        self.udp_send(address, message)


if __name__ == '__main__':
    test_component = auction_component('SERVER', 12345)
