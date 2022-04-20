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
    nbr_listen_ttl = dict()
    nbr_finished_activity = dict()
    nodes_dead = []#les noeuds morts, pour les oubliés dans l'etape discovery
    go = dict()
    lock_nfd = Lock()
    lock_nlt = Lock()
    lock_nfa = Lock()
    lock_nodes_dead = Lock()
    def __init__(self, node_nbr,X,Y, nbr_nodes):
        #logging.basicConfig(filename='gaf.log', level=logging.INFO, format='%(asctime)s | %(message)s',
                            #datefmt='%m/%d/%Y %I:%M:%S')
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
        self._TS = 10
        self._TA = 10
        self.ttl_max = 57
        self.nbr_battery_level_messages = 0#nombres des messages battery level recu des noeuds du meme grid
        # self.ttl
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
        self.setup_logger('log2', r'C:\Users\HP\Documents\PYTHON CODECADEMY\PROJET\Application\log2.log')
        self.log2 = logging.getLogger('log2')

    def job(self):
        #logging.info('Node ' + str(self.node) + ' Send message')
        self.bbb()
        self.log2.info('Info for log 2!')
        thread_hello = Thread(target=self.hello_process)#lancer hello-phase thread
        thread_hello.start()
        while (True):
            NodeDCC.lock_nodes_dead.acquire()
            for n in NodeDCC.nodes_dead:
                if n in self.nodes_same_voisin_list:
                    self.nodes_same_voisin_list.remove(n)#remove dead nodes from the same grid list
                if n in self.liste_equiv:
                    self.liste_equiv.remove(n)
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
        self.etat = "dead" #le noeud passe a l'etat dead
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
                        #self.log2.info(
                        #    'Node ' + str(self.node) + ' received: ' )
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
            #self.battery_level -= self._energie_transmit
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
                if len(self.nodes_same_voisin_list) == 0:  # si le noeud n'a que sois meme comme voisin il ne recoit aucun creation msg
                    break
                self.lock.acquire()
                if (self.battery_level <= 0):  # si la batterie <= 0 sortir de la boucle du recoit
                    self.lock.release()
                    break
                self.lock.release()

                data, address = sock7.recvfrom(1024)  # receive instruction

                self.lock.acquire()
                #self.battery_level -= self._energie_recoit  # tarif de recevoir pour batterie
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()

            except (socket.timeout,
                    socket.error) as e:  # if socket closed de la part du job thread, sortir de la boucle du recoit
                break
            
            if str(data.decode('utf-8').split('#')[0]) == "creation_phase":
                if int(data.decode('utf-8').split('#')[1]) in self.nodes_same_voisin_list:  # entendre que les voisins
                    #print("je suis ici")
                    if(data.decode('utf-8').split('#')[1] == str(self.node) and len(self.nodes_same_voisin_list)==1): 
                        self.creation_from_voisins_list.append(data.decode('utf-8').split('#')[1])
                        self.liste_2_sauts.append(self.node)
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
                            #self.log2.info(
                            #    'Node ' + str(self.node) + ' received: creation' )
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
            #self.battery_level -= self._energie_transmit
            self.lock.release()
        except (socket.timeout, socket.error) as e:
            self.lock.release()
        finally:
            sock6.shutdown(socket.SHUT_RDWR)
            # sock6.close()
            
    def list_equiv_calc(self):
        
        #self.log2.info("Node " + str(self.node) + " enter liste equiv Process")
        
        liste_temp = self.nodes_same_voisin_list
        #self.log2.info("liste voisin "+str(self.nodes_same_voisin_list))
        i=0
        for i in range(0,len(self.nodes_same_voisin_list)):
            #self.log2.info(" enter for et affiche la liste de saut[i]" + str(self.liste_2_sauts[i]))
            
            #self.log2.info("taille de la liste voisine: "+ str(self.liste_2_sauts[i])+" taille: "+ str(len(self.liste_2_sauts[i]))+ " taille du saut: "
            #+ str(liste_temp)+"taille: " + str(len(liste_temp)))
            
            if len(self.liste_2_sauts[i])==len(liste_temp):
                
                #test_list1.sort()
                #test_list2.sort()
                intersection_set = set.intersection(set(liste_temp), set(self.liste_2_sauts[i]))
                intersection_list = list(intersection_set)
                #self.log2.info("taille de la liste intersection : "+ str(intersection_list) +" liste voisine"+ str(liste_temp) + " voisin  "+ str(self.liste_2_sauts[i]))
                if len(intersection_list) == len(liste_temp):
                    #self.log2.info(" i did it youpiii ")
                    
                    self.liste_equiv.append(self.nodes_same_voisin_list[i])
                    #self.log2.info("lISTE equiv : " +str(self.node) + str(self.liste_equiv))
        #self.log2.info("fin")
        self.log2.info("Node liste equiv " + str(self.node) + " : " + ",".join(str(n) for n in self.liste_equiv))
        
        self.discovery()
        
    
    def discovery(self):
    
        #self.log2.info("Node " + str(self.node) + " enter Discovery state")
    
        if(len(self.liste_equiv)==1):
            self.log2.info("Node " + str(self.node) + " Mon energie: " + str(self.battery_level))
            if(self.etat == "dead"):
                return
            self.active()

        
        else:
        
            NodeDCC.lock_nfd.acquire()
        
            if (str(self.liste_equiv) in NodeDCC.nbr_finished_discovery):#incrementer ce dictionnaire statique pour le decrementer aprés pour assurer que tous les noeuds ont recu le niveau de batterie
                NodeDCC.nbr_finished_discovery[str(self.liste_equiv)] += 1
            else:#sinon initialiser nv numero grille comme key et mettre valeur a 1
                NodeDCC.nbr_finished_discovery[str(self.liste_equiv)] = 1
            NodeDCC.lock_nfd.release()
        
        

            NodeDCC.lock_nlt.acquire()
        
            if (str(self.liste_equiv) in NodeDCC.nbr_listen_ttl):
                NodeDCC.nbr_listen_ttl[str(self.liste_equiv)] += 1#dictionnaire pour savoir si j'ai recu ttl/2 de tous les noeuds du meme grille
            else:
                NodeDCC.nbr_listen_ttl[str(self.liste_equiv)] = 1
            NodeDCC.lock_nlt.release()
        
            #print("Node " + str(self.node) + " enter Discovery state")
            self.log2.info("Node " + str(self.node) + " enter Discovery state")
            self.etat = "discovery"
            self.sleep.clear()# enlever event sleep
            self.battery_big.clear()# enlever event ma batterie petite
            self.lock.acquire()
            battery_level_t = self.battery_level# le niveau de batterie que j'envoie et je compare reste constant
            self.lock.release()
            print("Node " + str(self.node) + " : " + str(battery_level_t))
            self.log2.info("Node " + str(self.node) + " : " + str(battery_level_t))
        
            sock9 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#envoyé
            sock10 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#receiv battery level

            thread_recv_discovery = Thread(target=self.receiv_ttl, args=[sock10, 2, battery_level_t])#2 veut dire recevoir niveau batterie et non ttl
            thread_recv_discovery.start()#lancer l'ecoute sur batterie level
           
            self.lock.acquire()
            #self.battery_level -= self._energie_transmit
            self.lock.release()

            #self.log2.info("node: " +str(self.node)+" battry je termine receiv discovery" + str(self.battery_level))
        
            self.lock.acquire()
            for n in range(0,len(self.liste_equiv)):#maybeee

                self.battery_level -= self._energie_recoit  
            self.lock.release()
        
            #self.log2.info("node recoit: " +str(self.node)+" battry je termine receiv discovery" + str(self.battery_level))
        
            while self.etat != "dead" and not self.battery_big.is_set():#je sort si battery petit
                self.sendTTL(sock9, 2, battery_level_t)#2 signifie que j'envoie niveau batterie(socket crée une seule fois)
                self.lock_nblm.acquire()
            
                if self.nbr_battery_level_messages == len(self.liste_equiv)-1:
                    self.lock_nblm.release()
                    break#je sort si je suis chef
                self.lock_nblm.release()
                time.sleep(2)
        
            #self.log2.info("node recoit: NNNNN")
        
            self.lock_nblm.acquire()
            self.nbr_battery_level_messages = 0
            self.lock_nblm.release()
            sock10.shutdown(socket.SHUT_RDWR)
            sock9.shutdown(socket.SHUT_RDWR)

            NodeDCC.go[str(self.liste_equiv)] = False#pour que tous entre active et sleep au meme temps
            if self.battery_big.is_set():
                self.before_sleeep(sock9, battery_level_t)#aller vers before sleep
                return#sortir de la fonction discovery
#----------------partie chef--------------------------------------------------------
            self.lock.acquire()
            self.ttl = (self.battery_level * self.ttl_max) / 5  # set ttl value maybe
            self.lock.release()
            self._TA = self.ttl / 2

            NodeDCC.lock_nfd.acquire()
            NodeDCC.nbr_finished_discovery[str(self.liste_equiv)] -= 1 #annoncé j'ai terminé discovery aux autres noeds(lzm ge3 ykemlou bach nroho lsend ttl
            NodeDCC.lock_nfd.release()
            while self.etat != "dead":
                self.sendTTL(sock9, 2, battery_level_t)#envoyé niveau batterie du futur chef pour assuré la reception de tous les noeuds
                NodeDCC.lock_nfd.acquire()
                if NodeDCC.nbr_finished_discovery.get(str(self.liste_equiv)) == 0:#si tous on fini discovery
                    NodeDCC.lock_nfd.release()
                    break
                NodeDCC.lock_nfd.release()
                time.sleep(2)

#tous on sorti de l'etape dicovery
            NodeDCC.lock_nlt.acquire()
            NodeDCC.nbr_listen_ttl[str(self.liste_equiv)] -= 1#le chef est pret pour envoyer ttl
            NodeDCC.lock_nlt.release()

            self.lock.acquire()
            #self.battery_level -= self._energie_transmit
            self.lock.release()

            while self.etat != "dead":
                self.sendTTL(sock9, 1, 0)#le chef envoie ttl
                NodeDCC.lock_nlt.acquire()
                if NodeDCC.nbr_listen_ttl.get(str(self.liste_equiv)) == 0:#le dernier noeud before sleep qui passe a l'ecoute??
                    NodeDCC.lock_nlt.release()
                    break
                NodeDCC.lock_nlt.release()
                time.sleep(2)
            NodeDCC.go[str(self.liste_equiv)] = True #tous les noeud on recu ttl je passe a l'active
            if(self.etat == "dead"):
                return
            self.active()


    def sendTTL(self, sock9, state, battery_level):
        # create msg
        if state == 1:
            self.lock.acquire()
            msgDC = "discovery_send_ttl," + str(self.node) + ',' + str(random.randint(0, sys.maxsize)) + ',' + str(
                self._TA)

            self.lock.release()
        elif state == 2:
            self.lock.acquire()
            msgDC = "discovery_send_battery_level," + str(self.node) + ',' + str(random.randint(0, sys.maxsize)) + ',' + str(battery_level)  # case 6
            self.lock.release()

        if state == 1:
            multicast_group = ('224.3.29.72', 10000)#pour la charge séparé les reseaux
        else:
            multicast_group = ('224.3.29.71', 10000)

        sock9 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the server address
        sock9.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl1 = struct.pack('b', 1)
        sock9.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl1)

        try:
            print("Node " + str(self.node) + " send TTL" + str(state))
            sent = sock9.sendto(msgDC.encode(), multicast_group)

        except (socket.timeout, socket.error) as e:
            self.lock.release()
        finally:
            sock9.shutdown(socket.SHUT_RDWR)
            # sock6.close()

        

    def receiv_ttl(self, sock10, state, battery_level_t):
        #self.log2.info('receiv function')
        if state == 1:
            multicast_group = '224.3.29.72'  # pour listner
        else:
            multicast_group = '224.3.29.71'  # pour listner
        server_address = ('', 10000)
        # Bind to the server address
        sock10.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock10.bind(server_address)
        # Tell the operating system to add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock10.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # Receive loop
        if state == 1:
            self.log2.info('Node ' + str(self.node) + ' Waiting to receive TTL')
        if state == 2:
            self.log2.info('Node ' + str(self.node) + ' Waiting to receive Battery Level')
        data=""
        thread_traitement_reciv_ttl = []
        index = 0#create thread a chaque recu
        self.loop=True
        while self.loop:
            try:
                self.lock.acquire()
                if (self.battery_level <= 0):
                    self.lock.release()
                    break
                self.lock.release()
                
                data, address = sock10.recvfrom(1024)  # receive instruction
                thread_traitement_reciv_ttl.append(Thread(target=self.traitement_reciv_ttl, args=[data, state, battery_level_t]))
                thread_traitement_reciv_ttl[index].start()
                index+=1
                #self.log2.info("index: "+ str(index))

            except (socket.timeout, socket.error) as e:
                break

    def traitement_reciv_ttl(self, data, state, battery_level_t):
        
        #self.log2.info(data.decode('utf-8').split(',')[1]+ 'liste equiv: '+ str(self.liste_equiv))
        #for i in self.liste_equiv:
        #    if int(data.decode('utf-8').split(',')[1])==i:
                
        if int(data.decode('utf-8').split(',')[1]) in self.liste_equiv:  # entendre que les membres du grid
            #self.log2.info("NNNN1 "+ data.decode('utf-8').split(',')[1]+ " liste_equiv: "+ str(self.liste_equiv) + " node: " +str(self.node))
            if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
                
                if (data.decode('utf-8').split(',')[2] not in self.messages):#filtrer les anciens messages
                    self.messages.append(data.decode('utf-8').split(',')[1])
                    
                    if (data.decode('utf-8').split(',')[0] == "discovery_send_battery_level") and state == 2:#receiving battery level
                        #self.log2.info("NNNN1 "+ data.decode('utf-8').split(',')[1]+ " liste_equiv: "+ str(self.liste_equiv) + " node: " +str(self.node))
                        self.lock_nblm.acquire()
                        #self.log2.info("NNNN2 "+ str(self.nbr_battery_level_messages))
                        self.log2.info("Node message" + str(self.node) + ":" + str(self.nbr_battery_level_messages) + ":" + str(len(self.liste_equiv)))
                        if self.nbr_battery_level_messages == len(self.liste_equiv)-1:#j'ai recu tous les nv battery
                            self.lock_nblm.release()
                            return
                        self.lock_nblm.release()
                        #self.log2.info("NNNN2 ")
                        self.lock_nblm.acquire()
                        self.nbr_battery_level_messages += 1
                        self.lock_nblm.release()
                        if float(data.decode('utf-8').split(',')[3]) > battery_level_t:
                            print("Node " + str(self.node) + " < " + data.decode('utf-8').split(',')[1])
                            self.battery_big.set()#declaré au thread sender ma batterie est petite va vers before_sleep()
                            self.loop = False#stop receiving battery level
                        elif float(data.decode('utf-8').split(',')[3]) == battery_level_t and self.node < int(data.decode('utf-8').split(',')[1]):
                            self.battery_big.set()
                            self.loop = False#stop receiving battery level
                    elif (data.decode('utf-8').split(',')[0] == "discovery_send_ttl") and state == 1:
                        self.log2.info("TIme to sleep ")
                        self._TS = float(data.decode('utf-8').split(',')[3])
                        self.loop = False#stop receiving ttl/2


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
                self.battery_level -= self._energie_transmit

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
                    if int(data.decode('utf-8').split(',')[1]) in self.nodes_same_voisin_list:  # entendre que les voisins
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

    def active(self):
        #maybe
        if(len(self.liste_equiv)==1):
            print("Node " + str(self.node) + " enter Active state")
            self.log2.info("Node " + str(self.node) + " enter Active state")
            self.etat = "active"
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
        
            
        else:
            
            NodeDCC.lock_nfa.acquire()
            if (str(self.liste_equiv) in NodeDCC.nbr_finished_activity):
                NodeDCC.nbr_finished_activity[str(self.liste_equiv)] += 1
            else:
                NodeDCC.nbr_finished_activity[str(self.liste_equiv)] = 1
            NodeDCC.lock_nfa.release()
            print("Node " + str(self.node) + " enter Active state")
            self.log2.info("Node " + str(self.node) + " enter Active state")
            self.etat = "active"
            sock10 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock9 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            thread_send = Thread(target=self.send)
            thread_recv = Thread(target=self.receiv)
            thread_recv.start()
            thread_send.start()
            print("Node " + str(self.node) + ": TA = " + str(self._TA))
            self.log2.info("Node " + str(self.node) + ": TA = " + str(self._TA))
            if(self._TA > 0):
                time.sleep(self._TA)
            self.sock1.shutdown(socket.SHUT_RDWR)
            self.sock2.shutdown(socket.SHUT_RDWR)
            sock10.shutdown(socket.SHUT_RDWR)
            sock9.shutdown(socket.SHUT_RDWR)

            NodeDCC.lock_nfa.acquire()
            NodeDCC.nbr_finished_activity[str(self.liste_equiv)] -= 1
            NodeDCC.lock_nfa.release()

            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                return
            self.lock.release()


            while self.etat != "dead":
                NodeDCC.lock_nfa.acquire()
                if NodeDCC.nbr_finished_activity.get(str(self.liste_equiv)) == 0:#attendre shab lgrid ykemlou sleep
                    NodeDCC.lock_nfa.release()
                    break
                NodeDCC.lock_nfa.release()
                time.sleep(2)
            if self.etat == "dead":
                return
            self.discovery()
        
    def before_sleeep(self, sock9, battery_level):
        sock11 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.lock.acquire()
        self.battery_level -= self._energie_recoit
        if (self.battery_level <= 0):

            self.lock.release()#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.lock.release()
        thread_recv_beforesleep = Thread(target=self.receiv_ttl, args=[sock11, 1, 0])#creer thread receiv ttl
        NodeDCC.lock_nfd.acquire()
        NodeDCC.nbr_finished_discovery[str(self.liste_equiv)] -= 1#dire  j"ai entre before sleep
        NodeDCC.lock_nfd.release()
        thread_recv_beforesleep.start()
        while self.etat != "dead":#envoyé batterie level aux autres qui n'ont pas encore recu
            self.sendTTL(sock9, 2, battery_level)
            NodeDCC.lock_nfd.acquire()
            if NodeDCC.nbr_finished_discovery.get(str(self.liste_equiv)) == 0:#sortir si tous on recu niveau batterie
                NodeDCC.lock_nfd.release()
                break
            NodeDCC.lock_nfd.release()
            time.sleep(2)

        thread_recv_beforesleep.join()#pour assurer j'ai recu ttl
        NodeDCC.lock_nfd.acquire()
        NodeDCC.nbr_listen_ttl[str(self.liste_equiv)] -= 1#decrementer jusqu'a tous les noeuds on recu ttl
        NodeDCC.lock_nfd.release()
        while self.etat != "dead" and not NodeDCC.go[str(self.liste_equiv)]:#attendre que le chef modifie vers true(tous les noeuds on recu ttl)
            time.sleep(2)

        if self.etat == "dead":
            sock9.shutdown(socket.SHUT_RDWR)
            sock11.shutdown(socket.SHUT_RDWR)
            return
        self.sleeep()


    def sleeep(self):
        self.etat = "sleep"
        NodeDCC.lock_nfa.acquire()
        if (str(self.liste_equiv) in NodeDCC.nbr_finished_activity):
            NodeDCC.nbr_finished_activity[str(self.liste_equiv)] += 1
        else:
            NodeDCC.nbr_finished_activity[str(self.liste_equiv)] = 1
        NodeDCC.lock_nfa.release()
        print("Node " + str(self.node) + " enter Sleep state")
        self.log2.info("Node " + str(self.node) + " enter Sleep state")
        self.log2.info("Node " + str(self.node) + ": TS = " + str(self._TS))
        if(self._TS > 0):
            time.sleep(self._TS)
        NodeDCC.lock_nfa.acquire()
        NodeDCC.nbr_finished_activity[str(self.liste_equiv)] -= 1  # le noeud a terminé sleep
        NodeDCC.lock_nfa.release()
        self.lock.acquire()
        if (self.battery_level <= 0):
            self.lock.release()
            return
        self.lock.release()


        while self.etat != "dead":
            NodeDCC.lock_nfa.acquire()
            if NodeDCC.nbr_finished_activity.get(str(self.liste_equiv)) == 0:  # si tous on fini sleep and chef active
                NodeDCC.lock_nfa.release()
                break
            NodeDCC.lock_nfa.release()
            time.sleep(2)
        if self.etat == "dead":
            return
        self.discovery()
