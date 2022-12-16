import click
import time
import socket
from colorama import Fore, Style

from auction_component import auction_component
from group_member_service import group_member_service
import utils


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_main: bool = False):
        super(Server, self).__init__('SERVER', UDP_PORT)
        self.SEQ_PORT = UDP_PORT + 4
        self.bid_history = []
        self.num_servers = 1
        self.num_clients = 0
        # self.server_list = pd.DataFrame([{'ID': self.id, 'ADDRESS': (self.MY_IP, self.UDP_PORT), 'NUMBER': 0,
        # 'HEARTBEAT': self.timestamp()}])
        # self.client_list = pd.DataFrame()
        self.gms = group_member_service(self.MY_IP, self.id, self.TYPE, self.GMS_PORT)
        self.gms.add_server(self.id, (self.MY_IP, self.UDP_PORT))
        self.is_main = is_main
        # initialize depends on whether this is the main server
        warm_up_list = [self.udp_listen, self.broadcast_listen, self.check_hold_back_queue]
        if is_main:
            self.is_member = True
            self.MAIN_SERVER = (self.MY_IP, self.UDP_PORT)
            self.sequencer = 0
            warm_up_list.append(self.sequence_listen)
        else:
            self.is_member = False
        self.report()
        # open multiple thread to do different jobs
        self.warm_up(warm_up_list)

    def report(self):
        message = '{} activate on\n' \
                  'ID: \t\t\t{}\n' \
                  'Address: \t\t{}:{} \n' \
                  'Broadcast: \t\t{}:{}\n' \
                  'Main Server: \t\t{}\n' \
                  'Number of Clients: \t{}\n' \
                  'Sequence number: \t{}'.format(self.TYPE, self.id, self.MY_IP, self.UDP_PORT,
                                                 self.BROADCAST_IP, self.BROADCAST_PORT,
                                                 self.MAIN_SERVER, self.num_clients,
                                                 self.sequence_counter)
        info = '$$$$\t' + 'Highest_bid:{}\t Winner:{}'.format(self.highest_bid, self.winner) + '\t$$$$'
        print(Fore.LIGHTYELLOW_EX + message + Style.RESET_ALL)
        print(Fore.RED + info + Style.RESET_ALL)

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
                # print('self.{} = {}'.format(key, tmp[key]))
                exec('self.{} = {}'.format(key, tmp[key]))
        # **********************  METHOD REDIRECT **********************************
        elif method == 'REDIRECT':
            if self.is_main:
                self.receive(request['CONTENT']['MESSAGE'])
        # **********************  METHOD RAISE BIT **********************************
        elif method == 'BIT':
            # if self.is_main:
            #     self.sequencer += 1
            #     request['SEQUENCE'] = self.sequencer
            #     request['ID'] = self.id
            #     self.multicast_send_without_response(self.server_list['ADDRESS'].to_list(),
            #                                          request)
            # else:
            price = int(request['CONTENT']['PRICE'])
            if price < self.highest_bid:
                message = self.create_message('PRINT', {'PRINT': 'Invalid Price, the highest bid now is {}'. format(self.highest_bid)})
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), message)
            else:
                sequence = self.sequence_send()
                # request['SEQUENCE'] = sequence
                # request['ID'] = self.id
                # message = self.create_message('SET', SEQUENCE=sequence, CONTENT={'highest_bid': price,
                #                                                                  'winner': request['ID']})
                # self.multicast_send_without_response(self.server_list['ADDRESS'].to_list(),
                #                                      message)
                # self.remote_para_set(self.server_list['ADDRESS'].to_list(), SEQUENCE=sequence, highest_bid=price,
                #                      winner=request['SENDER_ADDRESS'], update=True)
                self.gms.group_synchronise()
                # self.remote_methode_invocation(self.server_list['ADDRESS'].to_list(), 'pass_on')
                # foobar
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), self.create_message('WINNER', {}))
                self.bid_history.append(request)
        # **********************  METHOD HEARTBEAT **********************************
        elif method == 'HEARTBEAT':
            self.heartbeat_receiver(request)
        # ****************  METHOD REMOTE METHOD INVOCATION **************************
        elif method == 'RMI':
            exec('self.{}()'.format(request['CONTENT']['METHODE']))
        elif method == 'TEST':
            # ignore test signals
            pass
        else:
            print(request)

    def assign(self, request: dict) -> None:
        """
        HELPER FUNCTION:
        assign the join request to the right server to balance the performance
        :param request: dict, request receipted from the client or server
        :return:
        """
        if request['CONTENT']['TYPE'] == 'SERVER':
            if self.gms.is_member(request['ID'], 'SERVER'):
                return
            # self.server_list.append({'ID': request['ID'], 'ADDRESS': tuple(request['CONTENT']['UDP_ADDRESS']),
            #                          'NUMBER': 0})
            # new_row = pd.Series({'ID': request['ID'], 'ADDRESS': tuple(request['CONTENT']['UDP_ADDRESS']),
            #                      'NUMBER': 0})
            # self.server_list = pd.concat([self.server_list, new_row.to_frame().T], ignore_index=True)
            self.gms.add_server(request['ID'], tuple(request['CONTENT']['UDP_ADDRESS']))
            self.num_servers += 1

            self.remote_para_set(self.gms.get_server_address(),
                                 MAIN_SERVER=(self.MY_IP, self.UDP_PORT),
                                 is_member=True)
            self.gms.group_synchronise()
            # self.remote_methode_invocation(self.server_list['ADDRESS'].to_list(),
            #                                'to_df')
        else:
            if self.gms.is_member(request['ID'], 'CLIENT'):
                return
            iD, addr = self.assign_clients()
            if iD == self.id:
                self.accept(request)
                self.state_update()
            self.remote_para_set([request['CONTENT']['UDP_ADDRESS']],
                                 MAIN_SERVER=(self.MY_IP, self.UDP_PORT),
                                 is_member=True,
                                 CONTACT_SERVER=addr)
            if iD != self.id:
                self.remote_methode_invocation([request['CONTENT']['UDP_ADDRESS']], 'join_contact')

    # @staticmethod
    # def already_in(iD, table: list) -> bool:
    #     """
    #     HELPER FUNCTION:
    #     To determine whether the id appears in the server/client list
    #     :param iD:
    #     :param table:
    #     :return:
    #     """
    #     for ele in table:
    #         if ele['ID'] == iD:
    #             return True
    #     return False

    # def to_df(self):
    #     if isinstance(self.server_list, dict):
    #         self.server_list = pd.DataFrame(self.server_list)

    def pass_on(self):
        # TODO: here maybe need to add RMI with parameters
        self.remote_para_set(self.gms.get_client_address(), highest_bid=self.highest_bid, winner=self.winner)

    def accept(self, request: dict) -> None:
        """
        HELPER FUNCTION:
        this function can only handle the client arrangement!!!
        :param request:
        :return:
        """
        # content = {'CONTACT_SERVER': (self.MY_IP, self.UDP_PORT), 'is_member': True}
        # if request['CONTENT']['TYPE'] == 'CLIENT':
        # if self.already_in(request['ID'], self.client_list):
        if self.gms.is_member(request['ID'], 'CLIENT'):
            return
        # self.client_list.append({'ID': request['ID'], 'ADDRESS': tuple(request['CONTENT']['UDP_ADDRESS'])})
        self.gms.add_client(request['ID'], tuple(request['CONTENT']['UDP_ADDRESS']))
        self.num_clients += 1

    def heartbeat_sender(self):
        while True:
            if self.TERMINATE:
                break
            message = self.create_message('HEARTBEAT', {'ID': self.id})
            targets = []
            # a server sends it's heartbeat to all his connected clients
            if not self.client_list.empty:
                for clientAddress in self.client_list['ADDRESS'].to_list():
                    targets.append(self.get_port(clientAddress, 'HEA'))
            # the main server sends his heartbeat to all other servers, the other servers only to the main server
            if self.is_main:
               for serverAddress in self.server_list['ADDRESS'].to_list():
                    targets.append(self.get_port(serverAddress, 'HEA'))
            else:
                targets.append(self.get_port(self.MAIN_SERVER, 'HEA'))
                
            self.multicast_send_without_response(targets, message)
            time.sleep(self.HEARTBEAT_RATE)
            
    def heartbeat_receiver(self, request: dict):
        # we look for the sender of the heartbeat among all the servers and clients we're connected to,
        # and update the last heartbeat time when we find them
        self.server_list.loc[self.server_list['ID'] == request['CONTENT']['ID'], 'HEARTBEAT'] = self.timestamp()
        self.client_list.loc[self.server_list['ID'] == request['CONTENT']['ID'], 'HEARTBEAT'] = self.timestamp()
                
    def assign_clients(self):
        """
        HELPER FUNCTION:
        assign the new client to the server which has the least number of clients
        :return: the id of the server to be assigned
        """
        return self.gms.assign_clients()

    def sequence_listen(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.MY_IP, self.SEQ_PORT))
        while not self.TERMINATE:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                # message = json.loads(data.decode())
                # message = pickle.loads(data)
                # TODO: may need some logic
                self.sequencer += 1
                message = self.create_message('SEQUENCE', {'SEQ': self.sequencer})
                self.udp_send_without_response(address, message)

    def sequence_send(self):
        assert self.MAIN_SERVER is not None
        message = self.create_message('SEQUENCE', {})
        sequence = self.udp_send(utils.get_port(tuple(self.MAIN_SERVER), 'SEQ'), message)
        return sequence['CONTENT']['SEQ']

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
                self.gms.print_server()
            elif user_input == 'client':
                self.gms.print_client()
            elif user_input == 'join':
                self.join(None, True)
            elif user_input == 'seq':
                print(self.sequence_send())
            elif user_input == 'queue':
                self.print_hold_back_queue()
            elif user_input == 'seq_hist':
                for ele in self.multicast_hist:
                    print(ele)
            elif user_input.startswith('rmi'):
                info = user_input.split(' ')
                self.remote_methode_invocation([('172.17.112.1', int(info[1]))], info[2])
            elif user_input == 'history':
                for ele in self.bid_history:
                    print(ele)
            elif user_input == 'multi1':
                # multi test
                print('Reliable multicast test (Part 1)...')
                address = '141.58.50.65'
                self.multicast_send_without_response([(address, 5700)],
                                                     self.create_message('TEST', SEQUENCE=1, CONTENT={'N': 1}))
                self.multicast_send_without_response([(address, 5700)],
                                                     self.create_message('TEST', SEQUENCE=2, CONTENT={'N': 2}), test=0)
                self.multicast_send_without_response([(address, 5700)],
                                                     self.create_message('TEST', SEQUENCE=3, CONTENT={'N': 3}))
                self.multicast_send_without_response([(address, 5700)],
                                                     self.create_message('TEST', SEQUENCE=4, CONTENT={'N': 4}))
            elif user_input == 'multi2':
                address = '141.58.50.65'
                print('Reliable multicast test (Part 2)...')
                self.multicast_send_without_response([(address, 5700)],
                                                     self.create_message('TEST', SEQUENCE=5, CONTENT={'N': 5}))
            elif user_input == 'intercept':
                self.intercept = True
                print('Intercepting the next incoming message...')
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
        # self.to_df()
        # result = next((ser for ser in self.server_list if ser['ID'] == self.id), None)
        # result['NUMBER'] = self.num_clients
        # self.server_list.loc[self.server_list['ID'] == self.id, 'NUMBER'] = self.num_clients
        pass


@click.command()
@click.option('--port', required=True, default=10001, type=int, help='The port that the server connect to')
@click.option('--opt', required=True, default=1, type=int, help='whether the server is entry point of the system')
def main(port, opt):
    Server(port, opt == 1)


if __name__ == '__main__':
    main()
