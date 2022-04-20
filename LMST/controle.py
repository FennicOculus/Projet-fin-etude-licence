import _tkinter
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
import tkinter as tk
import modele
import time




class controle():
    def __init__(self):
        self.threadSim=False
    
    def controlancemSim(self,nb_noeud,window):
        try:
            if(nb_noeud.get()<2):
                messagebox.showerror("Erreur", "le nombre de nœuds doit être supérieur a 2")
                return
        except _tkinter.TclError as e:
            messagebox.showerror("Erreur", "les valeurs doit être des entier positif ")
        #initialiser la fenetre
        frame=window.ajouter_frame_Sim(nb_node=nb_noeud.get())
        
        frame.canvas.get_tk_widget().config(width = 1240, height = 600)




        #on est dans le thread de simulation
        #un moyen pour recuperer le subplot afin de lancer la simulation
        self.threadDC=modele.Application(nb_noeud.get(), frame.sGLMST, frame.sGgr, frame.nr, frame.en, frame.canvas,frame.colorbar)
        self.threadSim=True
        self.threadDC.start()
            
    def fermer_fen(self,root):
        if self.threadSim == True:
            self.threadDC.suspendre()
            if messagebox.askokcancel("Quitter l'application", "Voulez vous quitter l'application"):
                self.threadDC.arreter()
            else:
                self.threadDC.reprendre()
                return
        root.destroy()
    
    def ajouterDC(self,window):
        if window.gLMST.get():
            #afficher le plot LMST
            window.sGLMST.set_visible(True)
            if not window.gGr.get():
                window.colorbar.set_visible(True) 
        else:
            #masquer le plot LMST
            window.sGLMST.set_visible(False)
            if not window.gGr.get():
                window.colorbar.set_visible(False) 
        self.reploter(window) 
            
    def ajouterGr(self,window):
        if window.gGr.get():
            #afficher le plot Gr
            window.sGgr.set_visible(True)
            if not window.gLMST.get():
                window.colorbar.set_visible(True)  
        else:
            #masquer le plot Gr
            window.sGgr.set_visible(False)
            if not window.gLMST.get():
                window.colorbar.set_visible(False)  
        self.reploter(window)
    
    def ajouterEn(self,window):
        if window.gEn.get():
            #afficher le plot Energie
            window.en.set_visible(True) 
        else:
            #masquer le plot Energie
            window.en.set_visible(False) 
        self.reploter(window) 
   
    def ajouterNb(self,window):
        if window.gNb.get():
            #afficher le plot Nombre de noeud
            window.nr.set_visible(True) 
        else:
            #masquer le plot Nombre de noeud
            window.nr.set_visible(False) 
        self.reploter(window) 

    
    def voireExecLMST(self,window):
        root=tk.Tk()
        root.title("Fichier d'execution avec Duty Cycling")
        text = tk.Text(root, height=26, width=50)
        scroll = tk.Scrollbar(root, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        fDC = open("duty-cycling-proto.log", "r")
        fDC.seek(0, 0)
        text.insert(tk.END,fDC.read())
        fDC.close()
        text.pack(side=tk.LEFT,fill=tk.BOTH,expand=1)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
    def voireExecGr(self,window):
        root=tk.Tk()
        root.title("Fichier d'execution sans protocole")
        text = tk.Text(root, height=26, width=50)
        scroll = tk.Scrollbar(root, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        fGr = open("sans-proto.log", "r")
        fGr.seek(0,0)
        text.insert(tk.END,fGr.read())
        fGr.close()
        text.pack(side=tk.LEFT,fill=tk.BOTH,expand=1)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def reploter(self,window):
        lmst=window.gLMST.get()
        gr=window.gGr.get()
        en=window.gEn.get()
        nb=window.gNb.get()
        td=window.gTD.get()
        if lmst and not gr and not en and not nb and not td:
            window.sGLMST.change_geometry(1,1,1)
        elif not lmst and gr and not en and not nb and not td:
            window.sGgr.change_geometry(1,1,1)
        elif not lmst and not gr and en and not nb and not td:
            window.en.change_geometry(1,1,1)
        elif not lmst and not gr and not en and nb and not td:
            window.nr.change_geometry(1,1,1)
        elif not lmst and not gr and not en and not nb and td:
            window.packet.change_geometry(1,1,1)
        elif lmst and gr and not en and not nb and not td:
            window.sGLMST.change_geometry(1,2,2)
            window.sGgr.change_geometry(1,2,1)
        elif lmst and not gr and en and not nb and not td:
            window.sGLMST.change_geometry(1,2,1)
            window.en.change_geometry(1,2,2)
        elif lmst and not gr and not en and nb and not td:
            window.sGLMST.change_geometry(1,2,1)
            window.nr.change_geometry(1,2,2)
        elif lmst and not gr and not en and not nb and td:
            window.sGLMST.change_geometry(1,2,1)
            window.packet.change_geometry(1,2,2)
        elif not lmst and gr and en and not nb and not td:
            window.sGgr.change_geometry(1,2,1)
            window.en.change_geometry(1,2,2)
        elif not lmst and gr and not en and nb and not td:
            window.sGgr.change_geometry(1,2,1)
            window.nr.change_geometry(1,2,2)
        elif not lmst and gr and not en and not nb and td:
            window.sGgr.change_geometry(1,2,1)
            window.packet.change_geometry(1,2,2)
        elif not lmst and not gr and en and nb and not td:
            window.en.change_geometry(1,2,1)
            window.nr.change_geometry(1,2,2)
        elif not lmst and not gr and en and not nb and td:
            window.en.change_geometry(1,2,1)
            window.packet.change_geometry(1,2,2)
        elif not lmst and not gr and not en and nb and td:
            window.nr.change_geometry(1,2,1)
            window.packet.change_geometry(1,2,2)
        elif lmst and gr and en and not nb and not td:
            window.sGLMST.change_geometry(2,2,2)
            window.sGgr.change_geometry(2,2,1)
            window.en.change_geometry(2,1,2)
        elif lmst and gr and not en and nb and not td:
            window.sGLMST.change_geometry(2,2,2)
            window.sGgr.change_geometry(2,2,1)
            window.nr.change_geometry(2,1,2)
        elif lmst and gr and not en and not nb and td:
            window.sGLMST.change_geometry(2,2,2)
            window.sGgr.change_geometry(2,2,1)
            window.packet.change_geometry(2,1,2)
        elif lmst and not gr and en and nb and not td:
            window.sGLMST.change_geometry(1,2,1)
            window.en.change_geometry(2,2,2)
            window.nr.change_geometry(2,2,4)
        elif lmst and not gr and en and not nb and td:
            window.sGLMST.change_geometry(1,2,1)
            window.en.change_geometry(2,2,2)
            window.packet.change_geometry(2,2,4)
        elif lmst and not gr and not en and nb and td:
            window.sGLMST.change_geometry(1,2,1)
            window.nr.change_geometry(2,2,2)
            window.packet.change_geometry(2,2,4)
        elif not lmst and gr and en and nb and not td:
            window.sGgr.change_geometry(1,2,1)
            window.en.change_geometry(2,2,2)
            window.nr.change_geometry(2,2,4)
        elif not lmst and gr and en and not nb and td:
            window.sGgr.change_geometry(1,2,1)
            window.en.change_geometry(2,2,2)
            window.packet.change_geometry(2,2,4)
        elif not lmst and gr and not en and nb and td:
            window.sGgr.change_geometry(1,2,1)
            window.nr.change_geometry(2,2,2)
            window.packet.change_geometry(2,2,4)   
        elif not lmst and not gr and en and nb and td:
            window.en.change_geometry(3,1,1)
            window.nr.change_geometry(3,1,2)
            window.packet.change_geometry(3,1,3)
        elif lmst and gr and en and nb and not td:
            window.sGLMST.change_geometry(2,2,2)
            window.sGgr.change_geometry(2,2,1)
            window.en.change_geometry(2,2,3)
            window.nr.change_geometry(2,2,4)
        elif lmst and gr and not en and nb and td:
            window.sGLMST.change_geometry(2,2,2)
            window.sGgr.change_geometry(2,2,1)
            window.nr.change_geometry(2,2,3)
            window.packet.change_geometry(2,2,4)
        elif lmst and gr and en and not nb and td:
            window.sGLMST.change_geometry(2,2,2)
            window.sGgr.change_geometry(2,2,1)
            window.en.change_geometry(2,2,3)
            window.packet.change_geometry(2,2,4)
        elif not lmst and gr and en and nb and td:
            window.sGgr.change_geometry(2,2,1)
            window.en.change_geometry(2,2,2)
            window.nr.change_geometry(2,2,3)
            window.packet.change_geometry(2,2,4)
        elif lmst and not gr and en and nb and td:
            window.sGLMST.change_geometry(2,2,1)
            window.en.change_geometry(2,2,2)
            window.nr.change_geometry(2,2,3)
            window.packet.change_geometry(2,2,4)
        elif lmst and gr and en and nb and td:
            window.sGLMST.change_geometry(2,2,2)
            window.sGgr.change_geometry(2,2,1)
            window.nr.change_geometry(2,3,4)
            window.en.change_geometry(2,3,5)
            window.packet.change_geometry(2,3,6)
        window.canvas.draw()