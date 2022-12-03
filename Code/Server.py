import click
import time
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
        self.report()
        # open multiple thread to do different jobs
        self.warm_up([self.udp_listen, self.broadcast_listen])

    def report(self):
        message = '{} activate on\n' \
                  'Address: \t{}:{} \n' \
                  'Broadcast: \t{}:{}\n' \
                  'Main Server: \t{}'.format(self.TYPE, self.MY_IP,
                                             self.UDP_PORT, self.BROADCAST_IP,
                                             self.BROADCAST_PORT, self.MAIN_SERVER)
        print(message)

    def logic(self, request: dict):
        method = request['METHOD']
        self.print_message(request)
        # ********************** METHOD DISCOVERY **********************************
        if method == 'DISCOVERY':
            # if the server is still not a member or a main server
            if not self.is_member:
                self.join(tuple(request['CONTENT']['ADDRESS']))
            else:
                if self.is_main:
                    self.accept(request)
                elif self.MAIN_SERVER is not None:
                    self.forward(self.MAIN_SERVER, request)
        # ********************** METHOD JOIN **********************************
        elif method == 'JOIN':
            # join request can only be handled by the main server
            if self.is_main:
                self.accept(request)
            elif self.MAIN_SERVER is not None:
                self.forward(self.MAIN_SERVER, request)
        # **********************    METHOD SET     **********************************
        elif method == 'SET':
            tmp = request['CONTENT']
            for key in tmp:
                exec('self.{} = {}'.format(key, tmp[key]))
            self.state_update()
        # **********************  METHOD REDIRECT **********************************
        elif method == 'REDIRECT':
            self.receive(request)
        # **********************  METHOD HEARTBEAT **********************************
        elif method == 'HEARTBEAT':
            pass
            # TODO: implementation heartbeat
        else:
            print(request)

    def accept(self, request: dict) -> None:
        # append the article to the server or client list
        if request['CONTENT']['TYPE'] == 'SERVER':
            self.server_list.append({request['ID']: request['CONTENT']['UDP_ADDRESS']})
        else:
            self.client_list.append({request['ID']: request['CONTENT']['UDP_ADDRESS']})
        # inform the remote member the right sates: is_member = True & MAIN_SERVER
        message = self.create_message('SET', {'MAIN_SERVER': (self.MY_IP, self.UDP_PORT),
                                              'is_member': True})
        self.udp_send_without_response(tuple(request['CONTENT']['UDP_ADDRESS']), message)

    def heartbeat_sender(self):
        while True:
            if self.TERMINATE:
                break
            print('Heart beating...')
            # TODO: implement heartbeat
            time.sleep(self.HEARTBEAT_RATE)

    def interface(self) -> None:
        while True:
            print('*' * 50)
            user_input = input('Please enter your command:')
            if user_input == 'exit':
                self.TERMINATE = True
                quit()
            elif user_input == 'report':
                self.report()
            elif user_input == 'find':
                self.find_others()
            elif user_input == 'server':
                print(self.server_list)
            elif user_input == 'client':
                print(self.client_list)
            elif user_input == 'listen':
                self.broadcast_listen()
            elif user_input == 'join':
                self.join(('172.17.16.1', 10001))
            else:
                print('Invalid input!')

    def state_update(self) -> None:
        pass

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
    Server(port, opt == 1)


if __name__ == '__main__':
    main()
