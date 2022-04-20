import socket
import struct
from threading import Thread, Lock, Event
import time
import sys
import logging
import random


class NodeDC:
    nbr_finished_hello = 0
    nbr_finished_discovery = dict()
    nbr_listen_ttl = dict()
    nbr_finished_activity = dict()
    nodes_dead = []#les noeuds morts, pour les oubliés dans l'etape discovery
    go = dict()
    lock_nfd = Lock()
    lock_nlt = Lock()
    lock_nfa = Lock()
    lock_nodes_dead = Lock()
    def __init__(self, node_nbr,voisins, nbr_nodes):
        #logging.basicConfig(filename='gaf.log', level=logging.INFO, format='%(asctime)s | %(message)s',
                            #datefmt='%m/%d/%Y %I:%M:%S')
        self.nbr_nodes = nbr_nodes #le nombres des noeuds existant dans graph
        self.node = node_nbr  # recuperer from G.node[node]
        #self.grid_nbr = grid_nbr  # recuperer from G.node[node]['grid_nbr']
        self.voisins = voisins  # recuperer from G.adj[i]
        self.etat = "discovery"  # active - sleep - discovery - dead
        self.battery_level = 5  # niveau batterie max en joule
        self.message = 'Node ' + str(node_nbr) + ' send you'
        self.messages = []  # contient les id des messages pour que chaque noeud redifuse le msg une seule fois
        # --------------hello phase attributes------------------
        self.hello_from_voisins_list = []  # pour calculer le nombre msg recu des voisin
        #self.nodes_same_grid_list = []  # contient les noeuds qui appartient au meme grid que moi
        self.hello_phase_finished = False
        self.liset_equiv = [] 
        self.liset_2_sauts = []
        self.duty_cycling = True  # activer mode duty cycling ou execution normal
        # --------------------------------------------------------
        self.sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket de send
        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket de recv
        # sock3 : socket sendRecvedMesg
        # sock4 : socket de hello_phase_recv
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
        self.lock_ndlm = Lock()
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
            NodeDC.lock_nodes_dead.acquire()
            #for n in NodeDC.nodes_dead:
                #if n in self.nodes_same_grid_list:
                    #self.nodes_same_grid_list.remove(n)#remove dead nodes from the same grid list
            NodeDC.lock_nodes_dead.release()
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
        NodeDC.lock_nodes_dead.acquire()
        NodeDC.nodes_dead.append(self.node)#remplir la liste des noeuds morts
        NodeDC.lock_nodes_dead.release()
        print('Node ' + str(self.node) + ' DEAD')
        self.log2.info('Node ' + str(self.node) + ' DEAD')
        return

    def decouvre(self):
        
        print("Node " + str(self.node) + " enter Discovery state")
        self.log2.info("Node " + str(self.node) + " enter Discovery state")
        self.etat = "discovery"
        self.sleep.clear()# enlever event sleep
        self.battery_big.clear()# enlever event ma batterie petite
        self.lock.acquire()
        battery_level_t = self.battery_level# le niveau de batterie que j'envoie et je compare reste constant
        liiste_vois = self.hello_from_voisins_list
        self.lock.release()
        print("Node " + str(self.node) + " : " + list(liiste_vois))
        self.log2.info("Node " + str(self.node) + " : " + list(liiste_vois))
        sock9 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#envoyé
        sock10 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#receiv battery level
        
        thread_recv_discovery = Thread(target=self.receiv_discover, args=[sock10,liiste_vois])#2 veut dire recevoir niveau batterie et non ttl
        thread_recv_discovery.start()#lancer l'ecoute sur batterie level
        
        self.lock.acquire()
        self.battery_level -= self._energie_transmit
        self.lock.release()

        self.lock.acquire()
        for n in range(len(self.liiste_vois)):#maybeee

            self.battery_level -= self._energie_recoit
        self.lock.release()

        while self.etat != "dead" and not self.battery_big.is_set():#je sort si battery petit
            self.sendListVois(sock9, liiste_vois)#2 signifie que j'envoie niveau batterie(socket crée une seule fois)
            self.lock_nblm.acquire()

            if self.nbr_battery_level_messages == len(liiste_vois):
                self.lock_nblm.release()
                break#je sort si je suis chef
            self.lock_nblm.release()
            time.sleep(2)

        self.lock_ndlm.acquire()
        self.nbr_disco_level_messages = 0
        self.lock_ndlm.release()
        sock9.shutdown(socket.SHUT_RDWR)
        sock10.shutdown(socket.SHUT_RDWR)
        self.discovery()

    def discovery(self):


        NodeDC.lock_nfd.acquire()
        #if (str(int(self.grid_nbr)) in NodeDC.nbr_finished_discovery):#incrementer ce dictionnaire statique pour le decrementer aprés pour assurer que tous les noeuds ont recu le niveau de batterie
        #    NodeDC.nbr_finished_discovery[str(int(self.grid_nbr))] += 1
        #else:#sinon initialiser nv numero grille comme key et mettre valeur a 1
        #    NodeDC.nbr_finished_discovery[str(int(self.grid_nbr))] = 1
        NodeDC.lock_nfd.release()

        NodeDC.lock_nlt.acquire()
        #if (str(int(self.grid_nbr)) in NodeDC.nbr_listen_ttl):
        #    NodeDC.nbr_listen_ttl[str(int(self.grid_nbr))] += 1#dictionnaire pour savoir si j'ai recu ttl/2 de tous les noeuds du meme grille
        #else:
        #    NodeDC.nbr_listen_ttl[str(int(self.grid_nbr))] = 1
        NodeDC.lock_nlt.release()

        print("Node " + str(self.node) + " enter Discovery state")
        self.log2.info("Node " + str(self.node) + " enter Discovery state")
        self.etat = "discovery"
        self.sleep.clear()# enlever event sleep
        self.battery_big.clear()# enlever event ma batterie petite
        self.lock.acquire()
        battery_level_t = self.battery_level# le niveau de batterie que j'envoie et je compare reste constant
        self.lock.release()
        print("Node " + str(self.node) + " : " + str(battery_level_t))
        self.log2.info("Node " + str(self.node) + " : " + str(battery_level_t))
        sock6 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#envoyé
        sock7 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#receiv battery level

        thread_recv_discovery = Thread(target=self.receiv_ttl, args=[sock7, 2, battery_level_t])#2 veut dire recevoir niveau batterie et non ttl
        thread_recv_discovery.start()#lancer l'ecoute sur batterie level

        self.lock.acquire()
        self.battery_level -= self._energie_transmit
        self.lock.release()

        self.lock.acquire()
        for n in range(len(self.liset_equiv)):#maybeee

            self.battery_level -= self._energie_recoit
        self.lock.release()

        while self.etat != "dead" and not self.battery_big.is_set():#je sort si battery petit
            self.sendTTL(sock6, 2, battery_level_t)#2 signifie que j'envoie niveau batterie(socket crée une seule fois)
            self.lock_nblm.acquire()

            if self.nbr_battery_level_messages == len(self.liset_equiv):
                self.lock_nblm.release()
                break#je sort si je suis chef
            self.lock_nblm.release()
            time.sleep(2)

        self.lock_nblm.acquire()
        self.nbr_battery_level_messages = 0
        self.lock_nblm.release()
        sock7.shutdown(socket.SHUT_RDWR)
        sock6.shutdown(socket.SHUT_RDWR)
        #NodeDC.go[str(int(self.grid_nbr))] = False#pour que tous entre active et sleep au meme temps
        if self.battery_big.is_set():
            self.before_sleeep(sock6, battery_level_t)#aller vers before sleep
            return#sortir de la fonction discovery
#----------------partie chef--------------------------------------------------------
        self.lock.acquire()
        self.ttl = (self.battery_level * self.ttl_max) / 5  # set ttl value maybe
        self.lock.release()
        self._TA = self.ttl / 2

        NodeDC.lock_nfd.acquire()
        #NodeDC.nbr_finished_discovery[str(int(self.grid_nbr))] -= 1 #annoncé j'ai terminé discovery aux autres noeds(lzm ge3 ykemlou bach nroho lsend ttl
        NodeDC.lock_nfd.release()
        while self.etat != "dead":
            self.sendTTL(sock6, 2, battery_level_t)#envoyé niveau batterie du futur chef pour assuré la reception de tous les noeuds
            NodeDC.lock_nfd.acquire()
            #if NodeDC.nbr_finished_discovery.get(str(int(self.grid_nbr))) == 0:#si tous on fini discovery
            #    NodeDC.lock_nfd.release()
            #    break
            NodeDC.lock_nfd.release()
            time.sleep(2)
#tous on sorti de l'etape dicovery
        NodeDC.lock_nlt.acquire()
        #NodeDC.nbr_listen_ttl[str(int(self.grid_nbr))] -= 1#le chef est pret pour envoyer ttl
        NodeDC.lock_nlt.release()

        self.lock.acquire()
        self.battery_level -= self._energie_transmit
        self.lock.release()

        while self.etat != "dead":
            self.sendTTL(sock6, 1, 0)#le chef envoie ttl
            NodeDC.lock_nlt.acquire()
            #if NodeDC.nbr_listen_ttl.get(str(int(self.grid_nbr))) == 0:#le dernier noeud before sleep qui passe a l'ecoute??
            #    NodeDC.lock_nlt.release()
            #    break
            NodeDC.lock_nlt.release()
            time.sleep(2)
        #NodeDC.go[str(int(self.grid_nbr))] = True #tous les noeud on recu ttl je passe a l'active
        if(self.etat == "dead"):
            return
        self.active()

    def active(self):
        #maybe
        NodeDC.lock_nfa.acquire()
        #if (str(int(self.grid_nbr)) in NodeDC.nbr_finished_activity):
        #    NodeDC.nbr_finished_activity[str(int(self.grid_nbr))] += 1
        #else:
        #    NodeDC.nbr_finished_activity[str(int(self.grid_nbr))] = 1
        NodeDC.lock_nfa.release()
        print("Node " + str(self.node) + " enter Active state")
        self.log2.info("Node " + str(self.node) + " enter Active state")
        self.etat = "active"
        sock7 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock6 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        sock6.shutdown(socket.SHUT_RDWR)
        sock7.shutdown(socket.SHUT_RDWR)

        NodeDC.lock_nfa.acquire()
        #NodeDC.nbr_finished_activity[str(int(self.grid_nbr))] -= 1
        NodeDC.lock_nfa.release()

        self.lock.acquire()
        if (self.battery_level <= 0):
            self.lock.release()
            return
        self.lock.release()


        while self.etat != "dead":
            NodeDC.lock_nfa.acquire()
           # if NodeDC.nbr_finished_activity.get(str(int(self.grid_nbr))) == 0:#attendre shab lgrid ykemlou sleep
            #    NodeDC.lock_nfa.release()
             #   break
            NodeDC.lock_nfa.release()
            time.sleep(2)
        if self.etat == "dead":
            return
        self.discovery()

    def before_sleeep(self, sock6, battery_level):
        sock8 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.lock.acquire()
        self.battery_level -= self._energie_recoit
        if (self.battery_level <= 0):

            self.lock.release()#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.lock.release()
        thread_recv_beforesleep = Thread(target=self.receiv_ttl, args=[sock8, 1, 0])#creer thread receiv ttl
        NodeDC.lock_nfd.acquire()
        #NodeDC.nbr_finished_discovery[str(int(self.grid_nbr))] -= 1#dire  j"ai entre before sleep
        NodeDC.lock_nfd.release()
        thread_recv_beforesleep.start()
        while self.etat != "dead":#envoyé batterie level aux autres qui n'ont pas encore recu
            self.sendTTL(sock6, 2, battery_level)
            NodeDC.lock_nfd.acquire()
            #if NodeDC.nbr_finished_discovery.get(str(int(self.grid_nbr))) == 0:#sortir si tous on recu niveau batterie
             #   NodeDC.lock_nfd.release()
              #  break
            NodeDC.lock_nfd.release()
            time.sleep(2)

        thread_recv_beforesleep.join()#pour assurer j'ai recu ttl
        NodeDC.lock_nfd.acquire()
        #NodeDC.nbr_listen_ttl[str(int(self.grid_nbr))] -= 1#decrementer jusqu'a tous les noeuds on recu ttl
        NodeDC.lock_nfd.release()
        while self.etat != "dead" and not NodeDC.go[str(int(self.grid_nbr))]:#attendre que le chef modifie vers true(tous les noeuds on recu ttl)
            time.sleep(2)

        if self.etat == "dead":
            sock6.shutdown(socket.SHUT_RDWR)
            sock8.shutdown(socket.SHUT_RDWR)
            return
        self.sleeep()

    def sleeep(self):
        self.etat = "sleep"
        NodeDC.lock_nfa.acquire()
        #if (str(int(self.grid_nbr)) in NodeDC.nbr_finished_activity):
        #    NodeDC.nbr_finished_activity[str(int(self.grid_nbr))] += 1
        #else:
        #    NodeDC.nbr_finished_activity[str(int(self.grid_nbr))] = 1
        NodeDC.lock_nfa.release()
        print("Node " + str(self.node) + " enter Sleep state")
        self.log2.info("Node " + str(self.node) + " enter Sleep state")
        print("Node " + str(self.node) + ": TS = " + str(self._TS))
        if(self._TS > 0):
            time.sleep(self._TS)
        NodeDC.lock_nfa.acquire()
        #NodeDC.nbr_finished_activity[str(int(self.grid_nbr))] -= 1  # le noeud a terminé sleep
        NodeDC.lock_nfa.release()
        self.lock.acquire()
        if (self.battery_level <= 0):
            self.lock.release()
            return
        self.lock.release()


        while self.etat != "dead":
            NodeDC.lock_nfa.acquire()
         #   if NodeDC.nbr_finished_activity.get(str(int(self.grid_nbr))) == 0:  # si tous on fini sleep and chef active
          #      NodeDC.lock_nfa.release()
           #     break
            NodeDC.lock_nfa.release()
            time.sleep(2)
        if self.etat == "dead":
            return
        self.discovery()

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
        while not NodeDC.nbr_finished_hello == self.nbr_nodes:
            time.sleep(0.1)
        self.decouvre()

    def sendTTL(self, sock6, state, battery_level):
        # create msg
        if state == 1:
            self.lock.acquire()
            msgDC = "discovery_send_ttl," + str(self.node) + ',' + str(random.randint(0, sys.maxsize)) + ',' + str(
                self._TA)

            self.lock.release()
        elif state == 2:
            self.lock.acquire()
            msgDC = "discovery_send_battery_level," + str(self.node) + ',' + str(random.randint(0, sys.maxsize)) + ',' + str(battery_level) 
                    #+ ',' +list(self.hello_from_voisins_list))  # case 6
            self.lock.release()

        if state == 1:
            multicast_group = ('224.3.29.72', 10000)#pour la charge séparé les reseaux
        else:
            multicast_group = ('224.3.29.71', 10000)

        sock6 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the server address
        sock6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl1 = struct.pack('b', 1)
        sock6.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl1)

        try:
            print("Node " + str(self.node) + " send TTL" + str(state))
            sent = sock6.sendto(msgDC.encode(), multicast_group)

        except (socket.timeout, socket.error) as e:
            self.lock.release()
        finally:
            sock6.shutdown(socket.SHUT_RDWR)
            # sock6.close()

    def receiv_ttl(self, sock7, state, battery_level_t):
        # print('receiv function')
        if state == 1:
            multicast_group = '224.3.29.72'  # pour listner
        else:
            multicast_group = '224.3.29.71'  # pour listner
        server_address = ('', 10000)
        # Bind to the server address
        sock7.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock7.bind(server_address)
        # Tell the operating system to add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock7.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # Receive loop
        if state == 1:
            print('Node ' + str(self.node) + ' Waiting to receive TTL')
        if state == 2:
            print('Node ' + str(self.node) + ' Waiting to receive Battery Level')
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
                data, address = sock7.recvfrom(1024)  # receive instruction
                thread_traitement_reciv_ttl.append(Thread(target=self.traitement_reciv_ttl, args=[data, state, battery_level_t]))
                thread_traitement_reciv_ttl[index].start()
                index+=1

            except (socket.timeout, socket.error) as e:
                break
    
        def sendListVois(self, sock9, liiste_vois):
        # create msg

            self.lock.acquire()
            msgDC = "discovery_send_liste_voisin," + str(self.node) + ',' + str(random.randint(0, sys.maxsize)) + ',' + str(selfliiste_vois)  # case 6
            self.lock.release()

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

    
        def receiv_discover(self, sock10, liiste_vois):
            # print('receiv function')
        
            multicast_group = '224.3.29.71'  # pour listner
            server_address = ('', 10000)
            # Bind to the server address
            sock10.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock10.bind(server_address)
            # Tell the operating system to add the socket to the multicast group on all interfaces.
            group = socket.inet_aton(multicast_group)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            sock7.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            # Receive loop 
            print('Node ' + str(self.node) + ' Waiting to receive Battery Level')
            data=""
            thread_traitement_reciv_ttl1 = []
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
                    thread_traitement_reciv_ttl1.append(Thread(target=self.traitement_reciv_vois, args=[data, liiste_vois]))
                    thread_traitement_reciv_ttl1[index].start()
                    index+=1

                except (socket.timeout, socket.error) as e:
                    break

    def traitement_reciv_vois(self, data, liiste_vois):
        if int(data.decode('utf-8').split(',')[1]) in self.liiste_vois:  # entendre que les membres du grid
            if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
                if (data.decode('utf-8').split(',')[2] not in self.messages):#filtrer les anciens messages
                    self.messages.append(data.decode('utf-8').split(',')[1])
                    if (data.decode('utf-8').split(',')[0] == "discovery_send_liste_voisin"):#receiving battery level
                        self.liset_2_sauts = data.decode('utf-8').split(',')[3]
                        if len(self.liset_2_sauts)==len(self.liiste_vois):
                            self.liset_2_sauts.sort()
                            self.liiste_vois.sort()
                            if test_list1 == test_list2:
                                print (str(self.liiste_vois))
                                self.liset_equiv.append(
                                data.decode('utf-8').split(',')[1]) 
                        self.lock_ndlm.acquire()
                        print("Node " + str(self.node) + ":" + str(self.nbr_battery_level_messages) + ":" + str(
                            len(self.liset_equiv)))
                        if self.nbr_disco_level_messages == len(self.liiste_vois):#j'ai recu tous les nv battery
                            self.lock_ndlm.release()
                            return
                        self.lock_nblm.release()
                        self.lock_nblm.acquire()
                        self.nbr_disco_level_messages += 1
                        self.lock_nblm.release()
                        
                    
                        
    def traitement_reciv_ttl(self, data, state, battery_level_t):
        if int(data.decode('utf-8').split(',')[1]) in self.liset_equiv:  # entendre que les membres du grid
            if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
                if (data.decode('utf-8').split(',')[2] not in self.messages):#filtrer les anciens messages
                    self.messages.append(data.decode('utf-8').split(',')[1])
                    if (data.decode('utf-8').split(',')[0] == "discovery_send_battery_level") and state == 2:#receiving battery level
                        self.lock_nblm.acquire()
                        print("Node " + str(self.node) + ":" + str(self.nbr_battery_level_messages) + ":" + str(
                            len(self.liset_equiv)))
                        if self.nbr_battery_level_messages == len(self.liset_equiv):#j'ai recu tous les nv battery
                            self.lock_nblm.release()
                            return
                        self.lock_nblm.release()
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
                        self._TS = float(data.decode('utf-8').split(',')[3])
                        self.loop = False#stop receiving ttl/2

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
            random.randint(0, sys.maxsize)) + ',' + self.etat + ',' + str(
            self.battery_level) #+ ',' + 'hello this is my grid number' + ',' + str(self.grid_nbr)
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
                if len(self.voisins) == 0:  # si le noeud n'a pas de voisin il ne recoit aucun hello msg
                    break
                if len(self.voisins) == 1 and (self.voisins[0] == 0):  # si le noeud a seulement le sink comme voisin il ne recoit aucun hello msg
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
            
            if str(data.decode('utf-8').split(',')[0]) == "hello_phase":
                if int(data.decode('utf-8').split(',')[1]) in self.voisins:  # entendre que les voisins
                    if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
                        if (data.decode('utf-8').split(',')[2] not in self.messages):  # filtrer les messages deja recu
                            #self.log2.info("je suis rentre")
                            self.messages.append(data.decode('utf-8').split(',')[2])  # ajouter msg id
                            #self.hello_from_voisins_list.append(
                            #    int(data.decode('utf-8').split(',')[1]))  # ajouter au compteur du msg hello
                            #self.log2.info(str(self.hello_from_voisins_list))       
                                #if (float(data.decode('utf-8').split(',')[6]) == self.grid_nbr):  # ajouter les noeuds meme grille
                                #   self.nodes_same_grid_list.append(int(data.decode('utf-8').split(',')[1]))

                            if 0 in self.voisins:  # sink eliminer comme voisin
                               if (len(self.hello_from_voisins_list) == len(
                                        self.voisins) - 1):  # tester si tous les msgs hello sont arrivé
                                    break
                            if len(self.hello_from_voisins_list) == len(
                                    self.voisins):  # tester si tous les msgs hello sont arrivé
                               break
                            self.log2.info(
                                'Node ' + str(self.node) + ' received: ' + data.decode('utf-8').split(',')[4] + ' : ' +
                                data.decode('utf-8').split(',')[5])
            self.lock.acquire()
            if (self.battery_level <= 0):
                self.lock.release()
                break
            self.lock.release()
        sock4.shutdown(socket.SHUT_RDWR)
        # sock4.close()
        NodeDC.nbr_finished_hello += 1#assurer que tous les noeuds on recu hello messages
        self.log2.info("Node " + str(self.node) + ": " + ",".join(str(n) for n in self.hello_from_voisins_list))

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
                self.battery_level) + ',' + self.message #+ ',' + str(self.grid_nbr)
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
                    if int(data.decode('utf-8').split(',')[1]) in self.voisins:  # entendre que les voisins
                        #if (data.decode('utf-8').split(',')[1] != str(self.node)):  # filtrer moi meme(noeud)
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
