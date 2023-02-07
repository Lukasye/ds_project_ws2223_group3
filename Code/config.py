attr = {'BROADCAST_PORT': 5972,
        'MULTICAST_PORT': 5007,
        'MULTICAST_IP': '224.1.1.1',
        'BUFFER_SIZE': 4096,
        'DURATION': 100,
        'HEARTBEAT_RATE': 5,
        'SYNC_RATE': 5,
        'NUMBER_PORTS': 4,
        'CLIENT_PORT_START': 5700,
        'SERVER_PORT_START': 10000, 
        'TIM_OFFSET': 1,
        'ELE_OFFSET': 2,
        'GMS_OFFSET': 3,
        'ENCODING': 'utf-8'
        }

window = {'time': (0, 1, 2, 70),
          'info': (3, 1, 10, 70),
          'result': (14, 1, 10, 70),
          'list': (0, 73, 21, 20),
          'input': (22, 73, 2, 20),
          }

color = {
        'HEADER' : '\033[95m',
        'OKBLUE' : '\033[94m',
        'OKCYAN' : '\033[96m',
        'OKGREEN' : '\033[92m',
        'WARNING' : '\033[93m',
        'FAIL' : '\033[91m',
        'ENDC' : '\033[0m',
        'BOLD' : '\033[1m',
        }

# type_monitor = ['RMI', 'BIT', 'JOIN', 'DISCOVERY']
type_monitor = []
