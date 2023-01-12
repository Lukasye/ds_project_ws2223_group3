import socket
import threading
import pandas
import pickle
import time

import utils
import config as cfg
import pandas as pd


class group_member_service:
    def __init__(self, IP_ADDRESS: str,
                 iD,
                 TYPE: str,
                 listen_port):
        self.TYPE = TYPE
        self.id = iD
        self.IP_ADDRESS = IP_ADDRESS
        self.listen_port = listen_port
        self.send_port = None
        self.server_list = \
            pd.DataFrame(columns=['ADDRESS', 'PORT', 'number_of_client', 'time_stamp']).astype(
                {'number_of_client': 'int32'}) if self.TYPE == 'SERVER' else None
        self.client_list = pd.DataFrame(columns=['ADDRESS', 'PORT', 'time_stamp']) if self.TYPE == 'SERVER' else None
        self.BUFFER_SIZE = cfg.attr['BUFFER_SIZE']
        self.HEARTBEAT_RATE = cfg.attr['HEARTBEAT_RATE']
        self.TERMINATE = False
        self.threads = [self.heartbeat_listen, self.heartbeat_send]
        for th in self.threads:
            t = threading.Thread(target=th, daemon=True)
            t.start()

    @staticmethod
    def add_instance(iD, addr, port, df: pd.DataFrame):
        tmp = pd.DataFrame({'ADDRESS': addr, 'PORT': port}, index=[iD])
        df = pd.concat([df, tmp], ignore_index=False)
        return df

    def heartbeat_listen(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.IP_ADDRESS, self.listen_port))
        while not self.TERMINATE:
            data, address = server_socket.recvfrom(self.BUFFER_SIZE)
            if data:
                message = pickle.loads(data)
                if isinstance(message, pandas.DataFrame):
                    # if the incoming data is panda df, synchronize the df
                    self.server_list = message
                # elif isinstance(message, str):
                #     # if it is a string, means it is an iD that should be removed from the df
                #     self.remove_server(message)
                # elif isinstance(message, pandas.Series):
                #     # if it is a string, means it needs to be added to the df
                #     pass
                else:
                    if message['METHOD'] == 'HEAREQUEST':
                        reply = utils.create_message(self.id, 'HEAREPLY', {'ID': self.id})
                        self.udp_send_without_response(address, reply)
                    else:
                        print('Warning: Inappropriate message at heartbeat port.')
                pass

    def heartbeat_send(self):
        while True:
            if self.TERMINATE:
                break
                
            message = utils.create_message(self.id, 'HEAREQUEST', {'ID': self.id})
            
            if self.TYPE == 'CLIENT':
                pass
            else:
                pass
                
            time.sleep(self.HEARTBEAT_RATE)
        pass

    def ring_formation(self):
        # TODO
        pass

    def set_heartbeat_send_port(self, address: tuple):
        self.send_port = address

    def add_server(self, iD, addr: tuple, **kwargs):
        self.server_list = self.add_instance(iD, addr[0], addr[1], self.server_list)
        self.server_list.loc[iD, 'number_of_client'] = 0
        for ele in kwargs:
            self.server_list.loc[iD, ele] = kwargs[ele]
        self.group_synchronise()

    def add_client(self, iD, addr: tuple, **kwargs):
        self.client_list = self.add_instance(iD, addr[0], addr[1], self.client_list)
        for ele in kwargs:
            self.client_list.loc[iD, ele] = kwargs[ele]
        # increase the number of clients in server
        self.server_list.loc[self.id, 'number_of_client'] += 1

    def remove_server(self, iD):
        self.server_list = self.server_list.drop(iD, axis=0)

    def remove_client(self, iD):
        self.client_list = self.client_list.drop(iD, axis=0)

    def print_server(self):
        with pd.option_context('display.max_rows', None, 'display.max_columns',
                               None):
            print(self.server_list)

    def print_client(self):
        with pd.option_context('display.max_rows', None, 'display.max_columns',
                               None):
            print(self.client_list)

    def client_size(self):
        return len(self.client_list)

    def server_size(self):
        return len(self.server_list)

    def get_client_address(self, TYPE: str = 'UDP') -> list:
        """
        HELPER FUNCTION
        Get all the addresses of clients that store in the gms
        :param TYPE: specify the port you want to get
        :return: a list of tuple address
        """
        tmp = []
        for _, row in self.client_list.iterrows():
            result = (row['ADDRESS'], row['PORT'])
            tmp.append(utils.get_port(result, TYPE))
        return tmp

    def get_server_address(self, TYPE: str = 'UDP') -> list:
        """
        HELPER FUNCTION
        Get all the addresses of servers that store in the gms
        :param TYPE: specify the port you want to get
        :return: a list of tuple address
        """
        tmp = []
        for _, row in self.server_list.iterrows():
            result = (row['ADDRESS'], row['PORT'])
            tmp.append(utils.get_port(result, TYPE))
        return tmp

    def get_server_id(self) -> list:
        """
        HELPER FUNCTION
        Get all the id of servers that store in the gms
        :return: a list of tuple id
        """
        return self.server_list.index

    def get_all_address(self, TYPE: str = 'UDP'):
        return self.get_server_address(TYPE) + self.get_client_address(TYPE)

    def is_member(self, iD, TYPE: str = 'SERVER') -> bool:
        """
        HELPER FUNCTION
        determine whether the iD appears in the dataframe
        :param iD: the iD string of the process
        :param TYPE: either 'SERVER' or 'CLIENT'
        :return:
        """
        if TYPE == 'SERVER':
            return iD in self.server_list.index
        elif TYPE == 'CLIENT':
            return iD in self.client_list.index
        else:
            raise ValueError('TYPE can only be "SERVER" or "CLIENT"!')

    def close(self):
        self.TERMINATE = True

    def assign_clients(self) -> tuple:
        """
        HELPER FUNCTION
        return the server address with the least number of clients
        :return:
        """
        num = self.server_list['number_of_client'].argmin()
        iD = self.server_list.index[num]
        addr = tuple(self.server_list.loc[iD, ['ADDRESS', 'PORT']])
        return iD, addr

    def remote_synchronise(self, address: tuple) -> None:
        """
        HELPER FUNCTION
        synchronize the pandas dataframe with the object address
        :param address: the address of the process you want to sync with
        :return:
        """
        utils.udp_send_without_response(address, self.server_list)

    def group_synchronise(self) -> None:
        """
        HELPER FUNCTION
        synchronize with all the servers
        :return:
        """
        for member in self.get_server_address('GMS'):
            utils.udp_send_without_response(member, self.server_list)


def main():
    gms = group_member_service('192.168.0.200', 12341, 'SERVER', 4096)
    gms.add_server(1233234, ('123.123.123.123', 1634), time_stamp='asdf')
    gms.add_server(1455634, ('123.123.123.123', 1734), number_of_client=3)
    gms.add_server(1455934, ('123.123.123.123', 1834), time_stamp='a123')
    gms.add_server(1445834, ('123.123.123.123', 1234))
    gms.add_server(1111111, ('123.123.123.123', 1034))
    gms.remove_server(1111111)
    gms.print_server()
    print(gms.get_server_address())
    print(gms.server_size())
    print(gms.assign_clients())
    for ele in gms.get_server_id():
        print(ele)


if __name__ == '__main__':
    main()
