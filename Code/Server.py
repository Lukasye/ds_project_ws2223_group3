import click
import time
# from multiprocessing import Process
from auction_component import auction_component


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_main: bool = False):
        super(Server, self).__init__('SERVER', UDP_PORT)
        self.HEARTBEAT_RATE = 5
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
                  'Broadcast: \t{}:{}\n' \
                  'Main Server: \t{}'.format(self.TYPE, self.MY_IP,
                                             self.UDP_PORT, self.BROADCAST_IP,
                                             self.BROADCAST_PORT, self.MAIN_SERVER)
        print(message)

    def find_others(self) -> None:
        # TODO: should be convert into multi process function
        message = self.create_message('DISCOVERY', {'ADDRESS': (self.MY_IP, self.UDP_PORT)})
        self.broadcast_send(message)

    def logic(self, request: dict):
        method = request['METHOD']
        self.print_message(request)
        if method == 'DISCOVERY':
            if not self.is_member:
                self.join(tuple(request['CONTENT']['ADDRESS']))
            else:
                # TODO: send the contact information
                pass
        elif method == 'JOIN':
            # join request can only be handled by the main server
            if self.is_main:
                # append the article to the server or client list
                if request['CONTENT']['TYPE'] == 'SERVER':
                    self.server_list.append({request['ID']: request['CONTENT']['UDP_ADDRESS']})
                else:
                    self.client_list.append({request['ID']: request['CONTENT']['UDP_ADDRESS']})
                # inform the remote member the right sates: is_member = True & MAIN_SERVER
                message = self.create_message('SET', {'MAIN_SERVER': (self.MY_IP, self.UDP_PORT),
                                                      'is_member': True})
                self.udp_send_without_response(request['SENDER_ADDRESS'], message)
            else:
                pass
                # TODO: redirect to main server
        # remotely change the parameter
        elif method == 'SET':
            tmp = request['CONTENT']
            for key in tmp:
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


# class event_handler(Process, Server):
#     def __init__(self, request: dict):
#         super().__init__()
#         self.request = request
#
#     def run(self) -> None:
#         self.logic(self.request)


@click.command()
@click.option('--port', required=True, default=10001, type=int, help='The port that the server connect to')
@click.option('--opt', required=True, default=1, type=int, help='whether the server is entry point of the system')
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
            test_component.udp_listen()
        elif user_input == 'server':
            print(test_component.server_list)
        elif user_input == 'client':
            print(test_component.client_list)
        elif user_input == 'listen':
            test_component.broadcast_listen()
        elif user_input == 'udp_listen':
            test_component.udp_listen()
        elif user_input == 'join':
            test_component.join(('172.17.16.1', 10001))
        else:
            print('Invalid input!')


if __name__ == '__main__':
    main()
