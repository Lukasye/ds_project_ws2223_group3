import click
import time
from auction_component import auction_component


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_main: bool = False):
        super(Server, self).__init__('SERVER', UDP_PORT)
        self.HEARTBEAT_RATE = 5
        self.bid_history = []
        self.num_servers = 0
        self.num_clients = 0
        self.server_list = [{'ID': self.id, 'ADDRESS': (self.MY_IP, self.UDP_PORT), 'NUMBER': 0}]
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
                  'ID: \t\t{}\n' \
                  'Address: \t{}:{} \n' \
                  'Broadcast: \t{}:{}\n' \
                  'Main Server: \t{}'.format(self.TYPE, self.id, self.MY_IP,
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
                self.join(tuple(request['CONTENT']['UDP_ADDRESS']))
            else:
                if self.is_main:
                    self.accept(request)
                elif self.MAIN_SERVER is not None:
                    self.forward(self.MAIN_SERVER, request)
        # ********************** METHOD JOIN **********************************
        elif method == 'JOIN':
            # join request can only be handled by the main server
            # if self.is_main:
            self.accept(request)
            # elif self.MAIN_SERVER is not None:
            #     self.forward(self.MAIN_SERVER, request)
        # **********************    METHOD SET     **********************************
        elif method == 'SET':
            tmp = request['CONTENT']
            for key in tmp:
                exec('self.{} = {}'.format(key, tmp[key]))
            self.state_update()
        # **********************  METHOD REDIRECT **********************************
        elif method == 'REDIRECT':
            if self.is_main:
                self.receive(request['CONTENT']['MESSAGE'])
        # **********************  METHOD HEARTBEAT **********************************
        elif method == 'HEARTBEAT':
            # TODO: implementation heartbeat
            if self.is_main:
                pass
            else:
                pass
        # **********************  METHOD HEARTBEAT **********************************
        elif method == 'RMI':
            exec('self.{}()'.format(request['CONTENT']['METHODE']))
        else:
            print(request)

    def accept(self, request: dict) -> None:
        """
        HELPER FUNCTION:
        Add the sender to the list(server or client) and reset the state of the sender
        :param request:
        :return:
        """
        # append the article to the server or client list
        content = {'MAIN_SERVER': (self.MY_IP, self.UDP_PORT), 'is_member': True}
        if request['CONTENT']['TYPE'] == 'SERVER':
            self.server_list.append({'ID': request['ID'], 'ADDRESS': tuple(request['CONTENT']['UDP_ADDRESS']),
                                     'NUMBER': 0})
            content['server_list'] = self.server_list
            self.num_servers += 1
        else:
            self.client_list.append({request['ID']: tuple(request['CONTENT']['UDP_ADDRESS'])})
            # TODO: remote method invocation: let client join server
            self.num_clients += 1
        # inform the remote member the right sates: is_member = True & MAIN_SERVER
        message = self.create_message('SET', content)
        self.udp_send_without_response(tuple(request['CONTENT']['UDP_ADDRESS']), message)

    def heartbeat_sender(self):
        while True:
            if self.TERMINATE:
                break
            print('Heart beating...')
            # TODO: implement heartbeat
            time.sleep(self.HEARTBEAT_RATE)

    def assign_clients(self) -> tuple:
        """
        HELPER FUNCTION:
        assign the new client to the server which has the least number of clients
        :return: tuple, address of the contact server
        """
        candidate = self.server_list[0]
        for server in self.server_list:
            if server['NUMBER'] < candidate['NUMBER']:
                candidate = server
        return candidate['ADDRESS']

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
            elif user_input == 'join':
                self.join(None, True)
            elif user_input.startswith('rmi'):
                info = user_input.split(' ')
                self.remote_methode_invocation(('172.17.112.1', int(info[1])), info[2])
            else:
                print('Invalid input!')

    def state_update(self) -> None:
        pass


@click.command()
@click.option('--port', required=True, default=10001, type=int, help='The port that the server connect to')
@click.option('--opt', required=True, default=1, type=int, help='whether the server is entry point of the system')
def main(port, opt):
    Server(port, opt == 1)


if __name__ == '__main__':
    main()
