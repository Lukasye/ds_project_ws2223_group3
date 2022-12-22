import click
import time
from rich import print
from auction_component import auction_component
from group_member_service import group_member_service


class Client(auction_component):
    def __init__(self,
                 UDP_PORT):
        super().__init__('CLIENT', UDP_PORT)
        self.current_bid = 0
        self.is_member = False
        self.report()
        # open multiple thread to do different jobs
        self.gms = group_member_service(self.MY_IP, self.id, self.TYPE, self.GMS_PORT)
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
        info = '\t' + 'Highest_bid: {}\t Winner: {}'.format(self.highest_bid, self.winner) + '\t'
        print(":iphone:" + "\t" + message)
        print(":moneybag:" + info + ":moneybag:")

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
            self.console.print('*' * 60, style="yellow")
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
                self.console.print('Invalid input!', style="bold red")

    def state_update(self) -> None:
        pass


@click.command()
@click.option('--port', required=True, default=5700, type=int, help='The port that the server connect to')
def main(port):
    Client(port)


if __name__ == '__main__':
    main()
