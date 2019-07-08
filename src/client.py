#!/bin/python3
"""
"""

import socket
import sys
import time
from typing import List

HOST, PORT = "localhost", 9999


class Client:
    def __init__(self, sock: socket.socket, host: str, port: int) -> None:
        self.sock = sock
        self.host = host
        self.port = port

    def connect(self) -> None:
        self.sock.connect((HOST, PORT))

    def send(self, data: str) -> None:
        self.sock.sendall(bytes(data + "\n", "utf-8"))

    def receive(self, n: int = 1024) -> str:
        return str(self.sock.recv(n), "utf-8")


def main(args: List[str]) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        client = Client(sock, HOST, PORT)
        client.connect()

        data = " ".join(args[1:])
        client.send(" ".join(args[1:]))
        print(f"Sent:\t\t{data}")
        print(f"Received:\t{client.receive()}")

        time.sleep(5)
        client.send(" ".join(args[1:]))
        print(f"Sent:\t\t{data}")
        print(f"Received:\t{client.receive()}")

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
