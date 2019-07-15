#!/bin/python3
"""
"""

import curses
import socket
import sys
import time
import threading
from typing import Any, List

HOST, PORT = "localhost", 9999
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

    def receive(self, n: int = MESSAGE_SIZE) -> str:
        try:
            return str(self.sock.recv(n), "utf-8")
        except BlockingIOError as e:
            return ""


class ChatWindow:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn
        self.line = 0

    def tell(self, scr: Any, msg: str) -> None:
        if self.line == curses.LINES - 1:
            scr.scroll()
            self.line -= 1
        scr.addstr(self.line, 0, msg)
        self.line += 1

    def run(self, scr: Any) -> None:
        scr.nodelay(True) # Make input reading non-blocking.
        self.conn.connect()

        scr.addch(curses.LINES - 1, 0, ">")
        scr.move(0, 0)
        scr.setscrreg(0, curses.LINES - 2)
        scr.scrollok(True)
        cmd = ""

        while True:
            c = scr.getch()

            if c != curses.ERR:
                if c == ord("\n"):
                    if cmd.strip() == "/quit":
                        break
                    self.conn.send(cmd)
                    cmd = ""
                elif c == curses.KEY_BACKSPACE:
                    cmd = cmd[:-1]
                elif 0 <= c <= 255 and chr(c).isascii():
                    cmd += chr(c)
                scr.move(curses.LINES - 1, 1)
                scr.clrtoeol()
                scr.addstr(cmd)

            rcvd = filter(lambda x: x, self.conn.receive().split("\n"))
            for rcv in rcvd:
                self.tell(scr, f"{rcv}")

            scr.move(curses.LINES - 1, len(cmd) + 1)
            scr.refresh()

        self.conn.send("end")


def main(args: List[str]) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        conn = Connection(sock, HOST, PORT)
        chat = ChatWindow(conn)
        curses.wrapper(chat.run)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
