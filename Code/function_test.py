import time

from Server import Server
from Client import Client
from multiprocessing import Process

import config as cfg


def test_1(num: int = 4):
    """
    TEST FUNCTION:
    Test of dynamic discovery, whether the server can handle a large amount of clients.
    :param num: number of clients that we are going to create
    :return:
    """
    # initialization
    server_port = cfg.attr['SERVER_PORT_START']
    client_port = cfg.attr['CLIENT_PORT_START']
    step = 4
    client_list = []
    # create one main server
    mainServer = Server(server_port, is_main=True, headless=True)
    # create several clients
    for _ in range(num):
        client_list.append(Client(client_port, headless=True))
        client_port += step
    # send out dynamic discovery
    mainServer.find_others()
    time.sleep(1)
    print(mainServer.gms.client_size())
    # check if all clients are successfully connected
    assert mainServer.gms.client_size() == num
    print('Test Success!')


def test_2():
    server_port = cfg.attr['SERVER_PORT_START']
    mainServer = Server(server_port, is_main=True, headless=True)
    subServer = Server(server_port + 5, is_main=False)
    mainServer.find_others()
    time.sleep(0.5)
    for i in range(10):
        mainServer.unicast_group_without_response(mainServer.gms.get_server_address(),
                                                  mainServer.create_message(METHOD='TEST', SEQUENCE=i, CONTENT={}),
                                                  skip=0)
    mainServer.unicast_group_without_response(mainServer.gms.get_server_address(),
                                              mainServer.create_message(METHOD='TEST', SEQUENCE=10, CONTENT={}))
    time.sleep(0.5)
    print(subServer.sequence_counter)


if __name__ == '__main__':
    test_2()
