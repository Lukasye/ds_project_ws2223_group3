import calendar
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


def udp_send(address: tuple, message, timeout: int = 5) -> dict:
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
    elif PORT == 'BRO':
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


def get_broadcast_address(ip, netmask):
    """
    calculate broadcast address
    :param ip:
    :param netmask:
    :return:
    """
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
