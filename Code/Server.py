import click
import time
import pandas as pd
from auction_component import auction_component
from colorama import Fore, Style


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_main: bool = False):
        super(Server, self).__init__('SERVER', UDP_PORT)
        self.bid_history = []
        self.num_servers = 0
        self.num_clients = 0
        self.server_list = pd.DataFrame([{'ID': self.id, 'ADDRESS': (self.MY_IP, self.UDP_PORT), 'NUMBER': 0}])
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
                  'ID: \t\t\t{}\n' \
                  'Address: \t\t{}:{} \n' \
                  'Broadcast: \t\t{}:{}\n' \
                  'Main Server: \t\t{}\n' \
                  'Number of Clients: \t{}'.format(self.TYPE, self.id, self.MY_IP, self.UDP_PORT,
                                                   self.BROADCAST_IP, self.BROADCAST_PORT,
                                                   self.MAIN_SERVER, self.num_clients)
        print(Fore.LIGHTYELLOW_EX + message + Style.RESET_ALL)

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
                    self.assign(request)
                elif self.MAIN_SERVER is not None:
                    self.forward(self.MAIN_SERVER, request)
        # ********************** METHOD JOIN **********************************
        elif method == 'JOIN':
            # if the server is not main, it can only accept
            if not self.is_main:
                self.accept(request)
            else:
                self.assign(request)
        # **********************    METHOD SET     **********************************
        elif method == 'SET':
            tmp = request['CONTENT']
            for key in tmp:
                exec('self.{} = {}'.format(key, tmp[key]))
            # self.state_update()
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

    def assign(self, request: dict) -> None:
        """
        HELPER FUNCTION:
        assign the join request to the right server to balance the performance
        :param request: dict, request receipted from the client or server
        :return:
        """
        # content = {'MAIN_SERVER': (self.MY_IP, self.UDP_PORT), 'is_member': True}
        if request['CONTENT']['TYPE'] == 'SERVER':
            # if self.already_in(request['ID'], self.server_list):
            if request['ID'] in list(self.server_list['ID']):
                return
            # self.server_list.append({'ID': request['ID'], 'ADDRESS': tuple(request['CONTENT']['UDP_ADDRESS']),
            #                          'NUMBER': 0})
            new_row = pd.Series({'ID': request['ID'], 'ADDRESS': tuple(request['CONTENT']['UDP_ADDRESS']),
                                 'NUMBER': 0})
            self.server_list = pd.concat([self.server_list, new_row.to_frame().T])
            self.num_servers += 1
            self.remote_para_set(tuple(request['CONTENT']['UDP_ADDRESS']),
                                 MAINSERVER=(self.MY_IP, self.UDP_PORT),
                                 is_member=True,
                                 server_list=self.server_list.to_dict())
            self.remote_methode_invocation(tuple(request['CONTENT']['UDP_ADDRESS']), 'to_df')

        else:
            if self.already_in(request['ID'], self.client_list):
                return
            iD, addr = self.assign_clients()
            if iD == self.id:
                self.accept(request)
                self.state_update()
            self.remote_para_set(tuple(request['CONTENT']['UDP_ADDRESS']),
                                 MAINSERVER=(self.MY_IP, self.UDP_PORT),
                                 is_member=True,
                                 CONTACT_SERVER=addr)
            if iD != self.id:
                self.remote_methode_invocation(tuple(request['CONTENT']['UDP_ADDRESS']), 'join_contact')

    @staticmethod
    def already_in(iD, table: list) -> bool:
        """
        HELPER FUNCTION:
        To determine whether the id appears in the server/client list
        :param iD:
        :param table:
        :return:
        """
        for ele in table:
            if ele['ID'] == iD:
                return True
        return False

    def to_df(self):
        if isinstance(self.server_list, dict):
            self.server_list = pd.DataFrame(self.server_list)

    def accept(self, request: dict) -> None:
        """
        HELPER FUNCTION:
        this function can only handle the client arrangement!!!
        :param request:
        :return:
        """
        # content = {'CONTACT_SERVER': (self.MY_IP, self.UDP_PORT), 'is_member': True}
        # if request['CONTENT']['TYPE'] == 'CLIENT':
        if self.already_in(request['ID'], self.client_list):
            return
        self.client_list.append({'ID': request['ID'], 'ADDRESS': tuple(request['CONTENT']['UDP_ADDRESS'])})
        self.num_clients += 1

    def heartbeat_sender(self):
        while True:
            if self.TERMINATE:
                break
            print('Heart beating...')
            message = self.create_message('HEARTBEAT', {'UDP_ADDRESS': (self.MY_IP, self.UDP_PORT)})
            # a server sends it's heartbeat to all his connected clients
            for client in self.client_list:
                self.udp_send_without_response(client['ADDRESS'], message)
            # the main server sends his heartbeat to all other servers, the other servers only to the main server
            if self.is_main:
                for server in self.server_list:
                    if server['ID'] is not self.id:
                        self.udp_send_without_response(server['ADDRESS'], message)
            else:
                self.udp_send(MAIN_SERVER, message)
            time.sleep(self.HEARTBEAT_RATE)

    def assign_clients(self):
        """
        HELPER FUNCTION:
        assign the new client to the server which has the least number of clients
        :return: the id of the server to be assigned
        """
        # candidate = self.server_list['ID']
        # for server in self.server_list:
        #     if server['NUMBER'] < candidate['NUMBER']:
        #         candidate = server
        # return candidate['ID'], candidate['ADDRESS']
        result = self.server_list[self.server_list['NUMBER'] == self.server_list['NUMBER'].max()].iloc[0]
        return result['ID'], result['ADDRESS']

    def interface(self) -> None:
        while True:
            print(Fore.LIGHTBLUE_EX + '*' * 60 + Style.RESET_ALL)
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
            elif user_input == 'leave':
                if self.is_main:
                    print(Fore.RED + 'Main Server cannot leave!' + Style.RESET_ALL)
                    # TODO: when election then yes
                else:
                    self.is_member = False
                    self.MAIN_SERVER = None
                    print('Dis-attached with Main-server!')
                self.report()
            elif user_input == 'clear':
                self.clear_screen()
            else:
                print(Fore.RED + 'Invalid input!' + Style.RESET_ALL)

    def state_update(self) -> None:
        self.to_df()
        # result = next((ser for ser in self.server_list if ser['ID'] == self.id), None)
        # result['NUMBER'] = self.num_clients
        self.server_list.loc[self.server_list['ID'] == self.id, 'NUMBER'] = self.num_clients


@click.command()
@click.option('--port', required=True, default=10001, type=int, help='The port that the server connect to')
@click.option('--opt', required=True, default=1, type=int, help='whether the server is entry point of the system')
def main(port, opt):
    Server(port, opt == 1)


if __name__ == '__main__':
    main()
