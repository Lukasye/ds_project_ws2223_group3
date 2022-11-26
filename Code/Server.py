import time
from auction_component import auction_component


class Server(auction_component):
    def __init__(self):
        super().__init__()
        self.HEARTBEAT_RATE = 5
        self.server_list = []

    def find_others(self):
        pass

    def logic(self, request: dict):
        if request['METHOD'] == 'DISCOVERY':
            print(request['CONTENT'])

    def heartbeat_sender(self):
        while True:
            print('Heart beating...')
            # TODO: implement heartbeat
            time.sleep(self.HEARTBEAT_RATE)


if __name__ == '__main__':
    test_component = Server()
    p1 = test_component.multi_processing(test_component.broadcast_listen())
    p1.start()
    p1.join()
