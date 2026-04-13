from __future__ import annotations
import socket
import threading


class Client:
    def __init__(self,host,port):
        self.host = host
        self.port = port
        self.threads = []
        self._connect()

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host,self.port))
        self.server = s

    def _receive_msg(self):
        while True:
            print(self.server.recv(1024).decode())
    
    def send_message(self, msg: str):
            raw_msg = msg
            self.server.send(raw_msg.encode())
    
    def start(self):
        thd = threading.Thread(target=self._receive_msg)
        thd.start()
        self.threads.append(thd)

if __name__ == "__main__":
    _HOST = '127.0.0.1'
    _PORT = 8080
    c = Client(_HOST,_PORT)
    c.start()