import socket
import struct
from threading import Thread, Lock
import time
import sys
import logging
import random


class Node:


    def __init__(self, node_nbr, grid_nbr, voisins):
        #logging.basicConfig(filename='general.log', level=logging.INFO, format='%(asctime)s | %(message)s',
                            #datefmt='%m/%d/%Y %I:%M:%S')
        # --------------------------------------------------------
        self.node = node_nbr  # recuperer from G.node[node]
        self.grid_nbr = grid_nbr  # recuperer from G.node[node]['grid_nbr']
        self.voisins = voisins  # recuperer from G.adj[i]
        self.etat = "active"  # active - sleep - discovery - dead
        self.battery_level = 5  # niveau batterie max en joule
        self.message = 'Node ' + str(node_nbr) + ' send you'
        self.messages = []  # contient les id des messages pour que chaque noeud redifuse le msg une seule fois
        # --------------------------------------------------------
        self.sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket de send
        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket de recv
        # sock3 : socket sendRecvedMesg
        # --------------------------------------------------------
        self._energie_sommeil = 0.0000001
        self._energie_transmit = 0.000411  # pour d=5
        self._energie_recoit = 0.000246  # pour d=5
        self._energie_ecoute = 0.000246  # pour d=5
        # --------------------------------------------------------
        self.lock = Lock()

        thread_job = Thread(target=self.job)  #
        thread_job.start()  # thread principal
        #---------------------

    def setup_logger(self, logger_name, log_file, level=logging.INFO):
        l = logging.getLogger(logger_name)
        formatter = logging.Formatter('%(asctime)s : %(message)s')
        fileHandler = logging.FileHandler(log_file, mode='w')
        fileHandler.setFormatter(formatter)
        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(formatter)

        l.setLevel(level)
        l.addHandler(fileHandler)
        l.addHandler(streamHandler)

    def aaa(self):
        self.setup_logger('log1', r'C:\Users\HP\Documents\PYTHON CODECADEMY\PROJET\Application4\log1.log')
        self.log1 = logging.getLogger('log1')




    def job(self):
        self.aaa()
        self.log1.info('Info for log 1!')
        print('Info for log 1!')
        thread_send = Thread(target=self.send)
        thread_recv = Thread(target=self.receiv)
        thread_recv.start()
        thread_send.start()
        while (True):
            self.lock.acquire()
            self.battery_level -= self._energie_ecoute
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()
            time.sleep(2)
        self.sock1.shutdown(socket.SHUT_RDWR)
        self.sock2.shutdown(socket.SHUT_RDWR)
        self.sock1.close()
        self.sock2.close()
        self.etat = "dead"
        self.log1.info('Node ' + str(self.node) + ' DEAD')

    def send_received_msg(self, data):
        #('sendreceived fuction')
        multicast_group = ('224.3.29.75', 10000)
        sock3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the server address
        sock3.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl = struct.pack('b', 1)
        sock3.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        try:

            sent = sock3.sendto(data.encode(), multicast_group)
            self.lock.acquire()
            self.battery_level -= self._energie_transmit
            self.lock.release()
        except (socket.timeout, socket.error) as e:
            self.lock.release()
            print('timed out, no more responses')
        finally:
            sock3.shutdown(socket.SHUT_RDWR)
            sock3.close()

    def send(self):
        #print('send fucnction')
        multicast_group = ('224.3.29.75', 10000)

        # Bind to the server address
        self.sock1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the local network segment.
        ttl = struct.pack('b', 1)
        self.sock1.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        while (True):
            self.lock.acquire()
            msg = str(self.node) + ',' + str(random.randint(0, sys.maxsize)) + ',' + self.etat + ',' + str(
                self.battery_level) + ',' + self.message + ',' + str(self.grid_nbr)
            self.lock.release()
            try:
                self.lock.acquire()
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()

                sent = self.sock1.sendto(msg.encode(), multicast_group)

                self.lock.acquire()
                self.battery_level -= self._energie_transmit
                self.battery_level -= self._energie_transmit
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()

                self.log1.info('Node ' + str(self.node) + ' Send message')
            except (socket.timeout, socket.error) as e:
                self.lock.release()
                break
            time.sleep(2)

    def receiv(self):
        #print('receiv function')
        multicast_group = '224.3.29.75'  # pour listner
        server_address = ('', 10000)
        # Bind to the server address
        self.sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock2.bind(server_address)
        # Tell the operating system to add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.sock2.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Receive/respond loop
        # begin as listner
        self.log1.info('Node ' + str(self.node) + ' Waiting to receive message')
        thread_traitement_receiv = []
        index = 0
        while True:
            try:
                self.lock.acquire()
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()
                data, address = self.sock2.recvfrom(1024)  # receive instruction

                self.lock.acquire()
                self.battery_level -= self._energie_recoit
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()
                if int(data.decode('utf-8').split(',')[0]) in self.voisins:  # entendre que les voisins
                    if (data.decode('utf-8').split(',')[0] != str(self.node)):  # filtrer moi meme(noeud)
                        if (data.decode('utf-8').split(',')[1] not in self.messages):#filtrer msg deja recu
                            self.messages.append(data.decode('utf-8').split(',')[1])
                            self.lock.acquire()
                            self.battery_level -= self._energie_recoit
                            if (self.battery_level <= 0):
                                self.lock.release()
                                break
                            self.lock.release()
                            self.log1.info(
                                'Node ' + str(self.node) + ' received: ' + data.decode('utf-8').split(',')[3] + ' : ' +
                                data.decode('utf-8').split(',')[4])

                            self.send_received_msg(data.decode('utf-8'))  # envoyer ce que on a recu

            except (socket.timeout, socket.error) as e:
                break
            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()

