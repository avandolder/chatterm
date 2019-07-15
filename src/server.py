#!/usr/bin/python3
"""
"""

import socket
import sys
import threading
from typing import Dict, List, Union, cast

HOST, PORT = "localhost", 9999
MESSAGE_SIZE = 1024


class Server:
    """
    """
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connections: Dict[int, socket.socket] = {}
        self.connection_count = 0
        self.threads: List[threading.Thread] = []
        self.mutex = threading.RLock()
        self.nicks: Dict[Union[str, int], Union[str, int]] = {}

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(10)

            while True:
                conn, addr = s.accept()
                print(f"connnected {self.connection_count}")
                self.mutex.acquire()
                self.connections[self.connection_count] = conn
                self.threads.append(threading.Thread(
                    target=self.handle_client, args=[self.connection_count]))
                self.connection_count += 1
                self.threads[-1].start()
                self.mutex.release()
                self.tell_all(f"{self.connection_count - 1} joined chat")

    def handle_client(self, *conn_handle: int) -> None:
        conn = self.connections[conn_handle[0]]
        nick = str(conn_handle[0])
        while True:
            cmd = conn.recv(MESSAGE_SIZE).decode("utf-8")
            print(f"received '{cmd}' from {conn_handle[0]} aka {nick}")
            if not cmd:
                # Connection is closed
                break
            elif cmd.startswith("/nick"):
                nick = self.set_nick(conn_handle[0], cmd.split()[1])
            elif cmd.startswith("/msg"):
                nick, *msg = cmd.split()[1:]
                if nick in self.nicks:
                    conn = self.connections[cast(int, self.nicks[nick])]
                    self.tell(conn, f"*{nick}*: {' '.join(msg)}")
            else:
                self.tell_all(f"{nick}: {cmd}")

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

    def tell(self, conn: socket.socket, msg: str) -> None:
        """Send msg to specified client."""
        self.mutex.acquire()
        conn.sendall(msg.encode())
        self.mutex.release()

    def set_nick(self, handle: int, nick: str) -> str:
        prev_nick = str(handle)
        self.mutex.acquire()
        if handle in self.nicks:
            prev_nick = cast(str, self.nicks[handle])
        if nick in self.nicks and self.nicks[nick] != handle:
            # This nickname is being used by a different client.
            self.mutex.release()
            return prev_nick
        self.nicks[nick] = handle
        self.nicks[handle] = nick
        self.mutex.release()
        self.tell_all(f"{prev_nick} is now known as {nick}")
        return nick


def main(args: List[str]) -> int:
    server = Server(HOST, PORT)
    server.run()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
