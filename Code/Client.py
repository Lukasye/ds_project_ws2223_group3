import click
import random
import time
from threading import Lock

from auction_component import auction_component
from global_time_sync import global_time_sync
from group_member_service import group_member_service_client
import config as cfg
import utils


class Client(auction_component):
    def __init__(self,
                 UDP_PORT,
                 headless=False):
        super().__init__('CLIENT', UDP_PORT)
        self.current_bid = 0
        self.headless = headless
        self.gts = global_time_sync(self.TYPE, self.id, self.MY_IP, self.TIM_PORT)
        self.gms = group_member_service_client(self, self.MY_IP, self.id, self.UDP_PORT)
        self.lock = Lock()
        self.logging.info(self.report())
        # open multiple thread to do different jobs
        self.warm_up([self.broadcast_listen, self.udp_listen, self.check_hold_back_queue], headless)
        # introduce the global time synchronizer

    def shut_down(self) -> None:
        super().shut_down()
        self.gms.close()
        self.gts.close()

    def report(self):
        if self.headless:
            return
        message = '{} activate on\n' \
                  'ID: \t\t\t{}\n' \
                  'Address: \t\t{}:{} \n' \
                  'Is member: \t\t{}\n' \
                  'Main Server: \t\t{}\n' \
                  'Contact Server: \t{}\n' \
                  'Sequence number: \t{}'.format(self.TYPE, self.id, self.MY_IP, self.UDP_PORT,
                                                 self.gms.is_member, self.gms.MAIN_SERVER, self.gms.CONTACT_SERVER,
                                                 self.sequence_counter)
        utils.colorful_print(message + '\n', 'WARNING')
        return message

    def logic(self, response: dict):
        type_monitor = cfg.type_monitor
        method = response['METHOD']
        if not self.headless and method in type_monitor:
            self.print_message(response)
        # ************************************************************
        #               Method Discovery
        # ************************************************************
        if method == 'DISCOVERY':
            if not self.gms.is_member:
                self.join(tuple(response['CONTENT']['UDP_ADDRESS']))
            elif self.gms.MAIN_SERVER is not None:
                self.forward(self.gms.MAIN_SERVER, response)
        # ************************************************************
        #                 Method Join
        # ************************************************************
        elif method == 'JOIN':
            # don't deal with the join request
            pass
        # ************************************************************
        #                  Method Set
        # ************************************************************
        elif method == 'SET':
            tmp = response['CONTENT']
            for key in tmp:
                # print('self.{} = {}'.format(key, tmp[key]))
                exec('self.{} = {}'.format(key, tmp[key]))
            self.state_update()
        # ************************************************************
        #                  Method Print
        # ************************************************************
        elif method == 'PRINT':
            print(response['CONTENT']['PRINT'])
        # ****************  METHOD REMOTE METHOD INVOCATION **************************
        elif method == 'RMI':
            self.result = False
            command = response['CONTENT']['METHODE']
            exec(command)
            message = self.create_message('FOO', {'RESULT': self.result})
            self.udp_send_without_response(response['SENDER_ADDRESS'], message)
        elif method == 'TEST':
            # ignore test signals
            pass
        elif method == 'WINNER':
            # foobar message
            pass
        else:
            print('Unauthorized Message received! Please see log for more details.')
            self.logging.warning('Unauthorized message:', response)
    
    def pass_on(self, command, sequence: int = 0):
        # foobar function to get rid of bugs
        pass

    def join_contact(self):
        self.join(tuple(self.gms.CONTACT_SERVER))
        
    def leave(self) -> None:
        self.gms.is_member = False
        self.gms.MAIN_SERVER = None
        self.gms.CONTACT_SERVER = None
        self.sequence_counter = 1
        self.state_update()

    def end_game(self, winner):
        tmp = '$' * 40 + '\n' + 'Auction ended successfully!\n' + \
              f'Winner is {winner} with the price {self.highest_bid}!\n' + '$' * 40
        print(tmp)
        self.logging.debug(tmp)
        # self.logging.debug(self.bid_history

    def interface(self) -> None:
        while True:
            if not self.headless:
                print()
                utils.colorful_print('*' * 60, 'OKBLUE')
                utils.colorful_print(f'Time: {time.gmtime(self.gts.get_time())}', 'OKBLUE')
                info = 'Highest_bid: {}\t Winner: {}'.format(self.highest_bid, self.winner)
                utils.colorful_print(info, 'OKBLUE')
            print('')
            user_input = input('Please enter your command:')
            if user_input == '':
                continue
            else:
                self.logging.debug('User input: ' + user_input)
            if self.gms.CONTACT_SERVER is None:
                self.leave()
                self.find_others()
            # ************************************************************
            #                        Basic Functions
            # ************************************************************
            if user_input == 'exit':
                self.TERMINATE = True
                self.gms.close()
                self.gts.close()
                quit()
            elif user_input == 'report':
                self.report()
            elif user_input == 'find':
                self.find_others()
            elif user_input.startswith('bit'):
                print('Bit request sent out!')
                info = user_input.split(' ')
                message = self.create_message('BIT', {'UDP_ADDRESS': (self.MY_IP, self.UDP_PORT),
                                                      'PRICE': info[1]})
                if self.gms.CONTACT_SERVER is not None:
                    self.udp_send(tuple(self.gms.CONTACT_SERVER), message, receive=True)
            elif user_input == 'leave':
                self.leave()
                print('Dis-attached with Main-server!')
                self.shut_down()
                self.report()
            elif user_input == 'queue':
                self.print_hold_back_queue()
            elif user_input == 'history':
                utils.show_bid_hist(self.bid_history)
            elif user_input == 'seq_hist':
                for ele in self.multicast_hist:
                    print(ele)
            elif user_input == 'clear':
                self.clear_screen()
            # ************************************************************
            #                     Test Functions
            # ************************************************************
            elif user_input == 'intercept':
                self.intercept = 1
                print(f'Intercepting the next {self.intercept} incoming message...')
            else:
                print('Invalid input!')

    def state_update(self) -> None:
        self.gts.set_sync_server(self.gms.CONTACT_SERVER)
        self.gms.CONTACT_SERVER = self.CONTACT_SERVER


@click.command()
@click.option('--port', required=True, default=5700, type=int, help='The port that the server connect to')
def main(port):
    Client(port)


if __name__ == '__main__':
    main()
