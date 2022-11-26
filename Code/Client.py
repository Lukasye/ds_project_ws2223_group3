from auction_component import auction_component


class Client(auction_component):
    def __init__(self):
        super().__init__()
        self.TYPE = 'CLIENT'
        self.leader = None
        self.current_bid = 0
        self.highest_bid = 0
        self.is_member = False
        self.MAIN_SERVER = None

    def report(self):
        message = '{} activate on\n' \
                  'Address: \t{}:{} \n' \
                  'Main Server: \t{}'.format(self.TYPE, self.MY_IP, self.BROADCAST_PORT, self.MAIN_SERVER)
        print(message)

    def logic(self, response: dict):
        method = response['METHOD']
        if method == 'DISCOVERY':
            if not self.is_member:
                message = self.create_message('DISCOVERY', {'type': self.TYPE})
                print('Sent to', response['CONTENT']['ADDRESS'])
                self.udp_send(tuple(response['CONTENT']['ADDRESS']), message)
            else:
                message = self.create_message('REDIRECT', {'type': 'DISCOVERY',
                                                           'ADDRESS': self.leader})
                self.udp_send(response['SENDER_ADDRESS'], message)
        elif method == 'ACCEPT':
            self.is_member = True
            self.leader = response['CONTENT']['ADDRESS']
        elif method == 'REDIRECT':
            message = self.create_message(response['CONTENT']['type'],
                                          {'type': self.TYPE})
            self.udp_send(response['CONTENT']['ADDRESS'], message)


def main():
    test_component = Client()
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
        else:
            print('Invalid input!')


if __name__ == '__main__':
    main()
