import click
from auction_component import auction_component


class Client(auction_component):
    def __init__(self,
                 UDP_PORT):
        super().__init__('CLIENT', UDP_PORT)
        self.leader = None
        self.current_bid = 0
        self.highest_bid = 0
        self.is_member = False
        self.MAIN_SERVER = None
        self.CONTACT_SERVER = None

    def report(self):
        message = '{} activate on\n' \
                  'Address: \t{}:{} \n' \
                  'Is member: \t{}\n' \
                  'Main Server: \t{}'.format(self.TYPE, self.MY_IP, self.UDP_PORT, self.is_member, self.MAIN_SERVER)
        print(message)

    def logic(self, response: dict):
        method = response['METHOD']
        self.print_message(response)
        if method == 'DISCOVERY':
            if not self.is_member:
                self.join(tuple(response['CONTENT']['ADDRESS']))
            else:
                pass
        elif method == 'SET':
            tmp = response['CONTENT']
            for key in tmp:
                exec('self.{} = {}'.format(key, tmp[key]))
        elif method == 'REDIRECT':
            message = self.create_message(response['CONTENT']['type'],
                                          {'type': self.TYPE})
            self.udp_send(response['CONTENT']['ADDRESS'], message)
        else:
            print(response)


@click.command()
@click.option('--port', required=True, default=5700, type=int, help='The port that the server connect to')
def main(port):
    test_component = Client(port)
    test_component.report()
    while True:
        print('*' * 50)
        user_input = input('Please enter your command:')
        if user_input == 'exit':
            quit()
        elif user_input == 'report':
            test_component.report()
        elif user_input == 'listen':
            test_component.broadcast_listen()
        elif user_input == 'join':
            test_component.join(('172.17.16.1', 10001))
        elif user_input == 'udp_listen':
            test_component.udp_listen()
        else:
            print('Invalid input!')


if __name__ == '__main__':
    main()
