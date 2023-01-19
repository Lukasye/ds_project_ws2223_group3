import os
from collections.abc import Iterable
import calendar
import subprocess
import socket
import pickle
import time

import config as cfg


def udp_send_without_response(address: tuple, message):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.sendto(pickle.dumps(message), address)


def create_message(iD, METHOD: str, CONTENT: dict, SEQUENCE: int = 0):
    """
    HELPER FUNCTION:
    pack the info to generate as dict file for the transmitting
    :param iD: identification number of the sender
    :param SEQUENCE: the sequence number of the message
    :param METHOD: type of request
    :param CONTENT: body
    :return: dict object
    """
    return {'ID': iD,
            'METHOD': METHOD,
            'SEQUENCE': SEQUENCE,
            'CONTENT': CONTENT}


def udp_send(address: tuple, message, timeout: int = 5) -> None | dict:
    """
    normal udp send function
    :param address: the address of the recipient
    :param message: information any kind
    :param timeout: the number of seconds until a response needs to arrive
    :return: standard message format in dict, or None if a timeout occurs
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # udp_socket.sendto(str.encode(json.dumps(message)), address)
    message_byte = pickle.dumps(message)
    if len(message_byte) > cfg.attr['BUFFER_SIZE']:
        raise ValueError('Message too large')
    udp_socket.settimeout(timeout)
    try:
        udp_socket.sendto(message_byte, address)
        data, addr = udp_socket.recvfrom(cfg.attr['BUFFER_SIZE'])
        if data:
            data = pickle.loads(data)
            data['SENDER_ADDRESS'] = addr
            return data
    except TimeoutError:
        return None


def get_port(MAIN_SERVER: tuple, PORT: str = 'SEQ') -> tuple:
    addr = MAIN_SERVER[0]
    port = MAIN_SERVER[1]
    if PORT == 'UDP':
        port = port
    elif PORT == 'TIM':
        port += 1
    elif PORT == 'ELE':
        port += 2
    elif PORT == 'GMS':
        port += 3
    elif PORT == 'SEQ':
        port += 4
    else:
        raise ValueError('Input argument PORT not found!')
    return tuple([addr, port])


def get_broadcast_address():
    """
    calculate broadcast address
    :return:
    """
    ip = get_ip_address()
    netmask = get_netmask(ip)
    ip = ip.split('.')
    netmask = netmask.split('.')
    broadcast = []
    for i in range(3):
        broadcast.append(str(int(ip[i]) | (255 - int(netmask[i]))))
    broadcast.append("255")
    return '.'.join(broadcast)


def timestamp() -> int:
    return calendar.timegm(time.gmtime())


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def get_netmask(ip):
    flag = os.name == 'nt'
    proc = subprocess.Popen('ipconfig' if flag else 'ifconfig', stdout=subprocess.PIPE)
    while True:
        line = proc.stdout.readline()
        if ip.encode() in line:
            break
    if flag:
        mask = proc.stdout.readline().rstrip().split(b':')[-1].replace(b' ', b'').decode()
    else:
        mask = line.rstrip().split(b':')[-1].replace(b' ', b'').decode()
    return mask


def flatten(lis):
    for item in lis:
        if isinstance(item, Iterable) and not isinstance(item, str):
            for x in flatten(item):
                yield x
        else:
            yield item


def check_list(result: list):
    return all(list(flatten(result)))


def most_common(lst: list):
    return max(set(lst), key=lst.count)


def show_bid_hist(bid_hist: list) -> None:
    for num, ele in enumerate(bid_hist):
        iD, price = ele
        content = f'{num}: \t {iD} \t {price}'
        print(content)


if __name__ == '__main__':
    print(get_broadcast_address())
