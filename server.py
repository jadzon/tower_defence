import socket
import threading

HOST = '127.0.0.1'
PORT = 8080

clients = []
threads = []

def handle_client(conn):
    while True:
        print("waiting for message")
        raw_msg = conn.recv(1024)
        msg = raw_msg.decode()
        print(msg)
        broadcast_to_all(raw_msg,conn)

def broadcast_to_all(raw_msg, from_conn):
    for conn in clients:
        if conn == from_conn:
            continue
        conn.send(raw_msg)

def start_server():

    server = socket.create_server((HOST,PORT))

    while True:
        print("waiting for client")
        conn , add = server.accept()
        clients.append(conn)
        print("client connected: ", add)
        print("starting new thread")
        thd = threading.Thread(target=handle_client, args=(conn,))
        thd.start()
        threads.append(thd)

    

if __name__ == "__main__":
    print("server start 1.")
    start_server()
    
