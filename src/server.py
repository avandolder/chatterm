#!/usr/bin/python3
"""
"""

import socket
import sys
import threading
from typing import Dict, List

HOST, PORT = "localhost", 9999
MESSAGE_SIZE = 1024


class Server:
    """
    """
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connections = {} # type: Dict[int, socket.socket]
        self.connection_count = 0
        self.threads = [] # type: List[threading.Thread]
        self.mutex = threading.RLock()

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()

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

    def handle_client(self, *conn_handle: int) -> None:
        conn = self.connections[conn_handle[0]]
        while True:
            cmd = conn.recv(MESSAGE_SIZE).decode("utf-8")
            if not cmd:
                # Connection is closed
                break
            else:
                print(f"received {cmd} from {conn_handle[0]}")
                self.tell_all(f"{conn_handle[0]}: {cmd}")

        # Remove connection
        self.mutex.acquire()
        conn.close()
        self.connections.pop(conn_handle[0], None)
        self.mutex.release()
        print(f"closed {conn_handle[0]}")
        self.tell_all(f"{conn_handle[0]} left chat")

    def tell_all(self, msg: str) -> None:
        """Send msg to all clients."""
        self.mutex.acquire()
        for conn in self.connections.values():
            conn.sendall(msg.encode())
        self.mutex.release()


def main(args: List[str]) -> int:
    server = Server(HOST, PORT)
    server.run()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
