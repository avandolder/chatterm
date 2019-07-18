#!/usr/bin/python3
"""
"""

import socket
import sys
import threading
from typing import Dict, List, Set, Union, cast

MESSAGE_SIZE = 1024


class Server:
    """
    """
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connections: Dict[int, socket.socket] = {}
        self.threads: List[threading.Thread] = []
        self.channels: Dict[str, Set[int]] = {"default": set()}
        self.mutex = threading.RLock()
        self.nicks: Dict[Union[str, int], Union[str, int]] = {}

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(10)

            while True:
                conn, addr = s.accept()
                conn_handle = len(self.connections)
                print(f"connnected {conn_handle}")
                self.mutex.acquire()
                self.connections[conn_handle] = conn
                self.threads.append(threading.Thread(
                    target=self.handle_client, args=[conn_handle]))
                self.threads[-1].start()
                self.channels["default"].add(conn_handle)
                self.mutex.release()
                self.tell_all(f"{conn_handle} joined chat")

    def handle_client(self, *conn_handle: int) -> None:
        conn = self.connections[conn_handle[0]]
        nick = str(conn_handle[0])
        chan = "default"
        while True:
            cmd = conn.recv(MESSAGE_SIZE).decode("utf-8")
            print(f"received '{cmd}' from {conn_handle[0]} aka {nick}")
            if not cmd:
                # Connection is closed
                break
            elif cmd.startswith("/nick"):
                nick = self.set_nick(conn_handle[0], nick, cmd.split()[1])
            elif cmd.startswith("/msg"):
                nick, *msg = cmd.split()[1:]
                if nick in self.nicks:
                    conn = self.connections[cast(int, self.nicks[nick])]
                    self.tell(conn, f"*{nick}*: {' '.join(msg)}")
            elif cmd.startswith("/mkchannel"):
                new_chan = cmd.split()[1]
                if new_chan not in self.channels:
                    self.channels[new_chan] = set()
                    self.tell_all(f"Channel {new_chan} created")
                else:
                    self.tell(conn, f"Channel {new_chan} already exists")
            elif cmd.startswith("/channel"):
                new_chan = cmd.split()[1]
                if new_chan not in self.channels:
                    self.tell(conn, f"Channel {new_chan} doesn't exist")
                else:
                    self.mutex.acquire()
                    self.channels[chan].remove(conn_handle[0])
                    self.channels[new_chan].add(conn_handle[0])
                    self.mutex.release()
                    self.tell_channel(chan, f"{nick} left {chan}")
                    self.tell_channel(new_chan, f"{nick} joined {new_chan}")
                    chan = new_chan
            else:
                self.tell_channel(chan, f"{nick}: {cmd}")

        # Remove connection
        print(f"closed {conn_handle[0]}")
        self.tell_all(f"{nick} left chat")
        self.mutex.acquire()
        conn.close()
        self.connections.pop(conn_handle[0], None)
        self.nicks.pop(nick, None)
        self.nicks.pop(conn_handle[0], None)
        self.mutex.release()

    def tell_all(self, msg: str) -> None:
        """Send msg to all clients."""
        self.mutex.acquire()
        for conn in self.connections.values():
            conn.sendall(msg.encode())
        self.mutex.release()

    def tell_channel(self, chan: str, msg: str) -> None:
        """Send msg to eveyone on chan."""
        self.mutex.acquire()
        for conn in self.channels[chan]:
            self.connections[conn].sendall(msg.encode())
        self.mutex.release()

    def tell(self, conn: socket.socket, msg: str) -> None:
        """Send msg to specified client."""
        self.mutex.acquire()
        conn.sendall(msg.encode())
        self.mutex.release()

    def set_nick(self, handle: int, prev_nick: str, nick: str) -> str:
        self.mutex.acquire()
        if handle in self.nicks:
            prev_nick = cast(str, self.nicks[handle])
        if nick in self.nicks and self.nicks[nick] != handle:
            # This nickname is being used by a different client.
            self.tell(self.connections[handle], f"/nick {prev_nick}")
            self.mutex.release()
            return prev_nick
        self.nicks[nick] = handle
        self.nicks[handle] = nick
        self.mutex.release()
        self.tell_all(f"{prev_nick} is now known as {nick}")
        return nick


def main(args: List[str]) -> int:
    try:
        server = Server(args[1], int(args[2]))
    except (IndexError, ValueError) as e:
        print(f"usage: {args[0]} host port")
        return 1
    server.run()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
