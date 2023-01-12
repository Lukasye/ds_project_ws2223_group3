import curses


attr = {'BROADCAST_PORT': 5972,
        'BUFFER_SIZE': 4096,
        'DURATION': 100,
        'HEARTBEAT_RATE': 5,
        'NUMBER_PORTS': 4,
        'CLIENT_PORT_START': 5700,
        'SERVER_PORT_START': 10001}

window = {'time': (0, 1, 2, 70),
          'info': (3, 1, 10, 70),
          'result': (14, 1, 10, 70),
          'list': (0, 73, 21, 20),
          'input': (22, 73, 2, 20),
          }

type_monitor = ['SET', 'RMI', 'GET', 'JOIN']
