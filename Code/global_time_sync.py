import time
import datetime
import threading
import socket

import utils
import config as cfg


class global_time_sync:
    def __init__(self, IP_ADDRESS: str, TIM_PORT, is_main):
        self.IP_ADDRESS = IP_ADDRESS
        self.TIM_PORT = TIM_PORT
        self.is_main = is_main
        self.threads = [self.time_listen()]
        self.timestamp = None
        for th in self.threads:
            t = threading.Thread(target=th, daemon=True)
            t.start()

    def start(self, duration):
        """
        event that should be done when the auction is started
        :param duration:
        :return:
        """
        pass

    def end(self):
        """
        event that should be done when the auction is over
        :return:
        """
        pass

    def time_listen(self):
        """
        use udp port TIM_PORT to listen to the time stamp main server sends out
        and pass the variable to adjust_time function to update the time stamp
        :return:
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.IP_ADDRESS, self.TIM_PORT))
        pass

    def adjust_time(self, timestamp):
        """
        use the given time stamp to adjust the time different between this process and
        the main one
        :return:
        """
        pass

    def get_time(self) -> str:
        """
        HELPER FUNCTION:
        take the local timestamp, convert to datetime formate and return
        for display on the interface
        :return: str format time
        """
        pass

    def set_is_main(self, is_main):
        self.is_main = is_main


def test():
    pass


if __name__ == '__main__':
    test()
