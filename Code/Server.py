import click
import json
import socket
import time
from auction_component import auction_component


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_main: bool = False):
        super().__init__()
        self.HEARTBEAT_RATE = 5
        self.TYPE = 'SERVER'
        self.UDP_PORT = UDP_PORT
        self.server_list = []
        self.client_list = []
        self.is_main = is_main
        # initialize depends on whether this is the main server
        if is_main:
            self.is_member = True
            self.MAIN_SERVER = (self.MY_IP, self.UDP_PORT)
        else:
            self.is_member = False
            self.MAIN_SERVER = None

    def report(self):
        message = '{} activate on\n' \
                  'Address: \t{}:{} \n' \
                  'Main Server: \t{}'.format(self.TYPE, self.MY_IP, self.UDP_PORT, self.MAIN_SERVER)
        print(message)

    def find_others(self) -> None:
        # TODO: should be convert into multi process function
        message = self.create_message('DISCOVERY', {'ADDRESS': (self.MY_IP, self.UDP_PORT)})
        self.broadcast_send(message)

    def logic(self, request: dict):
        method = request['METHOD']
        print(request)
        if method == 'DISCOVERY':
            if not self.is_member:
                message = self.create_message('DISCOVERY', {'type': self.TYPE})
                self.udp_send(request['SENDER_ADDRESS'], message)
            else:
                # TODO: send the contact information
                pass
        elif method == 'JOIN':
            # join request can only be handled by the main server
            if self.is_main:
                message = self.create_message('SET', {'MAIN_SERVER': (self.MY_IP, self.UDP_PORT)})
                print(message)
                self.udp_send_without_response(request['SENDER_ADDRESS'], message)
            else:
                pass
                # TODO: redirect to main server
        # remotely change the parameter
        elif method == 'SET':
            tmp = request['CONTENT']
            for key in tmp:
                print('self.{} = {}'.format(key, tmp[key]))
                exec('self.{} = {}'.format(key, tmp[key]))
        elif method == 'HEARTBEAT':
            pass
            # TODO: implementation heartbeat
        else:
            print(request)

    def heartbeat_sender(self):
        while True:
            print('Heart beating...')
            # TODO: implement heartbeat
            time.sleep(self.HEARTBEAT_RATE)

    def udp_listen_(self):
        super().udp_listen(self.UDP_PORT)


@click.command()
@click.option('--port', required=True, default=10001, type=int, help='The port that the server connect to')
@click.option('--opt', required=True, default=0, type=int, help='whether the server is entry point of the system')
def main(port, opt):
    test_component = Server(port, opt == 1)
    test_component.report()
    while True:
        print('*' * 50)
        user_input = input('Please enter your command:')
        if user_input == 'exit':
            quit()
        elif user_input == 'report':
            test_component.report()
        elif user_input == 'find':
            test_component.find_others()
        elif user_input == 'server':
            print(test_component.server_list)
        elif user_input == 'client':
            print(test_component.client_list)
        elif user_input == 'udp_listen':
            print('UDP listening on port {}'.format(test_component.UDP_PORT))
            test_component.udp_listen_()
        elif user_input == 'join':
            test_component.join(('172.17.16.1', 10001))
        else:
            print('Invalid input!')


if __name__ == '__main__':
    main()
