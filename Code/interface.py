import curses
import time
from curses import wrapper
from curses.textpad import Textbox, rectangle

import config as cfg
from Server import Server
from auction_component import auction_component


class interface:
    def __init__(self, TYPE: str):
        self.TYPE = TYPE
        self.box = None
        self.TERMINATE = False
        print("Preparing to initialize screen...")
        self.update_screen()
        print("Screen initialized.")
        self.logic()

    def logic(self):
        count = 0
        while not self.TERMINATE:
            time.sleep(0.05)
            count += 1
            # self.update_screen()
            self.update_time(str(count))
            self.update_info('{} activate on\n' \
                             'ID: \t\t\t{}\n' \
                             'Address: \t\t{}:{} \n' \
                             'Broadcast: \t\t{}:{}\n' \
                             'Main Server: \t\t{}\n' \
                             'Number of Clients: \t{}\n' \
                             'Sequence number: \t{}'.format(1, 234563456345634563456345634563456, 3, 4, 5, 6,
                                                            7, 8, 9))
            self.get_user_input()

    def get_user_input(self):
        self.box.edit()
        try:
            text = self.box.gather().replace("\n", "")
        except:
            text = None
        if text is not None:
            self.update_result(text)

    def set_terminate(self, terminate):
        self.TERMINATE = terminate

    def update_window(self, name: str, text: str, clear: bool = True):
        if clear:
            self.windows[name].clear()
        self.windows[name].addstr(text)
        self.windows[name].refresh()

    def update_time(self, time_str: str):
        self.windows['time'].clear()
        self.windows['time'].addstr(self.TYPE, curses.A_BOLD | curses.A_UNDERLINE)
        self.update_window('time', '\t\t' + time_str, clear=False)

    def update_info(self, info: str):
        # info = self.process.report()
        self.update_window('info', info)

    def update_result(self, result: str):
        self.windows['input'].clear()
        self.update_window('result', result)

    def update_screen(self):
        for ele in cfg.window:
            y, x, h, w = cfg.window[ele]
            rectangle(self.screen, y, x, y + h, x + w)
            self.windows[ele] = curses.newwin(h - 1, w - 1, y + 1, x + 1)
        self.box = Textbox(self.windows['input'])
        self.screen.refresh()

    @staticmethod
    def close():
        curses.endwin()
        print("Window ended.")


def test():
    interface('SERVER')


if __name__ == '__main__':
    test()
