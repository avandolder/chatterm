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
        self.sock.connect((self.host, self.port))
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
            # No data has been received, but the connection is still active.
            return ""

    def close(self) -> None:
        self.sock.close()


class ChatWindow:
    """
    """

    man = {
        "server": "host port - join server",
        "leave": "- leave current server",
        "quit": "- quit chat",
        "clear": "- clear chat window",
        "nick": "nickname - set nickname",
        "msg": "name message - send direct message to name",
        "mkch": "channel - make new channel",
        "join": "channel - join channel",
        "list": "- list channels",
        "names": "[channels] - list users, all or just on channels",
        "help": "[commands] - print help for commands",
    }

    def __init__(self) -> None:
        self.conn: Optional[Connection] = None
        self.line = 0
        self.running = False
        self.inp: List[str] = []
        self.inp_cur = 0
        self.nick = ""
        self.history: List[str] = []
        self.history_ptr = 0
        self.commands: Dict[str, Callable[..., None]] = {
            "server": self.join_server,
            "leave": self.leave_server,
            "quit": self.quit,
            "clear": self.clear,
            "nick": self.set_nickname,
            "msg": self.direct_message,
            "mkch": self.make_channel,
            "join": self.join_channel,
            "list": self.list_channels,
            "names": self.list_users,
            "help": self.help,
        }

    def tell(self, msg: str) -> None:
        lines = 1 + len(msg)//curses.COLS
        if self.line == curses.LINES - 1:
            for i in range(lines):
                self.scr.scroll()
            self.line -= lines 
        self.scr.addstr(self.line, 0, msg)
        self.line += lines

    def handle_input(self) -> None:
        c = self.scr.getch()
        if c == curses.ERR:
            return
        elif c == ord("\n"):
            self.history.append("".join(self.inp))
            self.history_ptr = len(self.history)
            self.handle_command()
            self.inp.clear()
        elif ((c == curses.KEY_BACKSPACE or c == ord("\b"))
                and len(self.inp) > 0 and self.inp_cur > 0):
            self.inp_cur -= 1
            self.inp.pop(self.inp_cur)
        elif c == curses.KEY_DC and self.inp_cur < len(self.inp):
            self.inp.pop(self.inp_cur)
        elif c == curses.KEY_LEFT:
            self.inp_cur -= 1
        elif c == curses.KEY_RIGHT:
            self.inp_cur += 1 
        elif c == curses.KEY_UP and self.history:
            self.history_ptr = max(0, self.history_ptr - 1)
            self.inp = list(self.history[self.history_ptr])
            self.inp_cur = len(self.inp)
        elif c == curses.KEY_DOWN and self.history:
            self.history_ptr = min(len(self.history), self.history_ptr + 1)
            if self.history_ptr == len(self.history):
                self.inp = []
                self.inp_cur = 0
            else:
                self.inp = list(self.history[self.history_ptr])
                self.inp_cur = len(self.inp)
        elif chr(c) in string.printable and self.inp_cur < curses.COLS - 2:
            self.inp.insert(self.inp_cur, chr(c))
            self.inp_cur += 1
            
        self.scr.move(curses.LINES - 1, 0)
        self.scr.clrtoeol()
        self.scr.addstr(f">{''.join(self.inp)}")
        self.inp_cur = max(0, min(self.inp_cur, len(self.inp), curses.COLS - 2))

    def quit(self) -> None:
        if self.conn is not None:
            self.leave_server()
        self.running = False

    def clear(self) -> None:
        self.line = 0
        self.scr.clear()
        self.scr.addch(curses.LINES - 1, 0, ">")

    def set_nickname(self, nick: str) -> None:
        self.nick = nick
        if self.conn is not None:
            self.conn.send(f"/nick {nick}")
        else:
            self.tell(f"Nickname set to {self.nick}")

    def join_server(self, host: str, port: str) -> None:
        if self.conn is not None:
            self.tell("Must leave server before joining another")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.conn = Connection(sock, host, int(port))
        self.conn.connect()
        self.tell("joined chat")
        if self.nick:
            self.conn.send(f"/nick {self.nick}")

    def leave_server(self) -> None:
        if self.conn is None:
            self.tell("Must join server before being able to leave")
            return

        self.conn.close()
        self.conn = None
        self.tell("Left chat")

    def direct_message(self, nick: str, *msg: str) -> None:
        if self.conn is None:
            self.tell("Join server before MSGing")
            return
        msg_str = " ".join(msg)
        self.conn.send(f"/msg {nick} {msg_str}")

    def make_channel(self, chan: str) -> None:
        if self.conn is None:
            self.tell("Join server before making channels")
            return
        self.conn.send(f"/mkch {chan}")

    def join_channel(self, chan: str) -> None:
        if self.conn is None:
            self.tell("Join server before joining channel")
            return
        self.conn.send(f"/join {chan}")

    def list_channels(self) -> None:
        if self.conn is None:
            self.tell("Must join server before LISTing")
            return
        self.conn.send("/list")

    def list_users(self, *chans: str) -> None:
        if self.conn is None:
            self.tell("Must join server before /NAMES")
            return
        self.conn.send(f"/names {' '.join(chans)}")

    def help(self, *cmds: str) -> None:
        if not cmds:
            cmds = self.man.keys() # type: ignore
        for cmd in cmds:
            if cmd in self.man:
                self.tell(f"/{cmd} {self.man[cmd]}")
            else:
                self.tell(f"No such command: {cmd}")

    def handle_command(self) -> None:
        if self.inp and self.inp[0] == "/":
            # Any line beginning with / is a command.
            cmd = "".join(self.inp).strip().split()
            cmd_name = cmd[0][1:].lower()
            self.tell(f"/{cmd_name.upper()} {' '.join(cmd[1:])}")
            if cmd_name in self.commands: 
                self.commands[cmd_name](*cmd[1:])
            else:
                self.tell(f"unknown command: {cmd_name}")
        elif self.conn is not None:
            self.conn.send("".join(self.inp))
        else:
            self.tell("Must join server to chat")

    def run(self, scr) -> int:
        self.running = True
        self.scr = scr

        # Set up the chat window
        scr.addch(curses.LINES - 1, 0, ">")
        scr.move(0, 0)
        scr.setscrreg(0, curses.LINES - 2)
        scr.scrollok(True)
        scr.nodelay(True) # Make input reading non-blocking.

        self.tell("ChatTerm v0.1")
        self.tell("use /help for help")

        while self.running:
            self.handle_input()

            if self.conn is not None:
                rcvd = self.conn.receive()
                if rcvd is None:
                    self.leave_server()
                else:
                    # Split the received data by line, filtering out empty lines
                    for rcv in filter(lambda x: x, rcvd.split("\n")):
                        if rcv.startswith("/nick"):
                            # Setting nickname failed, go back to previous one
                            self.tell("Nickname already taken")
                            self.nick = rcv.split()[1]
                        else:
                            self.tell(rcv)

            scr.move(curses.LINES - 1, self.inp_cur + 1)
            scr.refresh()

        if self.conn is not None:
            self.conn.close()
            self.conn = None
        return 0


def main(args: List[str]) -> int:
    chat = ChatWindow()
    return curses.wrapper(chat.run)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
