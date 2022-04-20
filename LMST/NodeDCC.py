import socket
import struct
import math
from threading import Thread, Lock, Event
import time
import sys
import logging
import random

class NodeDCC:
    _dmax=0.3
    nbr_finished_hello = 0
    nbr_finished_creation = 0
    nbr_finished_discovery = dict()
    #nbr_listen_ttl = dict()
    nbr_finished_activity = dict()
    nodes_dead = []#les noeuds morts, pour les oubliés dans l'etape discovery
    go = dict()
    lock_nfd = Lock()
    #lock_nlt = Lock()
    lock_nfa = Lock()
    lock_nodes_dead = Lock()
    def __init__(self, node_nbr,X,Y, nbr_nodes):
        #logging.basicConfig(filename='gaf.log', level=logging.INFO, format='%(asctime)s | %(message)s',
                            #datefmt='%m/%d/%Y %I:%M:%S')
        self.log5.info("Je suis init NodeDCC")
        self.nbr_nodes = nbr_nodes #le nombres des noeuds existant dans graph
        self.node = node_nbr  # recuperer from G.node[node]
        self.X=X
        self.Y=Y 
        self.etat = "discovery"  # active - sleep - discovery - dead
        self.battery_level = 5  # niveau batterie max en joule
        self.message = 'Node ' + str(node_nbr) + ' send you'
        self.messages = []  # contient les id des messages pour que chaque noeud redifuse le msg une seule fois
        # --------------hello phase attributes------------------
        self.hello_from_voisins_list = []  # pour calculer le nombre msg recu des voisin
        self.creation_from_voisins_list = [] # pour calculer le nombre msg recu des voisin apres le hello
        self.nodes_same_voisin_list = []
        self.liste_2_sauts = []
        self.liste_equiv = []
        self.hello_phase_finished = False
        self.creation_phase_finished = False
        # --------------------------------------------------------
        self.sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket de send
        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket de recv
        # --------------------------------------------------------
        self._energie_sommeil = 0.0000001
        self._energie_transmit = 0.000411  # pour d=5
        self._energie_recoit = 0.000246  # pour d=5
        self._energie_ecoute = 0.000246  # pour d=5
        # --------------------------------------------------------
        self.lock = Lock()#battery level
        self.lock_nblm = Lock()#nbr_battery_level_messages lock
        self.sleep = Event()#
        self.battery_big = Event()#ma battery est inferieur aux moin a un noeud, pour que je go sleep
        # --------------------------------------------------------
        thread_job = Thread(target=self.job)#
        thread_job.start()#thread principal

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

    def bbb(self):
        self.setup_logger('log2', r'C:\Users\Samy\Desktop\Application1\log2.log')
        self.log2 = logging.getLogger('log2')
        self.setup_logger('log3', r'C:\Users\Samy\Desktop\Application1\log3.log')
        self.log3 = logging.getLogger('log3')
        self.setup_logger('log5', r'C:\Users\Samy\Desktop\Application1\log5.log')
        self.log5 = logging.getLogger('log5')

    def job(self):
        #logging.info('Node ' + str(self.node) + ' Send message')
        self.bbb()
        self.log2.info('Info for log 2!')
        thread_hello = Thread(target=self.hello_process)#lancer hello-phase thread
        thread_hello.start()
        while (True):
            NodeDCC.lock_nodes_dead.acquire()
            for n in NodeDCC.nodes_dead:
                if n in self.self.nodes_same_voisin_list:
                    self.nodes_same_voisin_list.remove(n)#remove dead nodes from the same grid list
            NodeDCC.lock_nodes_dead.release()
            self.lock.acquire()
            if(self.etat == "sleep"):
                self.battery_level -= self._energie_sommeil
                self.lock.release()
            else:
                self.battery_level -= self._energie_ecoute
                self.lock.release()
            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()
            time.sleep(2)
        self.sock1.shutdown(socket.SHUT_RDWR)
        self.sock2.shutdown(socket.SHUT_RDWR)
        self.etat = "dead"#le noeud passe a l'etat dead
        NodeDCC.lock_nodes_dead.acquire()
        NodeDCC.nodes_dead.append(self.node)#remplir la liste des noeuds morts
        NodeDCC.lock_nodes_dead.release()
        print('Node ' + str(self.node) + ' DEAD')
        self.log2.info('Node ' + str(self.node) + ' DEAD')
        return

    def hello_process(self):
        print("Node " + str(self.node) + " enter Hello Process")
        self.log2.info("Node " + str(self.node) + " enter Hello Process")
        thread_hello_phase_recv = Thread(target=self.hello_phase_recv)
        thread_hello_phase_recv.start()
        thread_send_hello_msg = Thread(target=self.send_hello_msg)
        thread_send_hello_msg.start()
        while (self.hello_phase_finished == False):  # boucle attendre jusqu'a le noeuds a recu tous les msg hello
            time.sleep(0.1)
        print('Node ' + str(self.node) + ' Finished Hello Process')
        self.log2.info('Node ' + str(self.node) + ' Finished Hello Process')
        while not NodeDCC.nbr_finished_hello == self.nbr_nodes:
            time.sleep(0.1)
        self.creation_list()

    def send_hello_msg(self):
        time.sleep(8)  # jusqu"a tous les noeuds are waiting to recv hello msgs (jusqu'a les threads recv hello sont tous entrain de resevé)
        multicast_group = ('224.3.29.71', 10000)
        sock5 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the server address
        sock5.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl = struct.pack('b', 1)
        sock5.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.lock.acquire()
        
        msg_hello = "hello_phase, " + str(self.node) + ',' + str(
            random.randint(0, sys.maxsize)) + ',' + str(self.X) + ',' + str(self.Y)
        
        #self.log2.info(msg_hello)
        self.lock.release()
        try:
            time.sleep(
                self.node / 4)  # instruction obligatoire car les il y a des pertes de messages sinon, perte des msg hello doit etre 0%
            sent = sock5.sendto(msg_hello.encode(), multicast_group)


        except (socket.timeout, socket.error) as e:
            print('timed out, no more responses')
        finally:
            self.lock.acquire()
            self.battery_level -= self._energie_transmit
            self.lock.release()
            sock5.shutdown(socket.SHUT_RDWR)
            # sock5.close()

    def hello_phase_recv(self):#
        # self.send_hello_msg()#fait appel au 'send hello msg' function
        multicast_group = '224.3.29.71'  # pour listner
        server_address = ('', 10000)
        # Bind to the server address
        sock4 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock4.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock4.bind(server_address)
        # Tell the operating system to add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock4.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Receive/respond loop
        # begin as listner
        #self.log2.info('Node ' + str(self.node) + ' Waiting to receive message in Hello Process')

        while True:
            try:
                
                self.lock.acquire()
                if (self.battery_level <= 0):  # si la batterie <= 0 sortir de la boucle du recoit
                    self.lock.release()
                    break
                self.lock.release()
                
                data, address = sock4.recvfrom(1024)  # receive instruction
                
                self.lock.acquire()
                self.battery_level -= self._energie_recoit  # tarif de recevoir pour batterie
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()
                
            except (socket.timeout,
                    socket.error) as e:  # if socket closed de la part du job thread, sortir de la boucle du recoit
                break
            
            if str(data.decode('utf-8').split(',')[0]) == "hello_phase":
                 #if int(data.decode('utf-8').split(',')[1]) in self.voisins:  # entendre que les voisins
                if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
                    
                    if (data.decode('utf-8').split(',')[2] not in self.messages):  # filtrer les messages deja recu
                        
                        self.messages.append(data.decode('utf-8').split(',')[2])  # ajouter msg id
                        self.hello_from_voisins_list.append(
                            data.decode('utf-8').split(',')[1])  # ajouter au compteur du msg hello
                            #self.log2.info(str(self.hello_from_voisins_list))       
                        #self.log2.info("je suis before dist")
                        dist= math.sqrt((self.X-(float(data.decode('utf-8').split(',')[3])))**2+(self.Y-(float(data.decode('utf-8').split(',')[4])))**2)
                        #self.log2.info(str(dist))
                        if(dist<NodeDCC._dmax):
                            self.nodes_same_voisin_list.append(int(data.decode('utf-8').split(',')[1]))

                        #if 0 in self.:  # sink eliminer comme voisin
                        #    if (len(self.hello_from_voisins_list) == 
                        #            self.nbr_nodes - 1:  # tester si tous les msgs hello sont arrivé
                        #        break
                        if len(self.hello_from_voisins_list) == self.nbr_nodes:  # tester si tous les msgs hello sont arrivé
                            break
                        self.log2.info(
                            'Node ' + str(self.node) + ' received: ' )
            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()
        sock4.shutdown(socket.SHUT_RDWR)
        # sock4.close()
        NodeDCC.nbr_finished_hello += 1 #assurer que tous les noeuds on recu hello messages
        self.log2.info("Node " + str(self.node) + ": " + ",".join(str(n) for n in self.nodes_same_voisin_list))

        self.hello_phase_finished = True

    def send_received_msg(self, data):
        # print('sendreceived fuction')
        multicast_group = ('224.3.29.71', 10000)
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
        finally:
            sock3.shutdown(socket.SHUT_RDWR)
            # sock3.close()

    def creation_list(self):
        print("Node " + str(self.node) + " enter creation Process")
        self.log2.info("Node " + str(self.node) + " enter creation Process")
        thread_creation_phase_recv = Thread(target=self.creation_phase_recv)
        thread_creation_phase_recv.start()
        thread_send_creation_msg = Thread(target=self.send_creation_msg)
        thread_send_creation_msg.start()
        while (self.creation_phase_finished == False):  # boucle attendre jusqu'a le noeuds a recu tous les msg hello
            time.sleep(0.1)
        print('Node ' + str(self.node) + ' Finished creation Process')
        self.log2.info('Node ' + str(self.node) + ' Finished creation Process')
        while not NodeDCC.nbr_finished_creation == self.nbr_nodes:
            time.sleep(0.1)
        self.list_equiv_calc()

    def send_creation_msg(self):
        time.sleep(8)  # jusqu"a tous les noeuds are waiting to recv hello msgs (jusqu'a les threads recv hello sont tous entrain de resevé)
        multicast_group = ('224.3.29.71', 10000)
        sock8 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the server address
        sock8.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl = struct.pack('b', 1)
        sock8.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.lock.acquire()
        
        msg_creation = "creation_phase# " + str(self.node) + '#' + str(
            random.randint(0, sys.maxsize)) + '#' + str(self.nodes_same_voisin_list)
        #self.log2.info(msg_hello)
        self.lock.release()
        try:
            time.sleep(
                self.node / 4)  # instruction obligatoire car les il y a des pertes de messages sinon, perte des msg hello doit etre 0%
            sent = sock8.sendto(msg_creation.encode(), multicast_group)


        except (socket.timeout, socket.error) as e:
            print('timed out, no more responses')
        finally:
            self.lock.acquire()
            self.battery_level -= self._energie_transmit
            self.lock.release()
            sock8.shutdown(socket.SHUT_RDWR)
            # sock8.close()

    def creation_phase_recv(self):#
        # self.send_hello_msg()#fait appel au 'send hello msg' function
        multicast_group = '224.3.29.71'  # pour listner
        server_address = ('', 10000)
        # Bind to the server address
        sock7 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock7.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock7.bind(server_address)
        # Tell the operating system to add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock7.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Receive/respond loop
        # begin as listner
        #self.log2.info('Node ' + str(self.node) + ' Waiting to receive message in Hello Process')
        
        
        while True:
            try:
                if len(self.nodes_same_voisin_list) == 1:  # si le noeud n'a que sois meme comme voisin il ne recoit aucun creation msg
                    break
                self.lock.acquire()
                if (self.battery_level <= 0):  # si la batterie <= 0 sortir de la boucle du recoit
                    self.lock.release()
                    break
                self.lock.release()

                data, address = sock7.recvfrom(1024)  # receive instruction

                self.lock.acquire()
                self.battery_level -= self._energie_recoit  # tarif de recevoir pour batterie
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()

            except (socket.timeout,
                    socket.error) as e:  # if socket closed de la part du job thread, sortir de la boucle du recoit
                break
            
            if str(data.decode('utf-8').split('#')[0]) == "creation_phase":
                if int(data.decode('utf-8').split('#')[1]) in self.nodes_same_voisin_list:  # entendre que les voisins
                    if (data.decode('utf-8').split('#')[1] != str(self.node)):  # filtrer moi meme(noeud)
                        if (data.decode('utf-8').split('#')[2] not in self.messages):  # filtrer les messages deja recu
                            
                            self.messages.append(data.decode('utf-8').split('#')[2])  # ajouter msg id
                            #self.log2.info(str(self.nodes_same_voisin_list))
                            
                            index_noeud_place=self.nodes_same_voisin_list.index(int(data.decode('utf-8').split('#')[1]))
                            #self.log2.info("je suis rentre")
                            
                            self.creation_from_voisins_list.append(data.decode('utf-8').split('#')[1])  # ajouter au compteur du msg creation
                            #self.log2.info(str(self.creation_from_voisins_list))       
                            
                            #Fonction pour decoder notre liste 
                            
                            lis=data.decode('utf-8').split('#')[3]
                            liss=lis.replace('[', '')
                            
                            liss1=liss.replace(']', '')
                            liss2=liss1.replace(' ', '')
                            liss2= liss2+','
                            #liss3=liss2.replace(',', '')
                            
                            #self.log2.info('liste:' + liss2)
                            LIST1=list(liss2)
                            #self.log2.info('liste:' + str(LIST1))
                            lissss=[]
                            
                            lissssss=''
                            for i in range(0,len(LIST1)):
                                if(LIST1[i]==','):
                                    lissss.append(int(lissssss))
                                    lissssss=''
                                if(LIST1[i]!=','):
                                    lissssss = lissssss + LIST1[i]
                            
                            #self.log2.info('Liste1: ' + str(lissss))
                            self.liste_2_sauts.insert(index_noeud_place,lissss)
                         
                            if 0 in self.nodes_same_voisin_list:  # sink eliminer comme voisin
                               if (len(self.creation_from_voisins_list) == len(
                                        self.nodes_same_voisin_list) - 1):  # tester si tous les msgs creation sont arrivé
                                    break
                            if len(self.creation_from_voisins_list) == len(
                                    self.nodes_same_voisin_list):  # tester si tous les msgs creation sont arrivé
                               break
                            self.log2.info(
                                'Node ' + str(self.node) + ' received: creation' )
            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()
        sock7.shutdown(socket.SHUT_RDWR)
        # sock7.close()
        NodeDCC.nbr_finished_creation += 1 #assurer que tous les noeuds on recu hello messages
        self.log2.info("Node " + str(self.node) + ": " + ",".join(str(n) for n in self.liste_2_sauts))

        self.creation_phase_finished = True

    def send_received_msg_creation(self, data):
        # print('sendreceived fuction')
        multicast_group = ('224.3.29.71', 10000)
        sock6 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the server address
        sock6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl = struct.pack('b', 1)
        sock6.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        try:

            sent = sock6.sendto(data.encode(), multicast_group)
            self.lock.acquire()
            self.battery_level -= self._energie_transmit
            self.lock.release()
        except (socket.timeout, socket.error) as e:
            self.lock.release()
        finally:
            sock6.shutdown(socket.SHUT_RDWR)
            # sock6.close()
            
    def list_equiv_calc(self):
        
        self.log2.info("Node " + str(self.node) + " enter liste equiv Process")
        
        liste_temp = self.nodes_same_voisin_list
        #self.log2.info(str(self.nodes_same_voisin_list))
        test_list1=[]
        test_list2=[]

        for i in self.nodes_same_voisin_list:
            self.log3.info("la liste des 2 saut" + str(self.liste_2_sauts[i]))
            #self.log2.info("la liste des voisins" + str(self.liste_temp))
            self.log3.info("la liste des voisins" + str(liste_temp))
            #self.log2.info(str("interieur du for externe"))



            if len(self.liste_2_sauts)==len(self.nodes_same_voisin_list):
                self.log3.info("IT'S GOOOOD")
                temp=[]
                temp=self.liste_2_sauts.intersection(self.nodes_same_voisin_list)
                if len(temp)==len(self.liste_2_sauts):
                    self.log3.info("ME HEEEREEEEE")
                    self.liset_equiv.append(
                        self.nodes_same_voisin_list[i])

        """    length=len(self.liste_temp)
            if len(self.self.liste_2_sauts[i])==length:
                self.log2.info("deuxieme if comparaison de longeur")
                test_list1=self.liset_2_sauts[i].sort()
                self.log2.info("liste 2 saut sort" + str(test_list1))
                test_list2=self.liste_temp.sort()
                self.log2.info("liste tempo" + str(test_list2))
                if test_list1 == test_list2:
                    self.log2.info(str("if test 1 == test 2"))
                    self.liset_equiv.append(
                                self.nodes_same_voisin_list[i])"""

        
        
        self.log2.info("Node " + str(self.node) + ": " + ",".join(str(n) for n in self.liste_equiv))
        
        self.discovry()
        
    
    #def discovery(self):