import time
import threading
import socket
import pickle

import utils
import config as cfg


class global_time_sync:
    def __init__(self, TYPE: str, iD, IP_ADDRESS: str, TIM_PORT):
        self.id = iD
        self.IP_ADDRESS = IP_ADDRESS
        self.TIM_PORT = TIM_PORT
        self.offset = 0
        self.SYNC_SERVER = None
        self.BUFFER_SIZE = cfg.attr['BUFFER_SIZE']
        self.SYNC_RATE = cfg.attr['SYNC_RATE']
        self.TYPE = TYPE
        self.TERMINATE = False
        self.threads = [self.time_synchronize]
        if self.TYPE == 'SERVER':
            self.threads.append(self.time_listen)
        for th in self.threads:
            t = threading.Thread(target=th, daemon=True)
            t.start()
            
    def close(self) -> None:
        """
        event that should be done when the auction is over
        :return:
        """
        self.TERMINATE = True
        
    def time_listen(self) -> None:
        """
        answer requests for the current time on the TIM_PORT
        :return:
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.IP_ADDRESS, self.TIM_PORT))
        
        while not self.TERMINATE:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                message = pickle.loads(data)
                method = message['METHOD']
                if method == 'SYNCREQUEST':
                    reply = utils.create_message(self.id, 'SYNCREPLY', {'SENDTIME': message['CONTENT']['SENDTIME'],
                                                                        'RCVTIME': self.get_time()})
                    utils.udp_send_without_response(address, reply)
                else:
                    print('Warning: Inappropriate message at time port.')

    def time_synchronize(self) -> None:
        """
        request updates of the current time from the sync server in regular intervals
        and use them to call the adjust_time function to update the time stamp
        :return:
        """
        
        while not self.TERMINATE:
            if self.SYNC_SERVER is not None:
                message = utils.create_message(self.id, 'SYNCREQUEST', {'SENDTIME': self.get_time()})
                
                try:
                    response = utils.udp_send(utils.get_port(self.SYNC_SERVER, 'TIM'), message)
                except ConnectionResetError:
                    # we lost the connection to our sync server -
                    # nothing we can do about it except wait until it comes back
                    response = None
                if response is None:
                    pass                # the request timed out - sucks, but not our problem
                elif response['METHOD'] == 'SYNCREPLY':
                    self.adjust_time(response['CONTENT']['SENDTIME'], response['CONTENT']['RCVTIME'])  
                else:
                    print('Warning: Inappropriate message at time port.')
               
            time.sleep(self.SYNC_RATE)

    def adjust_time(self, timestamp1, timestamp2) -> None:
        """
        use the given time stamps to adjust the time different between this process and
        the main one
        :return:
        """
        # we calculate the time it took for the timestamp the server sent us to get to us, which is half of the time
        # it took between our request and the response
        travel_time = (timestamp1 - self.get_time()) / 2
        # the new offset is the difference between server time plus travel time and the current system time
        self.offset = (timestamp2 + travel_time) - time.time()

    def get_time(self) -> float:
        """
        HELPER FUNCTION:
        take the local timestamp and add the offset to it
        :return: float seconds since epoch
        """
        return time.time() + self.offset

    def set_sync_server(self, SYNC_SERVER) -> None:
        """
        HELPER FUNCTION:
        set the server from which we get our information about the current time
        :return:
        """
        self.SYNC_SERVER = SYNC_SERVER


def test():
    pass


if __name__ == '__main__':
    test()
