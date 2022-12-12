from heapq import heapify, heappop, heappush


class hold_back_queue:
    class element:
        def __init__(self, info: dict):
            self.info = info
            self.SEQ = info['SEQUENCE']

        def __eq__(self, other):
            return self.SEQ == other.SEQ

        def __lt__(self, other):
            return self.SEQ < other.SEQ

        def __str__(self):
            return str(self.info)

    def __init__(self):
        self.heap = []
        self.counter = 1

    def print_heap(self):
        for ele in self.heap:
            print(ele)

    def push(self, message):
        num = message['SEQUENCE']
        # heappush(self.heap, element(message))
        if num == self.counter:
            self.counter += 1
        elif num > self.counter:
            self.negative_acknowledgment()
        else:
            # This message has already delivered
            pass

    def get(self, num):
        return self.heap[num]

    def negative_acknowledgment(self):
        # TODO: negative acknowledgment
        pass

    def has_next(self) -> bool:
        return bool(self.heap)


# class delivery_queue:
#     def __init__(self):
#         pass


if __name__ == '__main__':
    m = hold_back_queue()
    m.push({'SEQUENCE': 3, 'CONTENT': 'foobar'})
    m.push({'SEQUENCE': 1, 'CONTENT': 'foobar'})
    m.push({'SEQUENCE': 2, 'CONTENT': 'foobar'})
    m.push({'SEQUENCE': 4, 'CONTENT': 'foobar'})
    m.print_heap()
