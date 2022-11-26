from queue import PriorityQueue


class hold_back_queue:
    def __init__(self):
        self.queue = PriorityQueue()
        self.COUNTER = 0

    def push(self, message):
        self.queue.put((message['SEQUENCE']), message)

    def is_empty(self) -> bool:
        return self.queue.empty()


class delivery_queue:
    def __init__(self):
        pass


if __name__ == '__main__':
    m = hold_back_queue()

