import time
from auction_component import auction_component


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_member: bool = False):
        super().__init__()
        self.HEARTBEAT_RATE = 5
        self.TYPE = 'SERVER'
        self.UDP_PORT = UDP_PORT
        self.server_list = []
        self.is_member = is_member
        if is_member:
            self.MAIN_SERVER = (self.MY_IP, self.UDP_PORT)
        else:
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
        if method == 'DISCOVERY':
            if not self.is_member:
                message = self.create_message('DISCOVERY', {'type': self.TYPE})
                self.udp_send(request['SENDER_ADDRESS'], message)
            else:
                # TODO: send the contact information
                pass
        elif method == 'HEARTBEAT':
            pass
            # TODO: implementation heartbeat
        elif method == 'RAISE':
            pass
            # TODO: implementation raise bid
        else:
            print(request)

    def heartbeat_sender(self):
        while True:
            print('Heart beating...')
            # TODO: implement heartbeat
            time.sleep(self.HEARTBEAT_RATE)

    def udp_listen_(self):
        super().udp_listen(self.UDP_PORT)


if __name__ == '__main__':
    test_component = Server(10001)
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
        else:
            print('Invalid input!')
