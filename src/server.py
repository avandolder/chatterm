#!/usr/bin/python3
"""
"""

import socket
import sys
import threading
from typing import Dict, List, Set, Union, cast

MESSAGE_SIZE = 1024


class ClientInfo:
    def __init__(self, handle: int, conn: socket.socket, nick: str, chan: str):
        self.handle = handle
        self.conn = conn
        self.nick = nick
        self.chan = chan


class Server:
    """
    """
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connections: Dict[int, socket.socket] = {}
        self.connection_count = 0
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
                conn_handle = self.connection_count
                self.connection_count += 1
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
        client = ClientInfo(
            conn_handle[0],
            self.connections[conn_handle[0]],
            str(conn_handle[0]),
            "default",
        )

        while True:
            cmd = client.conn.recv(MESSAGE_SIZE).decode("utf-8")
            print(f"received '{cmd}' from {client.handle} aka {client.nick}")
            if not cmd:
                # Connection is closed
                break
            elif cmd[0] == "/":
                self.handle_command(client, cmd.split())
            else:
                self.tell_channel(client.chan, f"{client.nick}: {cmd}")

        # Remove connection
        print(f"{client.handle} aka {client.nick} connection closed")
        self.tell_all(f"{client.nick} left chat")
        self.mutex.acquire()
        client.conn.close()
        self.connections.pop(client.handle, None)
        self.nicks.pop(client.nick, None)
        self.nicks.pop(client.handle, None)
        self.mutex.release()

    def handle_command(self, client: ClientInfo, cmd: List[str]) -> None:
        if cmd[0] == "/nick":
            self.set_nick(client, cmd[1])
        elif cmd[0] == "/msg":
            nick = cmd[1]
            if nick in self.nicks:
                conn = self.connections[cast(int, self.nicks[nick])]
                msg_str = " ".join(cmd[2:])
                self.tell(conn, f"*{client.nick}* {msg_str}")
                self.tell(client.conn, f"-> *{nick}* {msg_str}")

        elif cmd[0] == "/mkch":
            new_chan = cmd[1]
            if new_chan not in self.channels:
                self.channels[new_chan] = set()
                self.tell_all(f"Channel {new_chan} created")
            else:
                self.tell(client.conn, f"Channel {new_chan} already exists")

        elif cmd[0] == "/join":
            if cmd[1] not in self.channels:
                self.tell(client.conn, f"Channel {new_chan} doesn't exist")
            else:
                self.mutex.acquire()
                self.channels[client.chan].remove(client.handle)
                self.channels[cmd[1]].add(client.handle)
                self.mutex.release()
                self.tell_channel(
                    client.chan, f"{client.nick} left {client.chan}")
                self.tell_channel(cmd[1], f"{client.nick} joined {cmd[1]}")
                client.chan = cmd[1]

        elif cmd[0] == "/list":
            self.list_channels(client.conn)
        elif cmd[0] == "/names":
            self.list_users(client.conn, cmd[1:])

    def tell_all(self, msg: str) -> None:
        """Send msg to all clients."""
        self.mutex.acquire()
        for conn in self.connections.values():
            conn.sendall((msg + "\n").encode())
        self.mutex.release()

    def tell_channel(self, chan: str, msg: str) -> None:
        """Send msg to everyone on chan."""
        self.mutex.acquire()
        for conn in self.channels[chan]:
            self.connections[conn].sendall((msg + "\n").encode())
        self.mutex.release()

    def tell(self, conn: socket.socket, msg: str) -> None:
        """Send msg to specified client."""
        self.mutex.acquire()
        conn.sendall((msg + "\n").encode())
        self.mutex.release()

    def set_nick(self, client: ClientInfo, nick: str) -> None:
        self.mutex.acquire()
        if nick in self.nicks and self.nicks[nick] != client.handle:
            # Inform client this nickname is being used by a different client.
            self.mutex.release()
            self.tell(self.connections[client.handle], f"/nick {client.nick}")
        else:
            self.nicks[nick] = client.handle
            self.nicks[client.handle] = nick
            self.nicks.pop(client.nick, None)
            self.mutex.release()
            self.tell_all(f"{client.nick} is now known as {nick}")
            client.nick = nick

    def list_channels(self, conn: socket.socket) -> None:
        self.tell(conn, "*** Channel\tUsers")
        for chan in self.channels:
            self.tell(conn, f"*** {chan}\t{len(self.channels[chan])}")

    def list_users(self, conn: socket.socket, chans: List[str]) -> None:
        if chans:
            for chan in chans:
                if chan not in self.channels:
                    self.tell(conn, f"{chan} channel doesn't exist")
                    continue

                handles = self.channels[chan]
                names = " ".join([
                    cast(str, self.nicks[h])
                    for h in handles
                    if h in self.nicks
                ])
                self.tell(conn, f"{chan}: {names}")
                
        else:
            names = " ".join([
                cast(str, nick)
                for nick in self.nicks.keys()
                if type(nick) is str
            ])
            self.tell(conn, f"all users: {names}")


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
