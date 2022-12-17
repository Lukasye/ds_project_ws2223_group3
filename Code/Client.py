import click
import time
from colorama import Fore, Style
from auction_component import auction_component


class Client(auction_component):
    def __init__(self,
                 UDP_PORT):
        super().__init__('CLIENT', UDP_PORT)
        # self.leader = None
        self.current_bid = 0
        self.is_member = False
        self.report()
        # open multiple thread to do different jobs
        self.warm_up([self.broadcast_listen, self.udp_listen, self.check_hold_back_queue])

    def report(self):
        message = '{} activate on\n' \
                  'ID: \t\t\t{}\n' \
                  'Address: \t\t{}:{} \n' \
                  'Is member: \t\t{}\n' \
                  'Main Server: \t\t{}\n' \
                  'Contact Server: \t{}\n' \
                  'Sequence number: \t{}'.format(self.TYPE, self.id, self.MY_IP, self.UDP_PORT,
                                                 self.is_member, self.MAIN_SERVER, self.CONTACT_SERVER,
                                                 self.sequence_counter)
        info = '$$$$\t' + 'Highest_bid:{}\t Winner:{}'.format(self.highest_bid, self.winner) + '\t$$$$'
        print(Fore.LIGHTYELLOW_EX + message + Style.RESET_ALL)
        print(Fore.RED + info + Style.RESET_ALL)

    def logic(self, response: dict):
        method = response['METHOD']
        self.print_message(response)
        # ********************** METHOD DISCOVERY **********************************
        if method == 'DISCOVERY':
            if not self.is_member:
                self.join(tuple(response['CONTENT']['UDP_ADDRESS']))
            elif self.MAIN_SERVER is not None:
                self.forward(self.MAIN_SERVER, response)
        # **********************    METHOD SET     **********************************
        elif method == 'SET':
            tmp = response['CONTENT']
            for key in tmp:
                # print('self.{} = {}'.format(key, tmp[key]))
                exec('self.{} = {}'.format(key, tmp[key]))
            self.state_update()
        # # ********************** METHOD PRINT **********************************
        elif method == 'PRINT':
            print(response['CONTENT']['PRINT'])
        # **********************  METHOD HEARTBEAT **********************************
        elif method == 'HEARTBEAT':
            self.heartbeat_receiver(response)
        # ****************  METHOD REMOTE METHOD INVOCATION **************************
        elif method == 'RMI':
            exec(response['CONTENT']['METHODE'])
        elif method == 'TEST':
            # ignore test signals
            pass
        else:
            print(response)

    def join_contact(self):
        self.join(tuple(self.CONTACT_SERVER))
        
    def leave(self) -> None:
        self.is_member = False
        self.MAIN_SERVER = None
        self.CONTACT_SERVER = None
        self.sequence_counter = 0

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
            elif user_input.startswith('bit'):
                info = user_input.split(' ')
                message = self.create_message('BIT', {'UDP_ADDRESS': (self.MY_IP, self.UDP_PORT),
                                                      'PRICE': info[1]})
                if self.CONTACT_SERVER is not None:
                    self.udp_send(tuple(self.CONTACT_SERVER), message)
            elif user_input == 'leave':
                self.leave()
                print('Dis-attached with Main-server!')
                self.report()
            elif user_input == 'queue':
                self.print_hold_back_queue()
            elif user_input == 'seq_hist':
                for ele in self.multicast_hist:
                    print(ele)
            elif user_input == 'intercept':
                self.intercept = True
                print('Intercepting the next incoming message...')
            elif user_input == 'clear':
                self.clear_screen()
            else:
                print(Fore.RED + 'Invalid input!' + Style.RESET_ALL)

    def heartbeat_sender(self):
        while True:
            if self.TERMINATE:
                break
            message = self.create_message('HEARTBEAT', {'ID': self.id})
            # a client sends it's heartbeat to all his contact server
            if self.CONTACT_SERVER is not None:
                self.udp_send_without_response(self.get_port(self.CONTACT_SERVER, 'HEA'), message)
                
                # we check how long it was since the last heartbeat of our contact server
                if self.CONTACT_SERVER['HEARTBEAT'] - self.timestamp() > self.HEARTBEAT_RATE * 1000 * 3:
                    # if it's been longer than three times the heartbeat rate,
                    # we'll accept that we've lost out connection and try to reconnect
                    self.leave()
                    self.find_others()
            
            time.sleep(self.HEARTBEAT_RATE)

    def heartbeat_receiver(self, request: dict):
        # we should only get heartbeats from our contact server. Heartbeats from everybody else can be ignored
        if self.CONTACT_SERVER is not None:
            if request['CONTENT']['ID'] == self.CONTACT_SERVER['ID']:
                # the last time we got a heartbeat from our contact server was right now
                self.CONTACT_SERVER['HEARTBEAT'] = self.timestamp()

    def state_update(self) -> None:
        pass


@click.command()
@click.option('--port', required=True, default=5700, type=int, help='The port that the server connect to')
def main(port):
    Client(port)


if __name__ == '__main__':
    main()
