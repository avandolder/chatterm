#!/usr/bin/python3
"""
"""

import socket
import sys
import threading
from typing import List

HOST, PORT = "localhost", 9999


class Server:
    def __init__(self, host: int, port: int) -> None:
        self.host = host
        self.port = port
        self.connections = []
        self.threads = []
        self.mutex = threading.RLock()

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()

            while True:
                conn, addr = s.accept()
                self.mutex.acquire()
                self.connections.append(conn)
                self.threads.append(
                    threading.Thread(target=self.handle_client, args=(self, conn))
                self.mutex.release()

    def handle_client(self, conn: socket.socket) -> None:
        with conn:
            nick = ""
            user = ""
            while True:
                cmd = conn.recv(1024)
                if cmd.startswith(""):
                    pass


def main(args: List[str]) -> int:
    server = Server(HOST, PORT)
    server.run()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
