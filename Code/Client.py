import click
from auction_component import auction_component, bcolors


class Client(auction_component):
    def __init__(self,
                 UDP_PORT):
        super().__init__('CLIENT', UDP_PORT)
        # self.leader = None
        self.current_bid = 0
        self.highest_bid = 0
        self.is_member = False
        self.MAIN_SERVER = None
        self.CONTACT_SERVER = None
        self.report()
        # open multiple thread to do different jobs
        self.warm_up([self.broadcast_listen, self.udp_listen])

    def report(self):
        message = '{} activate on\n' \
                  'ID: \t\t\t{}\n' \
                  'Address: \t\t{}:{} \n' \
                  'Is member: \t\t{}\n' \
                  'Main Server: \t\t{}\n' \
                  'Contact Server: \t{}'.format(self.TYPE,self.id, self.MY_IP, self.UDP_PORT,
                                                self.is_member, self.MAIN_SERVER, self.CONTACT_SERVER)
        print(message)

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
                exec('self.{} = {}'.format(key, tmp[key]))
            self.state_update()
        # **********************  METHOD HEARTBEAT **********************************
        elif method == 'HEARTBEAT':
            # TODO: response to the heartbeat
            pass
        # # ********************** METHOD REDIRECT **********************************
        # elif method == 'REDIRECT':
        #     message = self.create_message(response['CONTENT']['type'],
        #                                   {'type': self.TYPE})
        #     self.udp_send(response['CONTENT']['ADDRESS'], message)
        # **********************  METHOD HEARTBEAT **********************************
        elif method == 'RMI':
            exec('self.{}()'.format(response['CONTENT']['METHODE']))
        else:
            print(response)

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
            elif user_input == 'leave':
                self.is_member = False
                self.MAIN_SERVER = None
                self.CONTACT_SERVER = None
                print('Dis-attached with Main-server!')
                self.report()
            else:
                print('Invalid input!')

    def state_update(self) -> None:
        pass

    def foo(self):
        print("I'm working...")
        return 0


@click.command()
@click.option('--port', required=True, default=5700, type=int, help='The port that the server connect to')
def main(port):
    Client(port)


if __name__ == '__main__':
    main()
