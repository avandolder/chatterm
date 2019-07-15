#!/bin/python3
"""
"""

import curses
import socket
import string
import sys
import threading
from typing import Callable, Dict, List, Optional

MESSAGE_SIZE = 1024


class Connection:
    def __init__(self, sock: socket.socket, host: str, port: int) -> None:
        self.sock = sock
        self.host = host
        self.port = port

    def connect(self) -> None:
        self.sock.connect((HOST, PORT))
        self.sock.setblocking(False)

    def send(self, data: str) -> None:
        self.sock.sendall(bytes(data, "utf-8"))

    def receive(self, n: int = MESSAGE_SIZE) -> Optional[str]:
        try:
            data = str(self.sock.recv(n), "utf-8")
            if data == "":
                # If data is empty, and no exception was raised, then the
                # socket is closed.
                return None
            return data
        except BlockingIOError as e:
            return ""

    def close(self) -> None:
        self.sock.close()


class ChatWindow:
    """
    """

    def __init__(self) -> None:
        self.conn: Connection = None
        self.line = 0
        self.running = False
        self.connected = False
        self.inp: List[str] = []
        self.inp_cur = 0
        self.nick = ""
        self.commands: Dict[str, Callable[..., None]] = {
            "join": self.join_server,
            "leave": self.leave_server,
            "quit": self.quit,
            "clear": self.clear,
            "nick": self.set_nickname,
        }

    def tell(self, msg: str) -> None:
        if self.line == curses.LINES - 1:
            self.scr.scroll()
            self.line -= 1
        self.scr.addstr(self.line, 0, msg)
        self.line += 1

    def handle_input(self) -> None:
        c = self.scr.getch()
        if c == curses.ERR:
            return
        elif c == ord("\n"):
            self.handle_command()
            self.inp.clear()
        elif c == curses.KEY_BACKSPACE and self.inp:
            self.inp_cur -= 1
            self.inp.pop(self.inp_cur)
        elif c == curses.KEY_DC and self.inp_cur < len(self.inp):
            self.inp.pop(self.inp_cur)
        elif c == curses.KEY_LEFT:
            self.inp_cur -= 1
        elif c == curses.KEY_RIGHT:
            self.inp_cur += 1 
        elif chr(c) in string.printable:
            self.inp.insert(self.inp_cur, chr(c))
            self.inp_cur += 1
            
        self.scr.move(curses.LINES - 1, 1)
        self.scr.clrtoeol()
        self.scr.addstr("".join(self.inp))
        self.inp_cur = max(0, min(self.inp_cur, len(self.inp)))

    def quit(self) -> None:
        if self.connected:
            self.leave_server()
        self.running = False

    def clear(self) -> None:
        self.line = 0
        self.scr.clear()
        self.scr.addch(curses.LINES - 1, 0, ">")

    def set_nickname(self, nick: str) -> None:
        self.nick = nick
        if self.connected:
            self.conn.send(f"/nick {nick}")
        else:
            self.tell(f"Nickname set to {self.nick}")

    def join_server(self, host: str, port: str) -> None:
        if self.connected:
            self.tell("Must leave server before joining another")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.conn = Connection(sock, host, int(port))
        self.conn.connect()
        self.connected = True
        self.tell("joined chat")
        if self.nick:
            self.conn.send(f"/nick {self.nick}")

    def leave_server(self) -> None:
        if not self.connected:
            self.tell("Must join server before being able to leave")
            return

        self.conn.close()
        self.connected = False
        self.tell("Left chat")

    def handle_command(self) -> None:
        if self.inp and self.inp[0] == "/":
            # Any line beginning with / is a command.
            cmd = "".join(self.inp).strip().split()
            cmd_name = cmd[0][1:].lower()
            if cmd_name in self.commands: 
                self.commands[cmd_name](*cmd[1:])
            else:
                self.tell(f"unknown command: {cmd_name}")
        elif self.connected:
            self.conn.send("".join(self.inp))

    def run(self, scr) -> None:
        self.running = True
        self.scr = scr

        # Set up the chat window
        scr.addch(curses.LINES - 1, 0, ">")
        scr.move(0, 0)
        scr.setscrreg(0, curses.LINES - 2)
        scr.scrollok(True)
        scr.nodelay(True) # Make input reading non-blocking.

        while self.running:
            self.handle_input()

            if self.connected:
                rcvd = self.conn.receive()
                if rcvd is None:
                    self.leave_server()
                else:
                    for rcv in filter(lambda x: x, self.conn.receive().split("\n")):
                        self.tell(f"{rcv}")

            scr.move(curses.LINES - 1, self.inp_cur + 1)
            scr.refresh()

        if self.connected:
            self.conn.close()
        self.connected = False


def main(args: List[str]) -> int:
    chat = ChatWindow()
    curses.wrapper(chat.run)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
