import click
import time
import socket
from rich import print

from auction_component import auction_component
from group_member_service import group_member_service
from global_time_sync import global_time_sync
import utils


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_main: bool = False,
                 headless=False):
        super(Server, self).__init__('SERVER', UDP_PORT)
        self.SEQ_PORT = UDP_PORT + 4
        self.bid_history = []
        self.is_main = is_main
        self.headless = headless
        # introduce the group member service
        self.gms = group_member_service(self.MY_IP, self.id, self.TYPE, self.GMS_PORT)
        self.gms.add_server(self.id, (self.MY_IP, self.UDP_PORT))
        # introduce the global time synchronizer
        self.gts = global_time_sync(self.TIM_PORT, self.is_main)

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
        self.warm_up(warm_up_list, self.headless)

    def report(self):
        if self.headless:
            return
        message = '{} activate on\n' \
                  'ID: \t\t\t{}\n' \
                  'Address: \t\t{}:{} \n' \
                  'Broadcast: \t\t{}:{}\n' \
                  'Main Server: \t\t{}\n' \
                  'Number of Clients: \t{}\n' \
                  'Sequence number: \t{}'.format(self.TYPE, self.id, self.MY_IP, self.UDP_PORT,
                                                 self.BROADCAST_IP, self.BROADCAST_PORT,
                                                 self.MAIN_SERVER, self.gms.client_size(),
                                                 self.sequence_counter)
        info = 'Highest_bid: {}\t Winner: {}'.format(self.highest_bid, self.winner)
        print(":desktop_computer:" + "\t" + message)
        print(":moneybag:" + info + ":moneybag:")

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
        # **********************  METHOD REDIRECT **********************************
        elif method == 'REDIRECT':
            if self.is_main:
                self.receive(request['CONTENT']['MESSAGE'])
        # **********************  METHOD RAISE BIT **********************************
        elif method == 'BIT':
            # if the auction is started or already ended:
            if not self.in_auction:
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), self.create_message(
                    'PRINT', {'PRINT': 'Not in an auction!'}
                ))
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), self.create_message(
                    'SET', {'in_auction': False}
                ))
                return
            price = int(request['CONTENT']['PRICE'])
            if price < self.highest_bid:
                # if the bit is smaller than the current highest, nothing should be done.
                message = self.create_message('PRINT',
                                              {'PRINT': 'Invalid Price, '
                                                        'the highest bid now is {}'. format(self.highest_bid)})
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), message)
            else:
                sequence = self.sequence_send()
                message = self.create_message('SET', SEQUENCE=sequence, CONTENT={'highest_bid': price})
                tmp = request['ID']
                self.winner = tmp
                self.highest_bid = price
                self.multicast_send_without_response(self.gms.get_all_address(), message)
                self.remote_methode_invocation(self.gms.get_all_address(), f'self.winner = "{tmp}"')
                self.remote_methode_invocation(self.gms.get_server_address(), 'self.pass_on()')
                # foobar
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), self.create_message('WINNER', {}))
                self.bid_history.append(request)
        # ********************** METHOD PRINT **********************************
        elif method == 'PRINT':
            self.console.print(request['CONTENT']['PRINT'], style='pink3')
        # ****************  METHOD REMOTE METHOD INVOCATION **************************
        elif method == 'RMI':
            exec(request['CONTENT']['METHODE'])
        # **************************  METHOD GET *********************************
        elif method == 'GET':
            seq = request['CONTENT']['SEQ']
            if seq is not None and len(self.multicast_hist) >= seq > 0:
                archive = self.multicast_hist[seq]
                self.udp_send_without_response(request['SENDER_ADDRESS'], archive)
            else:
                # TODO: not tested yet
                content = {}
                for key in request['CONTENT']:
                    content[key] = request['CONTENT'][key]
                message = self.create_message('GET', content)
                self.udp_send_without_response(request['SENDER_ADDRESS'], message)
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
            self.gms.add_server(request['ID'], tuple(request['CONTENT']['UDP_ADDRESS']))
            self.remote_para_set(self.gms.get_server_address(),
                                 MAIN_SERVER=(self.MY_IP, self.UDP_PORT),
                                 is_member=True)
        else:
            if self.gms.is_member(request['ID'], 'CLIENT'):
                return
            iD, addr = self.assign_clients()
            if iD == self.id:
                self.accept(request)
            self.remote_para_set([request['CONTENT']['UDP_ADDRESS']],
                                 MAIN_SERVER=(self.MY_IP, self.UDP_PORT),
                                 is_member=True,
                                 CONTACT_SERVER=addr)
            if iD != self.id:
                self.remote_methode_invocation([request['CONTENT']['UDP_ADDRESS']], 'self.join_contact()')

    def pass_on(self):
        tmp = self.winner
        self.remote_para_set(self.gms.get_client_address(), highest_bid=self.highest_bid)
        self.remote_methode_invocation(self.gms.get_client_address(), f'self.winner = "{tmp}"')

    def accept(self, request: dict) -> None:
        """
        HELPER FUNCTION:
        this function can only handle the client arrangement!!!
        :param request:
        :return:
        """
        if self.gms.is_member(request['ID'], 'CLIENT'):
            return
        self.gms.add_client(request['ID'], tuple(request['CONTENT']['UDP_ADDRESS']))

    def heartbeat_sender(self):
        while True:
            if self.TERMINATE:
                break
            message = self.create_message('HEARTBEAT', {'ID': self.id})
            targets = []
            # a server sends its heartbeat to all his connected clients
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

    def sequence_listen(self) -> None:
        """
        hear at port SEQ_PORT and raise every time by 1 when a message received and increase the seq number
        :return:
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.MY_IP, self.SEQ_PORT))
        while not self.TERMINATE:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                self.sequencer += 1
                message = self.create_message('SEQUENCE', {'SEQ': self.sequencer})
                self.udp_send_without_response(address, message)

    def sequence_send(self):
        assert self.MAIN_SERVER is not None
        message = self.create_message('SEQUENCE', {})
        sequence = self.udp_send(utils.get_port(tuple(self.MAIN_SERVER), 'SEQ'), message)
        return sequence['CONTENT']['SEQ']

    def start_auction(self):
        # TODO: send out announcement
        self.in_auction = True
        print('Auction started!')

    def end_auction(self):
        # TODO: send out announcement
        self.in_auction = False
        print('Auction ended!')

    def interface(self) -> None:
        while True:
            self.console.print('*' * 60, style='yellow')
            user_input = self.console.input('Please enter your command:')
            if user_input == 'exit':
                self.TERMINATE = True
                self.gms.close()
                quit()
            elif user_input == 'report':
                self.report()
            elif user_input == 'find':
                self.find_others()
            elif user_input == 'server':
                self.gms.print_server()
            elif user_input == 'client':
                self.gms.print_client()
            elif user_input == 'start':
                self.start_auction()
            elif user_input == 'end':
                self.end_auction()
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
                    self.console.print('Main Server cannot leave!', style='bold red')
                    # TODO: when election then yes
                else:
                    self.is_member = False
                    self.MAIN_SERVER = None
                    self.console.print('Dis-attached with Main-server!', style='bold red')
                self.report()
            elif user_input == 'clear':
                self.clear_screen()
            else:
                self.console.print('Invalid input!', style='bold red')

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
