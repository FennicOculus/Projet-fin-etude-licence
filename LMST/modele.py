from threading import Thread,Event,Lock
import time
import random
import logging
import pickle
from Sink import Sink
from Node import Node
from LMST import LMST
from NodeDCC import NodeDCC
import networkx as nx
from networkx.algorithms import tree
import matplotlib.pyplot as plt

class Application(Thread):
        

        def __init__(self,nb_noeud,subplotDC,subplotGen,subplotNbNoeud,subplotEn,canvas,colorbar):
            Thread.__init__(self)
            self.nb_noeud=nb_noeud
            self.subplotDC=subplotDC
            self.subplotNbNoeud=subplotNbNoeud
            self.subplotEn=subplotEn
            self.subplotGen=subplotGen
            self.canvas=canvas
            self.arrete = Event()
            self.stopevent = Event()
            self.fLMST=False
            self.fGr=False
            self.colorbar=colorbar

            
        def run(self):#class modele lance
            finGr=True
            finDC=True
            intervale=1
            self.subplotDC.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1])
            self.subplotDC.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1])

            self.bbb()

            #G = nx.random_geometric_graph(self.nb_noeud + 1, 0.45)
            #nx.write_gpickle(G,"C:\\Users\\HP\\Documents\\PYTHON CODECADEMY\\PROJET\\GRAPHE\\102noeud.gpickle")
            G=nx.read_gpickle("C:\\Users\\HP\\Documents\\PYTHON CODECADEMY\\PROJET\\GRAPHE\\103noeud.gpickle")
            pos = nx.get_node_attributes(G, 'pos')
            for node in G.nodes():  # ajouter attribut grid_nbr pour chaque noeud
                G.nodes[node]['grid_nbr'] = (pos[node][0]) // 0.2 + ((pos[node][1]) // 0.2) * 5
            sGr = Sink(G.nodes[0]['grid_nbr'], list(G.adj[0]))
            sDC = Sink(G.nodes[0]['grid_nbr'], list(G.adj[0]))
            #les deux listes intermediaires entre modele et node nodedc
            lnoeudGr = [Node(node, G.nodes[node]['grid_nbr'], list(G.adj[node])) for node in G.nodes() if node != 0]
            lnoeudDC = [LMST(node,pos[node][0],pos[node][1],list(G.adj[node]), self.nb_noeud,G) for node in G.nodes() if node != 0]
            LMST.Liste_00=list(G.adj[0])
            LMST.X_00=pos[0][0]
            LMST.Y_00=pos[0][0]
            for node in G.nodes():
                self.log5.info("node : "+ str(node) + " liste de ces voisins: " + str(list(G.adj[node])))

            casGr=self.runCasGr(intervale, G, pos, sGr, lnoeudGr)
            casDC=self.runCasDC(intervale, G, pos, sDC, lnoeudDC)
            t=0
            noeud_rest_Gr={t:self.nb_noeud}
            self.log7.info("noeud restant Cas normal: "+ str(noeud_rest_Gr))
            energie_rest_Gr= {t:self.nb_noeud*5}
            self.log7.info("energie restante Cas normal: "+ str(energie_rest_Gr))
            noeud_rest_DC = {t: self.nb_noeud}
            energie_rest_DC = {t: self.nb_noeud * 5}
            while (finGr or finDC):
                while(finGr or finDC)and(not self.arrete.is_set())and(not self.stopevent.is_set()):
                    t+=intervale#time graph update 1s
                    self.log7.info("le temps : "+ str(t))
                    if finGr:
                        res=casGr.__next__()
                        finGr=res[0]
                        noeud_rest_Gr.update({t:len(finGr)})
                        if(t>0 and (t % 50) ==0 ):
                            self.log7.info("noeud restant Cas normal: "+ str(noeud_rest_Gr))
                        energie_rest_Gr.update({t:sum([n.battery_level for n in finGr])})                        
                        if(t>0 and (t % 50) ==0 ):
                            self.log7.info("energie restante Cas normal: "+ str(energie_rest_Gr))
                    if finDC:
                        res=casDC.__next__()
                        finDC=res[0]
                        noeud_rest_DC.update({t:len(finDC)})
                        energie_rest_DC.update({t:sum([n.battery_level for n in finDC])})
                    if t==intervale:
                        plt.colorbar(self.nodes,cax = self.colorbar). set_label("l'énergie restante dans les nœuds par joule")
                    #reafrichissement du graphe de nombre de noeud en fonction de temps
                    self.subplotNbNoeud.clear()
                    self.subplotNbNoeud.set_title('Nbr nœuds vivants / temps',fontsize=12)
                    self.subplotNbNoeud.plot([key for key in noeud_rest_Gr],[noeud_rest_Gr[key] for key in noeud_rest_Gr],"green",linewidth=0.8,label="Sans DC")
                    self.subplotNbNoeud.plot([key for key in noeud_rest_DC],[noeud_rest_DC[key] for key in noeud_rest_DC], "red", linewidth=0.8,label="Avec DC")
                    self.subplotNbNoeud.set_xlabel("temps(s)",fontsize=12)
                    self.subplotNbNoeud.set_ylabel("Nbr nœuds vivants",fontsize=12)
                    #reafrichissment d'energie par temps
                    self.subplotEn.clear()
                    self.subplotEn.set_title("l'énergie restante / temps",fontsize=12)
                    self.subplotEn.plot([key for key in energie_rest_Gr],[energie_rest_Gr[value] for value in energie_rest_Gr],"green",linewidth=0.8,label="Sans DC")
                    self.subplotEn.plot([key for key in energie_rest_DC],[energie_rest_DC[value] for value in energie_rest_DC],"red",linewidth=0.8,label="Avec DC")
                    self.subplotEn.set_xlabel("temps(s)",fontsize=12)
                    self.subplotEn.set_ylabel("Énergie restante(j)",fontsize=12)
                    self.canvas.draw_idle()
                    time.sleep(1)
                while ((self.arrete.is_set()) and (not self.stopevent.is_set())):
                    time.sleep(1)
                if self.stopevent.is_set():
                    break


        def runCasGr(self,temps, G, pos, s, lnoeud):#cas general change coler, refresh noeud active list,
            plot=self.subplotGen
            fin=True
            while(fin):
                lnoeudrestant=[n for n in lnoeud if n.etat=="active"]
                #afficher les graphes
                ledges=sibler(G.edges(), [n.node for n in lnoeudrestant]+[0])
                plot.clear()
                plot.set_title('la topologie sans protocole',fontsize=12)
                self.nodes = nx.draw_networkx_nodes(G,pos=pos,nodelist=[n.node for n in lnoeudrestant],ax=plot,node_size=40,with_labels =False,node_color=[n.battery_level for n in lnoeudrestant],cmap=plt.cm.autumn,label='nœud',vmin=0, vmax=5)
                nx.draw_networkx_nodes(G,pos={0:nx.get_node_attributes(G,'pos')[0]},nodelist=[0],ax=plot,node_size=60,with_labels=False,node_color='Green',node_shape='s',label='puits')
                nx.draw_networkx_edges(G,pos=pos,ax=plot,edgelist=ledges,arrows=False,width=0.5,label='lien bidirectionnel')
                fin=len(lnoeudrestant)
                yield [lnoeudrestant,lnoeud,s]#return plusieurs (s:sink)
            self.finGr = False

        def runCasDC(self,temps, G, pos, s, lnoeud):
            self.log5.info("Run DC")
            plot=self.subplotDC
            fin=True
            while(fin):
                lnoeudrestant=[n for n in lnoeud if n.etat!="dead"]
                #afficher les graphes
                self.log5.info("Avant LMST")
                if(LMST.compt_nb_nodes !=self.nb_noeud):
                    self.log5.info("Le nombre: "+str(LMST.compt_nb_nodes))
                    ledges=sibler(G.edges(),[n.node for n in lnoeudrestant]+[0])
                    #self.log5.info("liste LMST: "+ str(LMST.liste_distance_min))
                    plot.clear()
                    plot.set_title('la topologie Duty Cycling',fontsize=12)
                    
                        
                    #self.log7.info("LMST EDGES : " + str(LMST.edges_in_MST)) #le set est vide

                    self.nodesDC = nx.draw_networkx_nodes(G,pos=pos,nodelist=[n.node for n in lnoeudrestant if n.etat == "active"],ax=plot,node_size=40,with_labels =False,node_color=[n.battery_level for n in lnoeudrestant if n.etat == "active"],cmap=plt.cm.autumn,label='nœud',vmin=0, vmax=5)

                    nx.draw_networkx_nodes(G,pos={0:nx.get_node_attributes(G,'pos')[0]},nodelist=[0],ax=plot,node_size=60,with_labels=False,node_color='Green',node_shape='s',label='puits')


                    sleep_nodes = [n for n in lnoeudrestant if n.etat == "sleep"]

                    for i in sleep_nodes:
                        nx.draw_networkx_nodes(G, pos={i.node: nx.get_node_attributes(G, 'pos')[i.node]}, nodelist=[i.node],
                                           ax=plot, node_size=40, with_labels=False, node_color='skyblue', label='nœud',
                                           vmin=0, vmax=5)

                    discovery_nodes = [n for n in lnoeudrestant if n.etat == "discovery"]

                    for i in discovery_nodes:
                        nx.draw_networkx_nodes(G, pos={i.node: nx.get_node_attributes(G, 'pos')[i.node]}, nodelist=[i.node],
                                           ax=plot, node_size=40, with_labels=False, node_color='pink', label='nœud',
                                           vmin=0, vmax=5)

                    nx.draw_networkx_edges(G,pos=pos,ax=plot,edgelist=ledges,arrows=False,width=0.5,label='lien bidirectionnel')
                    fin=len(lnoeudrestant)
                    yield [lnoeudrestant,lnoeud,s]
                else:
                
                    #ledges=sibler(LMST.liste_distance_min,[n.node for n in lnoeudrestant]+[0])
                    lienreciproque,liennonreciproque=split(LMST.Liste_arcs)
                    self.log5.info("liste LMST: "+ str(LMST.liste_distance_min))
                    plot.clear()
                    plot.set_title('la topologie Duty Cycling',fontsize=12)
                    #self.log7.info("LMST EDGES : " + str(LMST.edges_in_MST)) #le set est vide

                    self.nodesDC = nx.draw_networkx_nodes(G,pos=pos,nodelist=[n.node for n in lnoeudrestant if n.etat == "active"],ax=plot,node_size=40,with_labels =False,node_color=[n.battery_level for n in lnoeudrestant if n.etat == "active"],cmap=plt.cm.autumn,label='nœud',vmin=0, vmax=5)

                    nx.draw_networkx_nodes(G,pos={0:nx.get_node_attributes(G,'pos')[0]},nodelist=[0],ax=plot,node_size=60,with_labels=False,node_color='Green',node_shape='s',label='puits')


                    sleep_nodes = [n for n in lnoeudrestant if n.etat == "sleep"]

                    for i in sleep_nodes:
                        nx.draw_networkx_nodes(G, pos={i.node: nx.get_node_attributes(G, 'pos')[i.node]}, nodelist=[i.node],
                                           ax=plot, node_size=40, with_labels=False, node_color='skyblue', label='nœud',
                                           vmin=0, vmax=5)

                    discovery_nodes = [n for n in lnoeudrestant if n.etat == "discovery"]

                    for i in discovery_nodes:
                        nx.draw_networkx_nodes(G, pos={i.node: nx.get_node_attributes(G, 'pos')[i.node]}, nodelist=[i.node],
                                           ax=plot, node_size=40, with_labels=False, node_color='pink', label='nœud',
                                           vmin=0, vmax=5)

                    nx.draw_networkx_edges(G,pos=pos,ax=plot,edgelist=lienreciproque,arrows=False,width=0.5,label='lien bidirectionnel')
                    nx.draw_networkx_edges(G,pos=pos,ax=plot,edgelist=liennonreciproque,arrowstyle='->',style='dashed',width=0.3,label='lien unidirectionnel')
                    fin=len(lnoeudrestant)
                    yield [lnoeudrestant,lnoeud,s]


            self.finGr = False

        def arreter(self):
            self.stopevent.set()
        def suspendre(self):
            self.arrete.set()
        def reprendre(self):
            self.arrete.clear()

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
            #self.setup_logger('log4', r'C:\Users\Samy\Desktop\Application1\log4.log')
            #self.log4 = logging.getLogger('log4')
            self.setup_logger('log5', r'C:\Users\HP\Documents\PYTHON CODECADEMY\PROJET\Application4\log5.log')
            self.log5 = logging.getLogger('log5')
            self.setup_logger('log7', r'C:\Users\HP\Documents\PYTHON CODECADEMY\PROJET\Application4\log7.log')
            self.log7 = logging.getLogger('log7')
                
                
def split(edges):#decide dessin des liens
    """ decoupe la liste des arcs en 2 se qui ont reciproque et ceux qui ne sont pas"""
    lrec=[]
    lnrec=[]
    for e in edges:
        if (e[1],e[0]) in edges:
            if e not in lrec and (e[1],e[0]) not in lrec:
                lrec.append(e)
        else:
            lnrec.append(e)
    return lrec,lnrec
        
def ecrire(nom_fichier,donnee):
    f=open(nom_fichier,"w")
    for temps in donnee:
        f.write('{}:\t{}\n'.format(temps,donnee[temps]))
    f.close()



def sibler(edges,noeuds):#decide dessin des liens
    resultat=[]
    for e in edges:
        if e[0] in noeuds and e[1] in noeuds:
            resultat.append(e)
    return resultat
