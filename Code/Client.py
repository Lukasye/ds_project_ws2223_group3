from auction_component import auction_component


class Client(auction_component):
    def __init__(self):
        super().__init__()

    def logic(self, request: dict):
        pass


if __name__ == '__main__':
    test_component = Client()
    for i in range(4):
        mess = test_component.create_message('DISCOVERY', {'type': 'client'})
        test_component.broadcast_send(mess)
