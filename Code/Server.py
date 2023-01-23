from typing import List, Any

import click
import time
import socket

from auction_component import auction_component
from group_member_service import group_member_service_server
from global_time_sync import global_time_sync
import config as cfg
import utils


class Server(auction_component):
    def __init__(self,
                 UDP_PORT,
                 is_main: bool = False,
                 headless=False):
        super(Server, self).__init__('SERVER', UDP_PORT)
        self.SEQ_PORT = UDP_PORT + 4
        self.is_main = is_main
        self.headless = headless
        self.sequencer = 0
        
        # initialize depends on whether this is the main server
        warm_up_list = [self.udp_listen, self.broadcast_listen, self.check_hold_back_queue]
        if is_main:
            self.is_member = True
            self.MULTICAST_IP = cfg.attr['MULTICAST_IP']
            self.enable_multicast(self.MULTICAST_IP)
            MAIN_SERVER = (self.MY_IP, self.UDP_PORT)
            warm_up_list.append(self.sequence_listen)
        else:
            self.is_member = False
            MAIN_SERVER = None
        
        # introduce the group member service
        self.gms = group_member_service_server(self.MY_IP, self.id, self.UDP_PORT, self.is_main, MAIN_SERVER)
        self.gms.add_server(self.id, (self.MY_IP, self.UDP_PORT))
        # introduce the global time synchronizer
        self.gts = global_time_sync(self.TYPE, self.id, self.MY_IP, self.TIM_PORT, self.is_main)
        
        self.report()
        # open multiple thread to do different jobs
        self.warm_up(warm_up_list, self.headless)

    def shut_down(self) -> None:
        super().shut_down()
        self.gms.close()
        self.gts.end()
        if self.gms.is_main:
            self.sequencer = 0

    def report(self):
        if self.headless:
            return
        message = '{} activate on\n' \
                  'ID: \t\t\t{}\n' \
                  'Address: \t\t{}:{} \n' \
                  'Broadcast: \t\t{}:{}\n' \
                  'Main Server: \t\t{}\n' \
                  'Is_Main: \t\t{}\n' \
                  'Number of Clients: \t{}\n' \
                  'Sequence number: \t{}'.format(self.TYPE, self.id, self.MY_IP, self.UDP_PORT,
                                                 self.BROADCAST_IP, self.BROADCAST_PORT,
                                                 self.gms.MAIN_SERVER, self.gms.is_main, self.gms.client_size(),
                                                 self.sequence_counter)
        print("\t" + message + '\n')
        if self.gms.is_main:
            zusatz = 'Sequencer: \t\t{}'.format(self.sequencer)
            print(zusatz)
        return message

    def logic(self, request: dict):
        type_monitor = cfg.type_monitor
        method = request['METHOD']
        if not self.headless and method in type_monitor:
            self.print_message(request)
        # ************************************************************
        #                        Methode DISCOVERY
        # ************************************************************
        if method == 'DISCOVERY':
            # if the server is still not a member or a main server
            if not self.is_member and not self.gms.is_main:
                self.join(tuple(request['CONTENT']['UDP_ADDRESS']))
            else:
                if self.gms.is_main:
                    self.assign(request)
                elif self.gms.MAIN_SERVER is not None:
                    self.forward(self.gms.MAIN_SERVER, request)
        # ************************************************************
        #                        Methode JOIN
        # ************************************************************
        elif method == 'JOIN':
            # see if the join request come from itself
            if request['CONTENT']['UDP_ADDRESS'] == (self.MY_IP, self.UDP_PORT):
                return
            # if the server is not main, it can only accept
            if not self.gms.is_main and self.is_member and request['CONTENT']['TYPE'] == 'CLIENT':
                self.accept(request)
            if self.gms.is_main:
                self.assign(request)
            self.remote_methode_invocation([tuple(request['CONTENT']['UDP_ADDRESS'])],
                                           'self.negative_acknowledgement()')
        # ************************************************************
        #                        Methode SET
        # ************************************************************
        elif method == 'SET':
            tmp = request['CONTENT']
            for key in tmp:
                exec('self.{} = {}'.format(key, tmp[key]))
            self.state_update()
        # ************************************************************
        #                        Methode REDIRECT
        # ************************************************************
        elif method == 'REDIRECT':
            if self.gms.is_main:
                self.receive(request['CONTENT']['MESSAGE'])
        # ************************************************************
        #                        Methode BIT
        # ************************************************************
        elif method == 'BIT':
            # if the auction is started or already ended:
            if not self.in_auction:
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), self.create_message(
                    'PRINT', {'PRINT': 'Not in an auction!'}
                ))
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), self.create_message(
                    'multicast_send_without_response', {'in_auction': False}
                ))
                return
            if self.gms.server_size() < 4:
                # there aren't enough servers for byzentain agreement
                highst_bid = self.highest_bid
            else:
                print('Execute BZT agreement')
                command = 'self.result = self.reach_agreement();'
                self.remote_methode_invocation(self.gms.get_server_address(), command, multicast=True)
                highst_bid = self.highest_bid
            price = int(request['CONTENT']['PRICE'])
            if price < highst_bid:
                # if the bit is smaller than the current highest, nothing should be done.
                message = self.create_message('PRINT',
                                              {'PRINT': 'Invalid Price, '
                                                        'the highest bid now is {}'.format(self.highest_bid)})
                command = f'self.highest_bid={self.highest_bid};self.winner="{self.winner}";print("Invalid input! The highest bid now is {self.highest_bid}");'
                self.remote_methode_invocation([request['SENDER_ADDRESS']], command)
                # print(result)
            else:
                sequence = self.sequence_send()
                # message = self.create_message('SET', SEQUENCE=sequence, CONTENT={'highest_bid': price})
                tmp = request['ID']
                self.winner = tmp
                self.highest_bid = price
                command = f'self.highest_bid={price};self.winner="{tmp}";self.bid_history.append(("{tmp}", {price}));'
                self.notify_all(command=command, sequence=sequence, result=False)
                # result = self.notify_all(command=command, sequence=sequence)
                # result = utils.check_list(result)
                # if not result:
                #     print('Something went Wrong!!!!!!!!!!!')
                # foobar
                self.udp_send_without_response(tuple(request['SENDER_ADDRESS']), self.create_message('WINNER', {}))
        # ************************************************************
        #                        Methode PRINT
        # ************************************************************
        elif method == 'PRINT' and not self.headless:
            print(request['CONTENT']['PRINT'])
        # ************************************************************
        #              Methode REMOTE METHOD INVOCATION
        # ************************************************************
        elif method == 'RMI':
            self.result = False
            exec(request['CONTENT']['METHODE'])
            message = self.create_message('FOO', {'RESULT': self.result})
            self.udp_send_without_response(request['SENDER_ADDRESS'], message)
        # ************************************************************
        #                        Methode GET
        # ************************************************************
        elif method == 'GET':
            seq = request['CONTENT']['SEQ']
            if seq is not None and len(self.multicast_hist) >= seq > 0:
                archive = self.multicast_hist[seq - 1]
                print(archive)
                self.udp_send_without_response(request['SENDER_ADDRESS'], archive)
            else:
                # TODO: not tested yet
                content = {}
                for key in request['CONTENT']:
                    content[key] = request['CONTENT'][key]
                message = self.create_message('GET', content)
                self.udp_send_without_response(request['SENDER_ADDRESS'], message)
        # ************************************************************
        #                        Methode Price
        # ************************************************************
        elif method == 'PRICE':
            message = self.create_message('PRICE', {'PRICE': self.highest_bid})
            self.udp_send_without_response(request['SENDER_ADDRESS'], message=message)
            # self.agreement[request['ID']] = request['CONTENT']['PRICE']
            # self.send_agreement()
            # if len(self.agreement) == self.gms.server_size():
            #     self.agreement = {}
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
            command = f'self.gms.MAIN_SERVER=("{self.MY_IP}",{self.UDP_PORT}); ' \
                      f'self.is_member=True; self.enable_multicast("{self.MULTICAST_IP}");self.result = True;'
            # self.remote_para_set(self.gms.get_server_address(without=[self.id]),
            #                      MAIN_SERVER=(self.MY_IP, self.UDP_PORT),
            #                      is_member=True)
            self.remote_methode_invocation([tuple(request['CONTENT']['UDP_ADDRESS'])], command)
            # command = 'self.enable_multicast(); self.result = True;'
            # self.remote_methode_invocation([request['SENDER_ADDRESS']], command)
        else:
            if self.gms.is_member(request['ID'], 'CLIENT'):
                return
            iD, addr = self.assign_clients()
            if iD == self.id:
                self.accept(request)
            command = f'self.gms.MAIN_SERVER=("{self.MY_IP}",{self.UDP_PORT}); ' \
                      f'self.is_member=True; self.gms.CONTACT_SERVER={addr};self.result = True;'
            print(command) 
            self.remote_methode_invocation([request['CONTENT']['UDP_ADDRESS']], command)
            # self.remote_para_set([request['CONTENT']['UDP_ADDRESS']],
            #                      MAIN_SERVER=(self.MY_IP, self.UDP_PORT),
            #                      is_member=True,
            #                      CONTACT_SERVER=addr)
            if iD != self.id:
                self.remote_methode_invocation([request['CONTENT']['UDP_ADDRESS']], 'self.join_contact();')

    def notify_all(self, command: str, sequence: int = 0, result: bool = True):
        """
        HELPER FUNCTION:
        To run the command on all the processes in this auction
        :param command: str type, command that need to be passed on
        :param sequence: int type sequence number if necessary
        :return:
        """
        new_command = command + f"self.result = self.pass_on('{command}', {sequence});"
        result = self.remote_methode_invocation(self.gms.get_server_address(), new_command, SEQUENCE=sequence, result=result)
        return result

    def pass_on(self, command, sequence: int = 0):
        """
        HELPER FUNCTION:
        The methode that used to be invented remotely the pass all the command to the clients
        :param command: str type, command that need to be passed on
        :param sequence: int type sequence number if necessary
        :return: Dict, None or list
        """
        # tmp = self.winner
        # command = f' self.highest_bid={self.highest_bid};self.winner="{tmp}";self.result = True'
        command += 'self.result = True;'
        result = self.remote_methode_invocation(self.gms.get_client_address(), command, SEQUENCE=sequence)
        return result

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

    def sequence_send(self) -> int:
        """
        HELPER FUNCTION:
        send out request for a new sequence number
        :return: int type sequence number
        """
        assert self.gms.MAIN_SERVER is not None
        message = self.create_message('SEQUENCE', {})
        sequence = self.udp_send(utils.get_port(tuple(self.gms.MAIN_SERVER), 'SEQ'), message)
        return sequence['CONTENT']['SEQ']

    def start_auction(self, duration: int = 5):
        if self.in_auction:
            print('Already in an auction!')
            return
        command = 'self.in_auction = True;print("Auction Started!");self.report(); self.result = True'
        result = self.remote_methode_invocation(self.gms.get_client_address(), command)
        if all(result) or self.gms.client_size() == 0:
            self.in_auction = True
            print('Auction started!')
        else:
            print('Failed!')
        # t = threading.Thread(target=self.auction_timer, args=duration)
        # t.start()
        self.report()

    def end_auction(self):
        if not self.in_auction:
            print('Already in an auction!')
            return
        command = f'self.in_auction = False;print("Winner is {self.winner}!");self.report(); self.result = True'
        result = self.remote_methode_invocation(self.gms.get_client_address(), command)
        if all(result) or self.gms.client_size() == 0:
            self.in_auction = False
            print('Auction ended successfully!')
        else:
            print('Failed!')
        self.report()

    def update_interface(self) -> None:
        """
        HELPER FUNCTION:
        Send out RMI to refresh all the interface of the clients of this server process
        :return: None
        """
        command = 'self.report()'
        self.remote_methode_invocation(self.gms.get_client_address(), command)

    def auction_timer(self, duration: int):
        # TODO: not tested!
        start_time = self.gts.get_time()
        self.gts.start(duration)
        while True:
            current = self.gts.get_time()
            if current - start_time > duration:
                break
        self.gts.end()
        self.end_auction()

    def reach_agreement(self):
        price = []
        message = self.create_message('PRICE', {'PRICE': self.highest_bid})
        result = self.unicast_group_send(self.gms.get_server_address(without=[self.id]), message)
        for message in result:
            price.append(message['CONTENT']['PRICE'])
        self.highest_bid = utils.most_common(price)
        print(self.highest_bid)
        return self.highest_bid

    def interface(self) -> None:
        while True:
            if not self.headless:
                print('*' * 60)
                print(f'Time: {time.gmtime(self.gts.get_time())}')
                info = 'Highest_bid: {}\t Winner: {}'.format(self.highest_bid, self.winner)
                print(info)
            user_input = input('Please enter your command:')
            # ************************************************************
            #                        Basic Functions
            # ************************************************************
            if user_input == 'exit':
                # self.response = True
                self.shut_down()
                quit()
            elif user_input == 'report':
                self.report()
            elif user_input == 'find':
                self.find_others()
            elif user_input == 'clear':
                self.clear_screen()
            elif user_input.startswith('bit'):
                print('Wake up! You are a Server!!')
            elif user_input == 'start':
                if self.gms.is_main:
                    self.remote_methode_invocation(self.gms.get_server_address(), 'self.start_auction()')
                else:
                    print('You are not main!')
            elif user_input == 'end':
                self.remote_methode_invocation(self.gms.get_server_address(), 'self.end_auction()')
            elif user_input == 'join':
                self.join(None, True)
            # ************************************************************
            #                 Information Functions
            # ************************************************************
            elif user_input == 'server':
                self.gms.print_server()
            elif user_input == 'client':
                self.gms.print_client()
            elif user_input == 'seq':
                print(self.sequence_send())
            elif user_input == 'queue':
                self.print_hold_back_queue()
            elif user_input == 'seq_hist':
                for ele in self.multicast_hist:
                    print(ele)
            elif user_input == 'history':
                utils.show_bid_hist(self.bid_history)
            # ************************************************************
            #                     Test Functions
            # ************************************************************
            elif user_input == 'ring_test':
                ring_uuid, ring = self.gms.form_ring()
                print(ring_uuid)
                print(self.gms.get_neighbour(ring))
                command = 'self.gms.LCR(); self.result = True'
                self.remote_methode_invocation(self.gms.get_server_address(), command)
            elif user_input == 'multi1':
                # multi test
                print('Reliable multicast test (Part 1)...')
                address = '141.58.50.65'
                self.unicast_group_without_response([(address, 5700)],
                                                    self.create_message('TEST', SEQUENCE=1, CONTENT={'N': 1}))
                self.unicast_group_without_response([(address, 5700)],
                                                    self.create_message('TEST', SEQUENCE=2, CONTENT={'N': 2}), test=0)
                self.unicast_group_without_response([(address, 5700)],
                                                    self.create_message('TEST', SEQUENCE=3, CONTENT={'N': 3}))
                self.unicast_group_without_response([(address, 5700)],
                                                    self.create_message('TEST', SEQUENCE=4, CONTENT={'N': 4}))
            elif user_input == 'multi2':
                address = '141.58.50.65'
                print('Reliable multicast test (Part 2)...')
                self.unicast_group_without_response([(address, 5700)],
                                                    self.create_message('TEST', SEQUENCE=5, CONTENT={'N': 5}))
            elif user_input == 'intercept':
                self.intercept = 1
                print(f'Intercepting the next {self.intercept} incoming message...')
            elif user_input == 'leave':
                if self.gms.is_main:
                    self.gms.is_main = False
                    print('you are note main server anymore!')
                else:
                    self.is_member = False
                    self.gms.MAIN_SERVER = None
                    print('Dis-attached with Main-server!')
                self.gms.close()
                self.gms = group_member_service_server(self.MY_IP, self.id, self.UDP_PORT, self.gms.is_main)
                self.report()
            elif user_input == 'multicast_test':
                for i in range(10):
                    self.unicast_group_without_response(self.gms.get_server_address(),
                                                        self.create_message(METHOD='TEST', SEQUENCE=i,
                                                                            CONTENT={}), skip=0)
                self.unicast_group_without_response(self.gms.get_server_address(),
                                                    self.create_message(METHOD='TEST', SEQUENCE=10, CONTENT={}))
            elif user_input == 'bzt':
                # self.send_agreement()
                # result = self.reach_agreement()
                command = 'self.result = self.reach_agreement();'
                self.remote_methode_invocation(self.gms.get_server_address(), command)
            elif user_input.startswith('cheat'):
                info = user_input.split(' ')
                self.highest_bid = int(info[1])
            elif user_input == 'yy':
                print(self.gms.get_server_address(without=[self.id]))
            elif user_input == 'ml':
                self.multicast_listen()
            elif user_input == 'ms':
                message = self.create_message('ULTRA', {'FOO': 'BAR'})
                self.multicast_send(self.MULTICAST_IP, message=message)
            else:
                print('Invalid input!')

    def state_update(self) -> None:
        # self.to_df()
        # result = next((ser for ser in self.server_list if ser['ID'] == self.id), None)
        # result['NUMBER'] = self.num_clients
        # self.server_list.loc[self.server_list['ID'] == self.id, 'NUMBER'] = self.num_clients
        self.gms.set_main_server(self.gms.MAIN_SERVER)
        if not self.gms.is_main:
            self.gts.set_sync_server(self.gms.MAIN_SERVER)


@click.command()
@click.option('--port', required=True, default=10000, type=int, help='The port that the server connect to')
@click.option('--opt', required=True, default=1, type=int, help='whether the server is entry point of the system')
def main(port, opt):
    Server(port, opt == 1)


if __name__ == '__main__':
    main()
