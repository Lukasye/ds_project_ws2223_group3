import click
from auction_component import auction_component


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
                  'Address: \t{}:{} \n' \
                  'Is member: \t{}\n' \
                  'Main Server: \t{}'.format(self.TYPE, self.MY_IP, self.UDP_PORT, self.is_member, self.MAIN_SERVER)
        print(message)

    def logic(self, response: dict):
        method = response['METHOD']
        self.print_message(response)
        # ********************** METHOD DISCOVERY **********************************
        if method == 'DISCOVERY':
            if not self.is_member:
                self.join(tuple(response['CONTENT']['ADDRESS']))
            elif self.MAIN_SERVER is not None:
                self.forward(self.MAIN_SERVER, response)
        # **********************    METHOD SET     **********************************
        elif method == 'SET':
            tmp = response['CONTENT']
            for key in tmp:
                exec('self.{} = {}'.format(key, tmp[key]))
            self.state_update()
        # # ********************** METHOD REDIRECT **********************************
        # elif method == 'REDIRECT':
        #     message = self.create_message(response['CONTENT']['type'],
        #                                   {'type': self.TYPE})
        #     self.udp_send(response['CONTENT']['ADDRESS'], message)
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
            elif user_input == 'join':
                self.join(None, True)
            else:
                print('Invalid input!')

    def state_update(self) -> None:
        pass


@click.command()
@click.option('--port', required=True, default=5700, type=int, help='The port that the server connect to')
def main(port):
    Client(port)


if __name__ == '__main__':
    main()
