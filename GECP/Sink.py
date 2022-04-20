import socket
import struct
from threading import Thread


#dans la boucle qui crée les objets noeuds a partir du graphe, laisser un noeud pour le crée en tant que Sink object et coloré le

class Sink:

    def __init__(self, grid_nbr, voisins):
        self.grid_nbr = grid_nbr
        self.voisins = voisins
        self.etat = "active"

        thread_sinkrecv = Thread(target=self.sinkreceiv)
        thread_sinkrecv.start()
        #logging.basicConfig(filename='nodes.log', level=logging.INFO, format='%(asctime)s | %(message)s',
                            #datefmt='%m/%d/%Y %I:%M:%S')
    def sinkreceiv(self):
        multicast_group = '224.3.29.71'  # pour listner
        server_address = ('', 10000)
        # Create the socket
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to the server address
        sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock2.bind(server_address)
        # Tell the operating system to add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock2.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Receive loop
        #logging.info('Sink Waiting to receive message')
        while True:
            try:
                data, address = sock2.recvfrom(1024)  # receive instruction
            except socket.timeout:
                break;

            #filtrer non voisins
            #if int(data.decode('utf-8').split(',')[1]) in self.voisins:
                #logging.info('Sink received: ' + data.decode('utf-8'))
