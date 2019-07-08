#!/bin/python3
"""
"""

import socketserver
import sys
from typing import List

HOST, PORT = "localhost", 9999


class RequestHandler(socketserver.StreamRequestHandler):
    """
    The TCP request handler for the IRC server.
    """

    def handle(self) -> None:
        for line in self.rfile:
            self.data = line.strip()
            print(f"{self.client_address[0]} wrote: {self.data}")
            self.wfile.write(self.data.upper())


def main(args: List[str]) -> int:
    with socketserver.ThreadingTCPServer((HOST, PORT), RequestHandler) as server:
        server.serve_forever()

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
