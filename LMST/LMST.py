import socket
import struct
import math
from queue import PriorityQueue
from threading import Thread, Lock, Event
import time
import sys
import logging
import random
import Application
import networkx as nx


class LMST:
    _dmax = 0.3
    nbr_finished_hello = 0
    nbr_finished_creation = 0
    nbr_finished_discovery = dict()
    liste_distance_min=[]
    Liste_arcs=[]
    Liste_arcs1=[]
    Liste_noeud=[]
    compt_nb_nodes=0
    X_00=None
    Y_00=None
    Liste_00=[]
    Liste_dist_0=[]
    Liste_toute_distance=[]
    Liste_toute_distance1=[]
    # nbr_listen_ttl = dict()
    nbr_finished_activity = dict()
    ps = dict()
    nodes_dead = []  # les noeuds morts, pour les oubliés dans l'etape discovery
    go = dict()
    lock_nfd = Lock()
    # lock_nlt = Lock()
    lock_nfa = Lock()
    lock_nodes_dead = Lock()
    
    

    def __init__(self, node_nbr, X, Y,voisin, nbr_nodes,G):
        # logging.basicConfig(filename='gaf.log', level=logging.INFO, format='%(asctime)s | %(message)s',
        # datefmt='%m/%d/%Y %I:%M:%S')

        self.nbr_nodes = nbr_nodes  # le nombres des noeuds existant dans graph
        self.node = node_nbr  # recuperer from G.node[node]
        self.G=G
        self.voisin=voisin
        self.X = X
        self.Y = Y
        self.dist_min=10
        self.have_0_comme_voisin=True
        self.liste_0_comme_voisin=True
        self.pq = PriorityQueue()
        self.noued_dist_min = None
        self.etat = "discovery"  # active - sleep - discovery - dead
        #self.etat = "active"
        self.battery_level = 5  # niveau batterie max en joule
        self.message = 'Node ' + str(node_nbr) + ' send you'
        self.messages = []  # contient les id des messages pour que chaque noeud redifuse le msg une seule fois
        # --------------hello phase attributes------------------
        self.hello_from_voisins_list = []  # pour calculer le nombre msg recu des voisin
        self.creation_from_voisins_list = []  # pour calculer le nombre msg recu des voisin apres le hello
        self.nodes_same_voisin_list = []
        self.liste_2_sauts = []
        self.liste_equiv = []
        self.voisin_envoye=[]
        self.voisin_coordo = []
        self.edges_in_MST = set()
        self.edges_in_MST1 = set()
        self.nodes_in_MST = set()
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
        self.lock = Lock()  # battery level
        self.lock_nblm = Lock()  # nbr_battery_level_messages lock
        self.sleep = Event()  #
        self.battery_big = Event()  # ma battery est inferieur aux moin a un noeud, pour que je go sleep
        # --------------------------------------------------------
        thread_job = Thread(target=self.job)  #
        thread_job.start()  # thread principal

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
        self.setup_logger('log4', r'C:\Users\HP\Documents\PYTHON CODECADEMY\PROJET\Application4\log4.log')
        self.log4 = logging.getLogger('log4')
        #self.setup_logger('log5', r'C:\Users\Samy\Desktop\Application1\log5.log')
        #self.log5 = logging.getLogger('log5')

    def job(self):
        # logging.info('Node ' + str(self.node) + ' Send message')
        self.bbb()
        self.log4.info('Info for log 2!')
        #self.log5.info("Je suis fel JOB")
        thread_hello = Thread(target=self.hello_process)  # lancer hello-phase thread
        thread_hello.start()
        while (True):
            LMST.lock_nodes_dead.acquire()
            for n in LMST.nodes_dead:
                if n in self.voisin:
                    self.voisin.remove(n)  # remove dead nodes from the same grid list
                if n in self.voisin_envoye:
                    self.voisin_envoye.remove(n)
            LMST.lock_nodes_dead.release()
            self.lock.acquire()
            if (self.etat == "sleep"):
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
        self.etat = "dead"  # le noeud passe a l'etat dead
        LMST.lock_nodes_dead.acquire()
        LMST.nodes_dead.append(self.node)  # remplir la liste des noeuds morts
        LMST.lock_nodes_dead.release()
        print('Node ' + str(self.node) + ' DEAD')
        self.log4.info('Node ' + str(self.node) + ' DEAD')
        return

    def hello_process(self):
        print("Node " + str(self.node) + " enter Hello Process")
        self.log4.info("Node " + str(self.node) + " enter Hello Process")
        thread_hello_phase_recv = Thread(target=self.hello_phase_recv)
        thread_hello_phase_recv.start()
        thread_send_hello_msg = Thread(target=self.send_hello_msg)
        thread_send_hello_msg.start()
        while (self.hello_phase_finished == False):  # boucle attendre jusqu'a le noeuds a recu tous les msg hello
            time.sleep(0.1)
        print('Node ' + str(self.node) + ' Finished Hello Process')
        self.log4.info('Node ' + str(self.node) + ' Finished Hello Process')
        self.log4.info("Le nbr finished: "+ str(LMST.nbr_finished_hello))
        if(LMST.nbr_finished_hello == self.nbr_nodes):
            LMST.Liste_toute_distance1.append((0,LMST.Liste_dist_0))
            
            LMST.Liste_toute_distance1.sort(key=lambda x:x[0])
            for i in LMST.Liste_toute_distance1:
                if i not in LMST.Liste_toute_distance:
                    LMST.Liste_toute_distance.append(i)
            #self.log4.info("liste :" + str(LMST.Liste_toute_distance1))
            #LMST.Liste_toute_distance=list(set(LMST.Liste_toute_distance1))
            #self.log4.info("liste :" + str(LMST.Liste_toute_distance))
        #self.log4.info('Node ' + str(LMST.nbr_finished_hello) + ' Finished Hello Process : '+ str(self.nbr_nodes))
        while not LMST.nbr_finished_hello == self.nbr_nodes:
            time.sleep(0.1)
        #self.creation_list()
        self.PrimsAlgorithm()
        #self.PrimsAlgorithm()

    def send_hello_msg(self):
        time.sleep(
            8)  # jusqu"a tous les noeuds are waiting to recv hello msgs (jusqu'a les threads recv hello sont tous entrain de resevé)
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

        # self.log4.info(msg_hello)
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

    def hello_phase_recv(self):  #
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
        #self.log4.info('Node ' + str(self.node) + ' Waiting to receive message in Hello Process')

        while True:
            try:
                if len(self.voisin) == 0:  # si le noeud n'a pas de voisin il ne recoit aucun hello msg
                    break
                if len(self.voisin)==1 and (self.voisin[
                                                   0] == 0):  # si le noeud a seulement le sink comme voisin il ne recoit aucun hello msg
                    dist=math.sqrt((self.X - (LMST.X_00)) ** 2 + (
                                    self.Y - (LMST.Y_00)) ** 2)
                    self.voisin_coordo.append((0,dist))
                    index_0=LMST.Liste_00.index(self.node)
                    LMST.Liste_dist_0.insert(index_0,(self.node,dist))
                    break
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
            #self.log4.info("je suis le noeud: "+str(self.node))
            if str(data.decode('utf-8').split(',')[0]) == "hello_phase":
                if int(data.decode('utf-8').split(',')[1]) in self.voisin:  # entendre que les voisins
                    
                    if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
                        
                        if (data.decode('utf-8').split(',')[2] not in self.messages):  # filtrer les messages deja recu
                            
                            #self.log4.info("je suis le noeud: "+ str(int(data.decode('utf-8').split(',')[1])))
                            self.messages.append(data.decode('utf-8').split(',')[2])  # ajouter msg id
                            self.hello_from_voisins_list.append(
                                data.decode('utf-8').split(',')[1])  # ajouter au compteur du msg hello
                            # self.log4.info(str(self.hello_from_voisins_list))
                            #self.log4.info("je suis before dist")
                            dist = math.sqrt((self.X - (float(data.decode('utf-8').split(',')[3]))) ** 2 + (
                                    self.Y - (float(data.decode('utf-8').split(',')[4]))) ** 2)
                            #self.log4.info(str(dist))
                            #   self.log5.info('Node ' + str(self.node) + ' Finished Hello Process')
                            #if (dist < LMST._dmax):
                            #    self.nodes_same_voisin_list.append(int(data.decode('utf-8').split(',')[1]))
                            self.voisin_coordo.append((int(data.decode('utf-8').split(',')[1]),dist))
                            
                            if(dist<self.dist_min and dist!=0.0):
                                self.dist_min=dist
                                self.noeud_dist_min= int(data.decode('utf-8').split(',')[1])
                            #self.log4.info('Je suis ici2')  
                            if 0 in self.voisin:  # sink eliminer comme voisin
                               if(self.have_0_comme_voisin):
                                dist=math.sqrt((self.X - (LMST.X_00)) ** 2 + (
                                    self.Y - (LMST.Y_00)) ** 2)
                                self.voisin_coordo.append((0,dist))
                                index_0=LMST.Liste_00.index(self.node)
                                LMST.Liste_dist_0.insert(index_0,(self.node,dist))
                                self.have_0_comme_voisin=False
                               if (len(self.hello_from_voisins_list) ==
                                        len(self.voisin) - 1):  # tester si tous les msgs hello sont arrivé
                                    break
                            if len(self.hello_from_voisins_list) == len(self.voisin):  # tester si tous les msgs hello sont arrivé
                                break
                            #self.log4.info(
                            #   'Node ' + str(self.node) + ' received: ')
                self.lock.acquire()
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()
        sock4.shutdown(socket.SHUT_RDWR)
        # sock4.close()
        LMST.nbr_finished_hello += 1  # assurer que tous les noeuds on recu hello messages
        #self.log4.info("Node " + str(self.node) + ": " + ",".join(str(n) for n in self.nodes_same_voisin_list))
        LMST.Liste_dist_0.sort(key=lambda x:x[0])
        #self.log4.info("Node 0: " + ",".join(str(n) for n in LMST.Liste_dist_0))# + "coord X: "+ str(LMST.X_00)+ "coord Y: "+ str(LMST.Y_00))
        self.voisin_coordo.sort(key=lambda x:x[0])
        LMST.Liste_toute_distance1.append((self.node,self.voisin_coordo))
        #self.log4.info("Node " + str(self.node) + ": " + ",".join(str(n) for n in self.voisin))
        self.log4.info("Node liste de coordonnees " + str(self.node) + ": " + ",".join(str(n) for n in self.voisin_coordo))
        LMST.liste_distance_min.append((self.node,self.noeud_dist_min))
        
        LMST.liste_distance_min.sort(key=lambda x:x[0])
        
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
            #self.lock.acquire()
            #self.battery_level -= self._energie_transmit
            #self.lock.release()
        except (socket.timeout, socket.error) as e:
            self.lock.release()
        finally:
            sock3.shutdown(socket.SHUT_RDWR)
            # sock3.close()

    def PrimsAlgorithm(self):
        self.log4.info("Je suis dans la methode PrimsAlgo")
        #pos=nx.get_node_attributes(self.G, 'pos')
        #pos1=pos[1]
        #self.log4.info("la liste general: " + str(LMST.Liste_toute_distance))
        
        for i in self.voisin_coordo:
            
            tuple_dist=i
            #self.log4.info("noeud : " +str(self.node)+ " tuple : "+ str(tuple_dist))
            tuple_exp=(tuple_dist[1],(self.node,tuple_dist[0]))
            self.pq.put(tuple_exp)
        
        #self.log4.info("Je suis dans la fin du for Prims Algo " + str(self.node)+ "la taille : "+ str(len(self.nodes_in_MST)))
        while len(self.nodes_in_MST) < self.nbr_nodes+1:
            
            #self.log4.info("Je suis dans le while Prims Algo "+ str(self.node))
            tuple_coor1= self.pq.get(self.pq)
            #dis, edge= self.pq.get(self.pq)
            #self.log4.info("Je suis dans le while Prims Algo2 "+ str(self.node)+ "Le tuple: "+ str(tuple_coor1[1]))
            edge=tuple_coor1[1]
            distt=tuple_coor1[0]
            if edge[0] not in self.nodes_in_MST:
                newNode = edge[0]
            elif edge[1] not in self.nodes_in_MST:
                newNode = edge[1]
            else:
                continue
            
            #self.log4.info("noeud new : " +str(newNode)+ " lllll: " +str(LMST.Liste_toute_distance[newNode]))
            for j in LMST.Liste_toute_distance[newNode][1]:
                tuple_dis=j
                #self.log4.info("noeud : " +str(newNode)+ " tuple1 : "+ str(tuple_dis))
                tuple_exp1=(tuple_dis[1],(newNode,tuple_dis[0]))
                #self.log4.info("Affiche tuple1 : "+ str(tuple_exp1))
                self.pq.put(tuple_exp1)
                
            self.edges_in_MST.add(edge)
            self.edges_in_MST1.add((edge,distt))
            self.nodes_in_MST.add(newNode)
            
        
        self.log4.info("noeud: "+str(self.node)+ " les arcs: "+ str(self.edges_in_MST))
        LMST.Liste_arcs= list(self.edges_in_MST.union(set(LMST.Liste_arcs)))
        LMST.Liste_arcs1= list(self.edges_in_MST1.union(set(LMST.Liste_arcs1)))
        self.log4.info("Liste d'arc: "+str(LMST.Liste_arcs))
        LMST.compt_nb_nodes+=1
        self.log4.info("Liste d'arc avec dist: "+str(LMST.Liste_arcs1))
        
        
        
        self.active()
        
        
        
    def active(self):
        
        #self.log4.info("je suis ici")
        
        #while not (LMST.compt_nb_nodes==self.nbr_nodes):
        #    self.active()
        
        #self.log4.info("je suis ici: "+ str(self.node)+ "le compt: "+ str(LMST.compt_nb_nodes)+ "le nombre de noeud: "+ str(self.nbr_nodes))
        
        #if(LMST.compt_nb_nodes==self.nbr_nodes):
            #self.log4.info("je suis ici")
        
        for i in LMST.Liste_arcs1:
                
            if(i[0][0]== self.node):
                    
                self.voisin_envoye.append(i[0][1])
                    #self.log4.info("je suis ici: "+ str(self.node)+ " le liste: "+ str(self.voisin_envoye))
            
            
        print("Node " + str(self.node) + " enter Active state")
        self.log4.info("Node " + str(self.node) + " enter Active state")
        self.etat = "active"
            #self.log4.info("je suis ici")
        thread_send = Thread(target=self.send)
        thread_recv = Thread(target=self.receiv)
        thread_recv.start()
        thread_send.start()
        self.sock1.shutdown(socket.SHUT_RDWR)
        self.sock2.shutdown(socket.SHUT_RDWR)
        
        self.lock.acquire()
        if (self.battery_level <= 0):
            self.lock.release()
            return
        self.lock.release()

        if self.etat == "dead":
            return
        self.active()
            
            
    def send(self):
        # print('send fucnction')
        multicast_group = ('224.3.29.71', 10000)

        # Bind to the server address
        self.sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the local network segment.
        ttl = struct.pack('b', 1)
        self.sock1.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        while (True):

            msg = "normal," + str(self.node) + ',' + str(random.randint(0, sys.maxsize)) + ',' + self.etat + ',' + str(
                self.battery_level) + ',' + self.message 
            try:
                time.sleep(2)
                self.lock.acquire()
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()

                sent = self.sock1.sendto(msg.encode(), multicast_group)

                self.lock.acquire()
                #self.battery_level -= self._energie_transmit

                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()


                #print('Node ' + str(self.node) + ' Send message')
            except (socket.timeout, socket.error) as e:
                if self.lock.locked(): self.lock.release()
                break

    def receiv(self):
        # print('receiv function')
        multicast_group = '224.3.29.71'  # pour listner
        server_address = ('', 10000)
        # Bind to the server address
        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock2.bind(server_address)
        # Tell the operating system to add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.sock2.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Receive/respond loop
        # begin as listner
        print('Node ' + str(self.node) + ' Waiting to receive message')
        while True:
            try:
                self.lock.acquire()
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()

                data, address = self.sock2.recvfrom(1024)  # receive instruction
                
                if str(data.decode('utf-8').split(',')[0]) == "normal":#entendre msg normaux
                    if int(data.decode('utf-8').split(',')[1]) in self.voisin_envoye:  # entendre que les voisins
                        if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
                            if (data.decode('utf-8').split(',')[2] not in self.messages):
                                self.messages.append(data.decode('utf-8').split(',')[2])
                                self.lock.acquire()
                                self.battery_level -= self._energie_recoit
                                if (self.battery_level <= 0):
                                    self.lock.release()
                                    break
                                self.lock.release()
                                #print(
                                #    'Node ' + str(self.node) + ' received: ' + data.decode('utf-8').split(',')[4] + ' : ' +
                                #    data.decode('utf-8').split(',')[5])

                                self.send_received_msg(data.decode('utf-8'))  # envoyer ce que on a recu
            except (socket.timeout, socket.error) as e:
                print("sortir")
                break
            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()
        #self.Active
        #    for j in i:
                
        #        self.log4.info("liste du tuple:" +str(j))
        #        tuple_exp=j
                
        #        self.pq.put(tuple_exp[1],(i,tuple_exp[0]))
        
        #for i in LMST.Liste_toute_distance:
        #    
        #    tuple_dist=i
        #    self.log4.info("tuple : " +str(i)+ "taille: "+ str(len(i[1])))
        #    for j in range(0,len(i[1])):
        #        
        #        self.log4.info("liste du tuple:" +str(i[1][j]))
        #        tuple_exp=i[1][j]
                
        #        self.pq.put(tuple_exp[1],(i[0],tuple_exp[0]))
        
            #self.log4.info("le tuple : " + str(tuple_dist) +" dans le noeud: "+str(self.node))
            #if(tuple_dist[1]<=self.dist_min):
            #    if(self.dist_min==tuple_dist[1]):
            #        if(max(self.node,self.noeud_dist_min)==max(self.node,tuple_dist[0])):
            #            if(min(self.node,self.noeud_dist_min)<min(self.node,tuple_dist[0])):
            #                self.noeud_dist_min=self.noeud_dist_min
            #            else:
            #                self.noeud_dist_min=tuple_dist[0]
            #        elif(max(self.node,self.noeud_dist_min)<max(self.node,tuple_dist[0])):
            #            self.noeud_dist_min=tuple_dist[0]
            #        else:
            #            self.noeud_dist_min=self.noeud_dist_min
            #    else:
            #        self.dist_min=tuple_dist[1]
            #        self.noeud_dist_min=tuple_dist[0]
        
        #self.log4.info(" ")
        #compteur+=1
        #self.log4.info("compteur: "+ str(compteur)+" distance du compt: "+str(self.dist_min)+ " le tuple de noeuds: "+str(self.node)+ " le tuple de noeuds2: "+str(self.noeud_dist_min))
        #self.log4.info("la liste general: " + str(LMST.liste_distance_min))
        
        """    for i in range(0,len(self.nodes_same_voisin_list)):
            if self.nodes_same_voisin_list[i] != self.node:
                self.log4.info("Je suis dans le for Prims Algo " + str(self.node))
                tuple_coor = self.voisin_coordo[self.nodes_same_voisin_list.index(self.nodes_same_voisin_list[i])]
                distence_u_v=math.sqrt((self.X-tuple_coor[0])**2+(self.Y-tuple_coor[1])**2)
                if(distence_u_v<self.dist_min):
                    self.noued_dist_min=self.nodes_same_voisin_list[i]
                tuple_exp=(distence_u_v,(self.node,i))
                compteur= compteur+1
                #self.log4.info("distance: "+str(tuple_exp[0])+ " le tuple de noeuds: "+str(tuple_exp[1][0])+ " le tuple de noeuds2: "+str(tuple_exp[1][1]))
                #self.log4.info("Je suis dans le for Prims Algo " + ",".join(tuple_exp))
                LMST.pq.put(tuple_exp)
                self.log4.info("compt: "+ str(compteur))
                if(compteur==len(self.nodes_same_voisin_list)-1):
                    self.log4.info("distance du compt: "+str(self.dist_min)+ " le tuple de noeuds: "+str(self.node)+ " le tuple de noeuds2: "+str(self.noeud_dist_min))
                    break
        while len(LMST.nodes_in_MST) < self.nbr_nodes:
            edge = LMST.pq.get(LMST.pq)
            self.log4.info("Je suis dans le while Prims Algo "+ str(self.node))
            self.log4.info("distance: "+str(edge[0])+ " le tuple de noeuds: "+str(edge[1][0])+ " le tuple de noeuds2: "+str(edge[1][1]))
            if edge[1][0] not in  LMST.nodes_in_MST:
                newNode = edge[1][0]
            elif edge[1][1] not in LMST.nodes_in_MST:
                newNode = edge[1][1]
            else:
                continue
            
            self.log4.info("Je suis dans le if d'apres while Prims Algo "+ str(self.node))
            
            posN = pos[newNode]
            for i in self.nodes_same_voisin_list[newNode]:
                if i != newNode:
                    posi=pos[i]
                    distence_u_v = math.sqrt((posN[0]-posi[0])**2+(posN[1]-posi[1])**2)
                    LMST.pq.put(distence_u_v,(newNode,i))
        LMST.edges_in_MST.add(tuple(sorted(edge)))
        LMST.nodes_in_MST.add(newNode)
        self.log4.info("la taille: "+ str(len(LMST.nodes_in_MST)))
    
        def creation_list(self):
        pass

        """
    def creation_list(self):
        print("Node " + str(self.node) + " enter creation Process")
        self.log4.info("Node " + str(self.node) + " enter creation Process")
        thread_creation_phase_recv = Thread(target=self.creation_phase_recv)
        thread_creation_phase_recv.start()
        thread_send_creation_msg = Thread(target=self.send_creation_msg)
        thread_send_creation_msg.start()
        while (self.creation_phase_finished == False):  # boucle attendre jusqu'a le noeuds a recu tous les msg hello
            time.sleep(0.1)
        print('Node ' + str(self.node) + ' Finished creation Process')
        self.log4.info('Node ' + str(self.node) + ' Finished creation Process')
        while not LMST.nbr_finished_creation == self.nbr_nodes:
            time.sleep(0.1)
        #self.list_equiv_calc()
        self.PrimsAlgorithm()

    def send_creation_msg(self):
        time.sleep(
            8)  # jusqu"a tous les noeuds are waiting to recv hello msgs (jusqu'a les threads recv hello sont tous entrain de resevé)
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
            random.randint(0, sys.maxsize)) + '#' + str(self.voisin) #+'#'+ str(self.voisin_coordo)
        # self.log4.info(msg_hello)
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

    def creation_phase_recv(self):  #
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
        # self.log4.info('Node ' + str(self.node) + ' Waiting to receive message in Hello Process')

        while True:
            try:
                if len(self.voisin) == 0:  # si le noeud n'a pas de voisin il ne recoit aucun hello msg
                    break
                if len(self.voisin) == 1 and (self.voisin[
                                                   0] == 0):  # si le noeud a seulement le sink comme voisin il ne recoit aucun hello msg
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
                if int(data.decode('utf-8').split('#')[1]) in self.voisin:  # entendre que les voisins
                    if (data.decode('utf-8').split('#')[1] != str(self.node)):  # filtrer moi meme(noeud)
                        if (data.decode('utf-8').split('#')[2] not in self.messages):  # filtrer les messages deja recu

                            self.messages.append(data.decode('utf-8').split('#')[2])  # ajouter msg id
                            # self.log4.info(str(self.nodes_same_voisin_list))

                            index_noeud_place = self.voisin.index(
                                int(data.decode('utf-8').split('#')[1]))
                            # self.log4.info("je suis rentre")

                            self.creation_from_voisins_list.append(
                                data.decode('utf-8').split('#')[1])  # ajouter au compteur du msg creation
                            # self.log4.info(str(self.creation_from_voisins_list))

                            # Fonction pour decoder notre liste
                            #lis1=data.decode('utf-8').split('#')[4]
                            #self.log4.info("la liste : "+ lis1)
                            lis = data.decode('utf-8').split('#')[3]
                            liss = lis.replace('[', '')

                            liss1 = liss.replace(']', '')
                            liss2 = liss1.replace(' ', '')
                            liss2 = liss2 + ','
                            # liss3=liss2.replace(',', '')

                            # self.log4.info('liste:' + liss2)
                            LIST1 = list(liss2)
                            # self.log4.info('liste:' + str(LIST1))
                            lissss = []

                            lissssss = ''
                            for i in range(0, len(LIST1)):
                                if (LIST1[i] == ','):
                                    lissss.append(int(lissssss))
                                    lissssss = ''
                                if (LIST1[i] != ','):
                                    lissssss = lissssss + LIST1[i]

                            # self.log4.info('Liste1: ' + str(lissss))
                            self.liste_2_sauts.insert(index_noeud_place, lissss)

                            if 0 in self.voisin:  # sink eliminer comme voisin
                                if(self.liste_0_comme_voisin):
                                    #self.log4.info("I'm here kraht la liste du 0: "+ str(LMST.Liste_00))
                                    self.liste_2_sauts.insert(0,LMST.Liste_00)
                                    self.liste_0_comme_voisin=False
                                if (len(self.creation_from_voisins_list) == len(
                                        self.voisin) - 1):  # tester si tous les msgs creation sont arrivé
                                    break
                            if len(self.creation_from_voisins_list) == len(
                                    self.voisin):  # tester si tous les msgs creation sont arrivé
                                break
                            self.log4.info(
                                'Node ' + str(self.node) + ' received: creation')
            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()
        sock7.shutdown(socket.SHUT_RDWR)
        # sock7.close()
        LMST.nbr_finished_creation += 1  # assurer que tous les noeuds on recu hello messages
        self.log4.info("Node " + str(self.node) +" la taille de la chaine " + str(len(self.liste_2_sauts))+" : " + ",".join(str(n) for n in self.liste_2_sauts))

        self.creation_phase_finished = True

        def send_received_msg_creation(self, data):
            # print('sendreceived fuction')
            multicast_group = ('224.3.29.71', 10000)
            sock6 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Bind to the server address
            sock6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Set the time-to-live for messages to 1 so they do not go past the
            #  local network segment.
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
    
    



