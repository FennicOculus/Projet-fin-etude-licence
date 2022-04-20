import tkinter as tk
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from controle import controle
from matplotlib import style
style.use('ggplot')
import os
from PIL import Image, ImageTk


class vue(tk.Tk):#herite de tkinter

    def __init__(self,*args,**kwargs):
        tk.Tk.__init__(self,*args,**kwargs)
        self.option_readfile('style')#le style
        #frame initial (entré nombre noeuds)
        self.frame_initial=tk.Frame(self)
        self.frame_initial.pack(side='top',fill=tk.BOTH,expand=True)
        self.frames={}
        self.f_act=None
        self.ajouter_frame_init(entrer)
        self.cont=controle()#create controle
        self.wm_protocol('WM_DELETE_WINDOW',lambda : self.cont.fermer_fen(self))



    def ajouter_frame_init(self,classe_f,**args):
        if self.f_act!=None:
            self.f_act.destroy()
        frame=classe_f(self.frame_initial,self,**args)
        frame.grid(row=0,column=0)
        self.frames[classe_f]=frame
        self.f_act=frame
        self.f_act.tkraise()

    def refresh(self):
        self.frame
    def ajouter_frame_Sim(self,nb_node):
        self.ajouter_frame_init(Sim,nb_node=nb_node)
        return self.frames[Sim]
        
    def ajouter_frame_entrer(self):
        self.ajouter_frame_init(entrer)

class entrer(tk.Frame):
    
    def __init__(self,master,window):
        tk.Frame.__init__(self,master)
        self.pack()
        #reglage de la fenetre
        self.window=window
        self.window.resizable(False,False)
        self.window.title("Réglage des paramètres d'implémentation")
        #le titre
        Head=tk.Label(self,text="Implémentation du protocole de contrôle de topologie \n basé DUTY CYCLING")
        Head.pack(side='top')
        #le frame de donnee
        donnée=tk.LabelFrame(self,text="Les données")
        #le nombre des noeuds
        tk.Label(donnée,text="nombres \n de nœuds").grid(row=0,column=0,sticky='w')
        self.nb_node=tk.IntVar()
        self.entre_nb_node=tk.Entry(donnée,textvariable=self.nb_node)
        self.entre_nb_node.focus_set()
        self.entre_nb_node.grid(row=0,column=1,sticky='w')
        #la surface de deploiement

        donnée.pack()
        #le bouton de lancement de l'application
        button_frame=tk.Frame(self)
        button_frame.pack(padx=25,pady=(0,15),anchor='s')
        tk.Button(button_frame,text='Lancer la simulation',default='active',\
                                        command=lambda : self.window.cont.controlancemSim(self.nb_node,self.window)).pack(side=tk.LEFT,pady='2m',padx="2m")
        
class Sim(tk.Frame):
    
    def __init__(self,master,window,**args):
        #scrollbar
        #canvas=tk.Canvas(master)
        #scrollbar = tk.Scrollbar(canvas,command=canvas.yview)
        #scrollbar.pack(side=tk.RIGHT,fill=tk.Y)
        #canvas.configure(yscrollcommand = scrollbar.set)
        #canvas.bind('<Configure>', 'on_configure')
        #canvas.pack()
        tk.Frame.__init__(self,master)
        #canvas.create_window((4,4), window=self, anchor='nw')
        self.pack()
        self.window=window
        self.window.resizable(True,True)
        self.window.title("Protocole Duty Cycling")
        #le menu
        self.creation_menu()

        load = Image.open("sommaire1.png")
        render = ImageTk.PhotoImage(load)
        img = tk.Label(master, image=render)
        img.image = render
        img.place(rely=0.0, relx=1.0, x=0, y=645, anchor='se')
        
        #le titre
        Head=tk.Label(self,text="Implémentation de protocole de contrôle de topologie  basé Duty Cycling")
        Head.pack(side='top')
        sous_titre=tk.Label(self,\
                            text="pour les paramètres suivants:  nombre de nœuds = {}".format(args['nb_node']))
        sous_titre.pack(side='top')
        self.f = plt.figure(figsize=(19,8.75))
        #f.subplots_adjust(bottom=0.025, left=0.025, top = 0.956, right=0.965,wspace=1,hspace=1)
        self.sGLMST = self.f.add_subplot(2,2,2)
        self.sGgr = self.f.add_subplot(2,2,1)
        self.nr = self.f.add_subplot(2,3,4)
        self.colorbar = self.f.add_axes([0.01, 0.5, 0.01, 0.40])
        self.nr.set_ylim([-0.5,args['nb_node']+1])
        #self.nr.axes([-0.5,None,-0.5,args['nb_node']+1])
        self.en = self.f.add_subplot(2,3,5)
        self.packet = self.f.add_subplot(2, 3, 6)
        self.packet.set_visible(False)
        #self.en.axes([-0.5,None,-0.5,args['nb_node']*0.5+1])
        plt.axis('on')
        #plt.tight_layout(h_pad=0.125,w_pad=5)
        self.canvas = FigureCanvasTkAgg(self.f, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.pack(side=tk.TOP)
        self.toolbar.update()
        self.toolbar.pack_forget()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)



        self.invoke()
        
    def creation_menu(self):
        frame_menu=tk.Frame(self,relief=tk.RAISED, borderwidth=2)
        frame_menu.pack(side=tk.TOP,fill=tk.X)
        #menu execution
        self.Exec=tk.Menubutton(frame_menu, text='', underline=0)
        self.Exec.pack(side=tk.LEFT, padx="2m")
        self.Exec.menu = tk.Menu(self.Exec)
        self.Exec.menu.add('separator')
        self.Exec.menu.add_command(label="Quitter la simulation", command=lambda : self.window.cont.annulerSim(self.window))
        self.Exec['menu'] = self.Exec.menu
        #menu Affichage      
        self.Aff = tk.Menubutton(frame_menu, text='Affichage', underline=0)
        self.Aff.pack(side=tk.LEFT, padx="2m")
        self.Aff.menu = tk.Menu(self.Aff)
        self.Aff.choiG = tk.Menu(self.Aff.menu)
        self.gLMST = tk.BooleanVar()
        self.gGr = tk.BooleanVar()
        self.Aff.choiG.add_checkbutton(label='DUTY CYCLING', variable=self.gLMST, onvalue=True, offvalue=False,
                                       command=lambda: self.window.cont.ajouterDC(self))
        self.Aff.choiG.add_checkbutton(label='Générale', variable=self.gGr, onvalue=True, offvalue=False,
                                       command=lambda: self.window.cont.ajouterGr(self))
        self.Aff.menu.add_cascade(label='graphe de topologie', menu=self.Aff.choiG)
        self.Aff.choiP = tk.Menu(self.Aff.menu)
        self.gEn = tk.BooleanVar()
        self.gNb = tk.BooleanVar()
        self.gTD = tk.BooleanVar()
        self.Aff.choiP.add_checkbutton(label='Énergie Restante', variable=self.gEn, onvalue=True, offvalue=False,
                                       command=lambda: self.window.cont.ajouterEn(self))
        self.Aff.choiP.add_checkbutton(label='Nœuds Vivants', variable=self.gNb, onvalue=True, offvalue=False,
                                       command=lambda: self.window.cont.ajouterNb(self))
        self.Aff.menu.add_cascade(label='graphe de performance', menu=self.Aff.choiP)
        self.Aff['menu'] = self.Aff.menu
        #menu fichier trace
        self.fichTrac=tk.Menubutton(frame_menu, text='', underline=0)
        self.fichTrac.pack(side=tk.LEFT, padx="2m")
        self.fichTrac.menu = tk.Menu(self.fichTrac)
        self.fichTrac.menu.add_command(label="exécution DUTY CYCLING", command=lambda : self.window.cont.voireExecLMST(self))
        self.fichTrac.menu.add_command(label="exécution Générale", command=lambda : self.window.cont.voireExecGr(self))
        self.fichTrac['menu']=self.fichTrac.menu

    def invoke(self):
        self.Aff.choiG.invoke(self.Aff.choiG.index('DUTY CYCLING'))
        self.Aff.choiG.invoke(self.Aff.choiG.index('Générale'))
        self.Aff.choiP.invoke(self.Aff.choiP.index('Énergie Restante'))
        self.Aff.choiP.invoke(self.Aff.choiP.index('Nœuds Vivants'))
                
if __name__=='__main__':#entry point
    app=vue()#appelle a l'application
    #app.geometry('1270x980')
    app.mainloop()#tkinter main loop
    app.quit()
    os._exit(0)
