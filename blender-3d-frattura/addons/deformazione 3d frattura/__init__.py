
# PER INSTALLARE MODULI PYTHON SU BLENDER:
# >> "C:\Program Files\Blender Foundation\Blender 4.3\4.3\python\bin\python.exe" -m pip install -U pillow --target="C:\Users\Anna\AppData\Roaming\Blender Foundation\Blender\4.3\scripts\modules"
# dove il target path l'ho trovato scrivendo questo nella console di Blender:
# >> bpy.utils.user_resource("SCRIPTS", path="modules")
# e il primo parametro e' il percorso dell'installazione di python shippata insieme a blender, trovata eseguendo questo dentro blender:
'''
def python_exec():
    import os
    import bpy
    try:
        # 2.92 and older
        path = bpy.app.binary_path_python
    except AttributeError:
        # 2.93 and later
        import sys
        path = sys.executable
    return os.path.abspath(path)

print(python_exec())
'''


# PATH di python
# C:\Program Files\Blender Foundation\Blender 4.3\4.3\python\bin\python.exe

# per importare le librerie
#import sys
#sys.path.append('C:\\Users\\Anna\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages')
#sys.path.append('C:\\Users\\Anna\\AppData\\Roaming\\Python\\Python311\\site-packages')


import bpy
from bpy.app.handlers import persistent
import addon_utils
import bmesh


import math
import mathutils
import pickle
import numpy as np
import torch

import copy

# Classi e funzioni per ML definite negli altri file
from .ML_model import *
from .ML_utils import *



# PER SPOSTARE UN VERTICE:
# bpy.data.objects["plate"].data.vertices[0].co.x = 2.8


# PATH vari
PATH_WEIGHTS = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d-frattura\\addons\deformazione 3d frattura\\model_state_dict_frattura.pth"
PATH_NORM_VALUES_INPUT = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d-frattura\\addons\deformazione 3d frattura\\input_norm_values.pkl"
PATH_NORM_VALUES_TARGET = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d-frattura\\addons\deformazione 3d frattura\\target_norm_values.pkl"


# PARAMETRI
CIRCLE_OBJECT_NAME = "circle"
PLATE_OBJECT_NAME = "plate"
CIRCLE_DEFAULT_RADIUS = 2.5     # Cosi' lo scaling del cerchio lo calcoliamo in base a questo valore di default
TIME_TO_IMPACT = 0.5                # Quanti secondi vogliamo che ci metta la palla a raggiungere la lastra
TIME_TOTAL = 1                  # Quanti secondi vogliamo che duri l'animazione
FPS = 30

MARGIN_TRAJECTORY = 0.01       # margine che aggiungo alla traiettoria e che uso nel controllo della collisione

SCALING_PARAMETER = 10  
# Lo scaling parameter dovrebbe essere 1000, perche' in Abaqus abbiamo fatto tutto in millimetri e Blender usa i metri,
# ma e' scomodo lavorare con modelli troppo piccoli su Blender (la palla con raggio 1.5 mm per esempio) quindi
# dividiamo tutto per 10 invece di 1000

# Custom properties
CIRCLE_VELOCITY_PROPERTY_NAME = "velocity"
CIRCLE_VELOCITY_DEFAULT_VALUE = 4000
CIRCLE_VELOCITY_RANGE = [3000, 10000]

CIRCLE_ALPHA_Y_PROPERTY_NAME = "alpha_y"
CIRCLE_ALPHA_Y_DEFAULT_VALUE = 0
CIRCLE_ALPHA_Y_RANGE = [0, 60]  

CIRCLE_ALPHA_X_PROPERTY_NAME = "alpha_x"
CIRCLE_ALPHA_X_DEFAULT_VALUE = 0
CIRCLE_ALPHA_X_RANGE = [-180, 180]  

CIRCLE_RADIUS_PROPERTY_NAME = "radius"
CIRCLE_RADIUS_DEFAULT_VALUE = 3.0
CIRCLE_RADIUS_RANGE = [2, 4.5]

# Posiz iniziale coi valori di default (nota: in Blender, l'asse verticale e' la Z)
trajectory = abs(TIME_TO_IMPACT * CIRCLE_VELOCITY_DEFAULT_VALUE/SCALING_PARAMETER) + CIRCLE_RADIUS_DEFAULT_VALUE/SCALING_PARAMETER + MARGIN_TRAJECTORY

CIRCLE_DEFAULT_POSITION_Y = trajectory * math.cos(math.radians(CIRCLE_ALPHA_Y_DEFAULT_VALUE)) + CIRCLE_RADIUS_DEFAULT_VALUE
CIRCLE_DEFAULT_POSITION_X = - trajectory * math.sin(math.radians(CIRCLE_ALPHA_Y_DEFAULT_VALUE)) * math.cos(math.radians(CIRCLE_ALPHA_X_DEFAULT_VALUE))
CIRCLE_DEFAULT_POSITION_Z = - trajectory * math.sin(math.radians(CIRCLE_ALPHA_Y_DEFAULT_VALUE)) * math.sin(math.radians(CIRCLE_ALPHA_X_DEFAULT_VALUE))
CIRCLE_DEFAULT_POSITION = (CIRCLE_DEFAULT_POSITION_X, CIRCLE_DEFAULT_POSITION_Z, CIRCLE_DEFAULT_POSITION_Y)




bl_info = {
    "name": "Deformazione 3D Frattura",
    "author": "Anna",
    "description": "Menu",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Right 3d View Panel > Deformazione 3D Frattura",
    "category": "Object",
}


#** ON ADDON LOAD **#

@persistent
def load_handler(dummy):

    print("setting properties")
    bpy.context.scene.simulation_properties.reset()
    bpy.context.scene.machine_learning_properties.initialize()

    # Crea modello pytorch
    MachineLearningSingletonClass()



bpy.app.handlers.load_post.append(load_handler)




#****** Classe singleton per avere un'unica istanza del modello pytorch accessibile ovunque ******#


class MachineLearningSingletonClass(object):
  
    model = None

    norm_values_input = {
        "mean":[],
        "std":[]
    }

    norm_values_target = {
        "mean":[],
        "std":[]
    }

    def getModel(self):
        return self.model

    def getNormValuesInput(self):
        return self.norm_values_input
    
    def getNormValuesTarget(self):
        return self.norm_values_target
    
    def getInputSeqLength(self):
        return self.input_seq_len

    def initModel(self):

        print("creating model")

        if False: #torch.cuda.is_available():
            print("cuda available")
            self.device = "cuda"
        else:
            self.device = "cpu"
        
        # Crea modello ML
        self.input_seq_len = 98
        input_dim = 6  # Each input is a sequence of 3Dx2 points (x, y, z)
        d_model = 512  # Embedding dimension
        nhead = 4  # Number of attention heads
        num_encoder_layers = 4  # Number of transformer encoder layers
        dim_feedforward = 512  # Feedforward network dimension
        n_points = 2738   
        output_dim = n_points*3  # Each output is a 3D point (x, y, z)
        dropout = 0.0

        self.model = Transformer3DPointsModel(input_dim, self.input_seq_len, d_model, nhead, num_encoder_layers, dim_feedforward, output_dim, dropout).to(self.device)

        print("model created, loading weights")

        # Carica i pesi
        self.model.load_state_dict(torch.load(PATH_WEIGHTS, weights_only=True, map_location=torch.device('cpu')))

        print("weights loaded")

    def initNormValues(self):
        print("getting norm values")
        with open(PATH_NORM_VALUES_INPUT, 'rb') as input_file:
            self.norm_values_input = pickle.load(input_file)   
        with open(PATH_NORM_VALUES_TARGET, 'rb') as input_file:
            self.norm_values_target = pickle.load(input_file)   
        print("set norm values")

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(MachineLearningSingletonClass, cls).__new__(cls)
            cls.instance.initModel()
            cls.instance.initNormValues()
        return cls.instance




#******************* PROPERTIES *******************#

class SimulationProperties(bpy.types.PropertyGroup):

    velocity: bpy.props.IntProperty(
        name = CIRCLE_VELOCITY_PROPERTY_NAME,
        default = CIRCLE_VELOCITY_DEFAULT_VALUE,
        min = CIRCLE_VELOCITY_RANGE[0],
        max = CIRCLE_VELOCITY_RANGE[1],
        step=1
    )
    
    alpha_y: bpy.props.IntProperty(
        name = CIRCLE_ALPHA_Y_PROPERTY_NAME,
        default = CIRCLE_ALPHA_Y_DEFAULT_VALUE,
        min = CIRCLE_ALPHA_Y_RANGE[0],
        max = CIRCLE_ALPHA_Y_RANGE[1],
        step=1
    )

    alpha_x: bpy.props.IntProperty(
        name = CIRCLE_ALPHA_X_PROPERTY_NAME,
        default = CIRCLE_ALPHA_X_DEFAULT_VALUE,
        min = CIRCLE_ALPHA_X_RANGE[0],
        max = CIRCLE_ALPHA_X_RANGE[1],
        step=1
    )

    radius: bpy.props.FloatProperty(
        name = CIRCLE_RADIUS_PROPERTY_NAME,
        default = CIRCLE_RADIUS_DEFAULT_VALUE,
        min = CIRCLE_RADIUS_RANGE[0],
        max = CIRCLE_RADIUS_RANGE[1],
        step=0.1
    )

    def reset(self):
        self.velocity = CIRCLE_VELOCITY_DEFAULT_VALUE
        self.alpha_y = CIRCLE_ALPHA_Y_DEFAULT_VALUE
        self.alpha_x = CIRCLE_ALPHA_X_DEFAULT_VALUE
        self.radius = CIRCLE_RADIUS_DEFAULT_VALUE



class FloatValuePropertiesGroup(bpy.types.PropertyGroup):
    val : bpy.props.FloatProperty()


class MachineLearningProperties(bpy.types.PropertyGroup):

    
    mean: bpy.props.CollectionProperty(
        name = "mean",
        type = FloatValuePropertiesGroup
    )
    
    std: bpy.props.CollectionProperty(
        name = "std",
        type = FloatValuePropertiesGroup
    )

    def setMean(self, values):
        for v in values:
            fl = self.mean.add()
            fl.val = v

    def getMean(self):
        return [m.val for m in self.mean]
    
    def setStd(self, values):
        for v in values:
            fl = self.std.add()
            fl.val = v

    def getStd(self):
        return [m.val for m in self.std]


    def initialize(self):
        self.mean.clear()
        self.std.clear()
        with open('D:\\TESI\\Blender scripts\\norm_values.pkl', 'rb') as input_file:
            norm_values = pickle.load(input_file)   
            #print("norm values:")
            #print(norm_values)

            self.setMean(norm_values["mean"])
            self.setStd(norm_values["std"])

            #print("mean:")
            #print(self.getMean())




#******************* OPERATORI *******************#


class OT_print_properties(bpy.types.Operator):
    """Print properties"""

    bl_idname = "mesh.print_properties"
    bl_label = "Print"

    def execute(self, context):
        print("Velocity: " + str(context.scene.simulation_properties.velocity))
        print("Angle Y: " + str(context.scene.simulation_properties.alpha_y))
        print("Angle X: " + str(context.scene.simulation_properties.alpha_x))
        print("Radius: " + str(context.scene.simulation_properties.radius))

        print("pytorch model:")
        print(MachineLearningSingletonClass().getModel())

        return {"FINISHED"}



class OT_reset_all(bpy.types.Operator):
    """Reset simulation"""

    bl_idname = "mesh.reset_all"
    bl_label = "Reset simulation"

    def execute(self, context):

        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]
        plate = bpy.data.objects[PLATE_OBJECT_NAME]

        # Seleziona il primo frame
        context.scene.frame_set(1)

        # Elimina animazione
        circle.animation_data_clear()

        # Ripristina posizione e scala iniziali
        circle.location = CIRCLE_DEFAULT_POSITION
        circle.scale = (1, 1, 1)

        # Ripristina valori di default
        #context.scene.simulation_properties.reset()

        # Ripristina posizioni nodi della lastra
        print("resetting plate vertices")
        for i in range(0, len(plate.data.vertices)):
            plate.data.vertices[i].co.x = plate.data["vertices_initial"][str(i)][0]
            plate.data.vertices[i].co.y = plate.data["vertices_initial"][str(i)][1]
            plate.data.vertices[i].co.z = plate.data["vertices_initial"][str(i)][2]

        return {"FINISHED"}



# Operatore per riprodurre l'animazione ed eseguire codice ad ogni frame
class OT_play_animation(bpy.types.Operator):
    """Operator which runs itself from a timer"""
    bl_idname = "wm.play_animation"
    bl_label = "Modal Timer Operator"

    _timer = None

    next_frame = 0      # cosi' ricomincio poi da 1

    # Per il movimento della palla
    displacement_x = 0
    displacement_y = 0
    displacement_z = 0

    # Per lo scaling
    circle_scaling = 1  # salvo qua perche' mi serve anche in compute displacements
    circle_origin_x = 0
    circle_origin_y = 0
    circle_origin_z = 0

    has_collided = False

    # Coordinate al frame prima
    circle_prev_coordinates_1 = []

    # Coordinate due frame prima
    circle_prev_coordinates_2 = []

    # per quando e' a 60 fps
    # invece di usare 1 e 2, uso 1 e 3 (non 2 e 4, perche' a 60 fps la collisione viene rilevata 1 frame prima - cioe' mezzo frame prima a 30 FPS,
    # quindi bisogna sfasarlo di un frame a 60 FPS)
    circle_prev_coordinates_3 = []


    circle_prev_coordinates_1_precomputed = []
    circle_prev_coordinates_2_precomputed = []


    def __init__(self):

        if False: #torch.cuda.is_available():
            self.device = "cuda"
            self.using_cuda = True
            print("using cuda!")
        else:
            self.device = "cpu"
            self.using_cuda = False



        ## ********************************************************************************************************************** ##
        # TEMP: carico i vertici degli edge rimossi da file
        edgesToRemoveFilename = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d-frattura\\addons\\plate_surface_vertices_removed_info.txt"
        self.vertices_removed_info = []
        with open(edgesToRemoveFilename, mode="r") as edgesFile:
            for line in edgesFile:
                line = line.strip()
                lineArray = line.split(",")
                self.vertices_removed_info.append(int(lineArray[0]))
    
        ## ********************************************************************************************************************** ##


    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'} or self.next_frame > TIME_TOTAL*FPS:
            self.next_frame = 0
            self.cancel(context)
            return {'FINISHED'}

        if event.type == 'TIMER':
            circle = bpy.data.objects[CIRCLE_OBJECT_NAME]
            plate = bpy.data.objects[PLATE_OBJECT_NAME]

            # muovi cerchio
            self.move_circle(context, self.displacement_x, self.displacement_y, self.displacement_z)


            # se c'e' la collisione
            if ( (not self.has_collided) and self.checkCollision(context)):

                with torch.autograd.profiler.profile(use_cuda=self.using_cuda) as prof:

                    self.has_collided = True
                    print("applying displacement on frame " + str(self.next_frame))

                    # prendo coordinate
                    if (FPS == 60):
                        init_coords_circle_data = np.array(self.circle_prev_coordinates_3) 
                        before_coords_data = np.array(self.circle_prev_coordinates_1) 
                    else:
                        init_coords_circle_data = np.array(self.circle_prev_coordinates_2)    
                        before_coords_data = np.array(self.circle_prev_coordinates_1)           

                    ### TEMP
                    '''
                    circle_obj = context.scene.objects[CIRCLE_OBJECT_NAME]
                    circle_world_matrix = circle_obj.matrix_world.copy()
                    new_before_coords_data = []
                    for vert in circle.data.vertices:
                        vert_global = circle_world_matrix @ vert.co
                        new_before_coords_data.append([vert_global[0]*SCALING_PARAMETER, vert_global[2]*SCALING_PARAMETER, vert_global[1]*SCALING_PARAMETER])
                    before_coords_data = np.array(new_before_coords_data)  
                    '''
                    ###

                    ### TEMP
                    init_coords_circle_data = np.array(self.circle_prev_coordinates_1_precomputed) 
                    before_coords_data = np.array(self.circle_prev_coordinates_2_precomputed) 
                    ###

                    print("init coords circle")
                    print(init_coords_circle_data[:4])
                    print("before coords circle")
                    print(before_coords_data[:4])

                    # trasformo coordinate in tensori
                    init_coords_circle_data = torch.tensor(init_coords_circle_data).float()
                    before_coords_data = torch.tensor(before_coords_data).float()

                    total_data = torch.cat((init_coords_circle_data,before_coords_data),1)
                    padding = MachineLearningSingletonClass().getInputSeqLength()
                    if (padding is not None) and total_data.shape[0]<padding:
                        total_data = zero_pad_tensor(total_data,target_size=padding)

                    # normalizzo:
                    total_data = normalize_targets(total_data, MachineLearningSingletonClass().getNormValuesInput())
                    total_data = total_data.to(self.device)
                    total_data = total_data[None, :, :]

                    print("chiamo modello ML")

                    # passo in input alla rete neurale
                    predicted_displacements,_ = self.model(total_data,None)

                    # de-normalizzo:
                    predicted_displacements = denormalize_targets(predicted_displacements, MachineLearningSingletonClass().getNormValuesTarget())
                    predicted_displacements = predicted_displacements.cpu().detach().numpy()
                    predicted_displacements = predicted_displacements.reshape(-1,3)

                    self.displacements = predicted_displacements
                    
                    #print("predicted displacements:")
                    #print(predicted_displacements)


                    ## ********************************************************************************************************************** ##
                    

                    #'''
                    # TEMP: applico i displacement da file
                    i = 0
                    for val in self.displacements:
                        plate.data.vertices[i].co.x += float(val[0])/SCALING_PARAMETER
                        plate.data.vertices[i].co.y += float(val[2])/SCALING_PARAMETER
                        plate.data.vertices[i].co.z += float(val[1])/SCALING_PARAMETER
                        i += 1
                    #'''


                    # vertici che devono perdere un edge:
                    plate_vertices_that_lost_an_edge = []

                    i = 1   # gli indici dei vertici in blender partono da 1
                    for val in self.vertices_removed_info:
                        if (val == 1):
                            plate_vertices_that_lost_an_edge.append(i)
                        i += 1


                    # Se non ci sono vertici che perdono un edge, tutta la parte dopo non serve
                    if False: #(len(plate_vertices_that_lost_an_edge) >= 3):          # 3 perche' rimuovo una faccia solo se almeno 3 suoi vertici sono nella lista

                        # vertici a cui dovro' ricostruire gli edge
                        plate_vertices_that_need_new_edges = []


                        # rimuovo le facce che hanno almeno tre vertici tra quelli che perdono un edge
                        bpy.context.view_layer.objects.active = plate
                        bpy.ops.object.mode_set(mode='EDIT')

                        me = plate.data
                        bm = bmesh.from_edit_mesh(me)
                        bm.verts.ensure_lookup_table()
                        bm.edges.ensure_lookup_table()
                        bm.faces.ensure_lookup_table()

                        plate_faces = [[[vert.index for vert in face.verts], face] for face in bm.faces]

                        faces_to_be_deleted = []
                        
                        for face in plate_faces:
                            how_many_vertices_in_list = 0
                            for i in range(0, len(face[0])):
                                if (face[0][i] in plate_vertices_that_lost_an_edge):
                                    how_many_vertices_in_list += 1
                            if (how_many_vertices_in_list >= 3):
                                faces_to_be_deleted.append(face[1])
                                plate_vertices_that_need_new_edges += face[0]       # concateno i vertici di questa faccia alla lista


                        # Aggiorna mesh
                        bmesh.update_edit_mesh(me)    

                        # Creo nuovi edge cercandoli nella lista di tutti gli edge
                        plate_all_edges = plate.data["edges_all"]
                        
                        # i nuovi edge da creare sono quelli dentro plate_all_edges che hanno entrambi i vertici tra i vertici a cui e' stato eliminato un edge,
                        # ma al tempo stesso non deve essere stato eliminato un edge proprio tra quei due vertici (se no lo starei andando a ri aggiungere)

                        # scorro tutti gli edge e controllo quelli che contengono entrambi i vertici dentro plate_vertices_that_lost_an_edge ma che non sono in self.edges_to_remove:
                        bm.verts.ensure_lookup_table()
                        for edge in plate_all_edges:
                            if (edge[0] in plate_vertices_that_need_new_edges and edge[1] in plate_vertices_that_need_new_edges):
                                # Creo il nuovo edge solo se non esiste:
                                if not(set(bm.verts[edge[0]].link_edges) & set(bm.verts[edge[1]].link_edges)):
                                    #print(f"({edge[0]},{edge[1]})")
                                    bm.edges.new((bm.verts[edge[0]], bm.verts[edge[1]]))
                        

                        # solo ora elimino le facce, se lo faccio prima mi incasina gli indici
                        bmesh.ops.delete(bm, geom=faces_to_be_deleted, context='FACES')

                        # Aggiorna mesh
                        bmesh.update_edit_mesh(me)     

                        # Elimino i vertici che non hanno nessuna faccia
                        vertices_to_be_deleted = [v for v in bm.verts if not v.link_faces]
                        print("going to delete vertices:")
                        print(vertices_to_be_deleted)
                        bmesh.ops.delete(bm, geom=vertices_to_be_deleted, context='VERTS')

                        # Aggiorna mesh
                        #bmesh.update_edit_mesh(me)     

                        #'''
                        # Crea nuove facce
                        bpy.ops.mesh.select_mode(type="VERT")
                        bpy.ops.mesh.select_all(action = 'SELECT')
                        bpy.ops.mesh.edge_face_add()    # Crea facce

                        # Aggiorna mesh
                        bmesh.update_edit_mesh(me)    

                        #'''
                        
                        bpy.ops.object.mode_set(mode='OBJECT')



                    ## ********************************************************************************************************************** ##



                #print("elapsed time:")
                #print(prof)
            

            # prendo la world matrix dell'oggetto, i vertici vanno moltiplicati per quella se no ottengo
            # solo le posizioni locali ignorando i displacement e scaling
            circle_obj = context.scene.objects[CIRCLE_OBJECT_NAME]
            circle_world_matrix = circle_obj.matrix_world.copy()

            # Aggiorna posizioni frame precedenti
            if (FPS == 60):
                self.circle_prev_coordinates_3 = copy.deepcopy(self.circle_prev_coordinates_2)
            self.circle_prev_coordinates_2 = copy.deepcopy(self.circle_prev_coordinates_1)

            self.circle_prev_coordinates_1 = []
            for vert in circle.data.vertices:
                vert_global = circle_world_matrix @ vert.co
                # inverto la y e la z perche' in blender la z e' l'asse verticale, quello che in abaqus era la y
                # e moltiplico le coordinate per lo scaling parameter perche' prima le avevo divise
                self.circle_prev_coordinates_1.append([vert_global[0]*SCALING_PARAMETER, vert_global[2]*SCALING_PARAMETER, vert_global[1]*SCALING_PARAMETER])

            self.next_frame += 1

        return {'PASS_THROUGH'}

    def execute(self, context):
        self.reset(context)
        self.has_collided = False

        self.model = MachineLearningSingletonClass().getModel()

        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]

        # Valori velocita' raggio e angolo
        velocity = context.scene.simulation_properties.velocity / SCALING_PARAMETER
        alpha_y = context.scene.simulation_properties.alpha_y
        alpha_x = context.scene.simulation_properties.alpha_x
        radius = context.scene.simulation_properties.radius / SCALING_PARAMETER

        # Applica scaling al cerchio
        self.circle_scaling = context.scene.simulation_properties.radius / CIRCLE_DEFAULT_RADIUS
        circle.scale = (self.circle_scaling, self.circle_scaling, self.circle_scaling)

        # Lunghezza traiettoria
        trajectory = abs(TIME_TO_IMPACT * velocity) + radius #+ MARGIN_TRAJECTORY

        # Posiz iniziale
        self.circle_origin_y = trajectory * math.cos(math.radians(alpha_y)) + radius
        self.circle_origin_x = - trajectory * math.sin(math.radians(alpha_y)) * math.cos(math.radians(alpha_x))
        self.circle_origin_z = - trajectory * math.sin(math.radians(alpha_y)) * math.sin(math.radians(alpha_x))

        # Calcola spostamenti
        self.displacement_y = -velocity*math.cos(math.radians(alpha_y))/FPS
        self.displacement_x = velocity*math.sin(math.radians(alpha_y)) * math.cos(math.radians(alpha_x)) / FPS
        self.displacement_z = velocity*math.sin(math.radians(alpha_y)) * math.sin(math.radians(alpha_x)) / FPS

        # TEMP
        self.preComputeCoordinates(self.displacement_x, self.displacement_y, self.displacement_z)

        # Imposta posizione iniziale cerchio
        circle.location = (self.circle_origin_x, self.circle_origin_z, self.circle_origin_y)

        # prendo la world matrix dell'oggetto, i vertici vanno moltiplicati per quella se no ottengo
        # solo le posizioni locali ignorando i displacement e scaling
        circle_obj = context.scene.objects[CIRCLE_OBJECT_NAME]
        circle_world_matrix = circle_obj.matrix_world.copy()

        # Inizializza posizioni frame precedenti
        self.circle_prev_coordinates_1 = []
        for vert in circle.data.vertices:
            vert_global = circle_world_matrix @ vert.co
            self.circle_prev_coordinates_1.append([vert_global[0]*SCALING_PARAMETER, vert_global[2]*SCALING_PARAMETER, vert_global[1]*SCALING_PARAMETER])
        
        self.circle_prev_coordinates_2 = self.circle_prev_coordinates_1
        self.circle_prev_coordinates_3 = self.circle_prev_coordinates_1

        # Avvia operatore
        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=1/FPS, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def preComputeCoordinates(self, displacement_x, displacement_y, displacement_z):
        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]

        circle_world_matrix_1 = mathutils.Matrix()      # senza parametri genera una matrice identita' 4x4
        circle_world_matrix_2 = mathutils.Matrix()

        # metto la posizione iniziale
        circle_world_matrix_1[0][3] = self.circle_origin_x
        circle_world_matrix_1[1][3] = self.circle_origin_z
        circle_world_matrix_1[2][3] = self.circle_origin_y

        circle_world_matrix_2[0][3] = self.circle_origin_x
        circle_world_matrix_2[1][3] = self.circle_origin_z
        circle_world_matrix_2[2][3] = self.circle_origin_y


        #print("world matrix prima di spostamenti previsti:")
        #print(circle_world_matrix_1)

        incr_1 = 13
        incr_2 = 14
        if (FPS == 60):
            incr_1 = 27
            incr_2 = 29
        
        # metto i displacements
        circle_world_matrix_1[0][3] += displacement_x*incr_1
        circle_world_matrix_1[1][3] += displacement_z*incr_1
        circle_world_matrix_1[2][3] += displacement_y*incr_1

        circle_world_matrix_2[0][3] += displacement_x*incr_2
        circle_world_matrix_2[1][3] += displacement_z*incr_2
        circle_world_matrix_2[2][3] += displacement_y*incr_2

        # metto lo scaling
        circle_world_matrix_1[0][0] = self.circle_scaling
        circle_world_matrix_1[1][1] = self.circle_scaling
        circle_world_matrix_1[2][2] = self.circle_scaling

        circle_world_matrix_2[0][0] = self.circle_scaling
        circle_world_matrix_2[1][1] = self.circle_scaling
        circle_world_matrix_2[2][2] = self.circle_scaling

        
        print("matrix 1:")
        print(circle_world_matrix_1)
        print("matrix 2:")
        print(circle_world_matrix_2)

        for vert in circle.data.vertices:

            vert_global_1 = circle_world_matrix_1 @ vert.co
            self.circle_prev_coordinates_1_precomputed.append([vert_global_1[0]*SCALING_PARAMETER, vert_global_1[2]*SCALING_PARAMETER, vert_global_1[1]*SCALING_PARAMETER])

            vert_global_2 = circle_world_matrix_2 @ vert.co
            self.circle_prev_coordinates_2_precomputed.append([vert_global_2[0]*SCALING_PARAMETER, vert_global_2[2]*SCALING_PARAMETER, vert_global_2[1]*SCALING_PARAMETER])

        print("precomputed coordinates 1:")
        print(self.circle_prev_coordinates_1_precomputed[:4])
        print("precomputed coordinates 2:")
        print(self.circle_prev_coordinates_2_precomputed[:4])


    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)


    def checkCollision(self, context):
        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]
        radius = context.scene.simulation_properties.radius / SCALING_PARAMETER

        if (circle.location.z <= radius + MARGIN_TRAJECTORY):
            #print("collisione, posizione:")
            #print(circle.location.z)
            return True
        return False


    def move_circle(self, context, displacement_x, displacement_y, displacement_z):
        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]

        # Muovi cerchio
        circle.location.x += displacement_x
        circle.location.z += displacement_y
        circle.location.y += displacement_z


    def reset(self, context):
        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]
        plate = bpy.data.objects[PLATE_OBJECT_NAME]

        # Ripristina scala e posizione iniziali
        circle.location = CIRCLE_DEFAULT_POSITION
        circle.scale = (1, 1, 1)

        # Ripristina posizioni nodi della lastra
        print("resetting plate vertices")
        for i in range(0, len(plate.data.vertices)):
            plate.data.vertices[i].co.x = plate.data["vertices_initial"][str(i)][0]
            plate.data.vertices[i].co.y = plate.data["vertices_initial"][str(i)][1]
            plate.data.vertices[i].co.z = plate.data["vertices_initial"][str(i)][2]


#******************* UI *******************#


class MainPanel(bpy.types.Panel):
    bl_label = "Frattura 3D"
    bl_idname = "ANNA_PT_Simulation_Options_Frattura_3D_Main_Panel"  # deve essere diverso per ogni classe
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Simulation Options - Frattura 3D"

    def draw(self, context):

        layout = self.layout
        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]
 
        #row = layout.row()
        #row.label(text="Animation")
        #layout.separator()
        
        col = layout.column(align=True)
        
        # Slider velocita'
        col.prop(context.scene.simulation_properties, "velocity", text="Circle velocity", slider=True)
        col.separator()

        # Slider angolo y
        col.prop(context.scene.simulation_properties, "alpha_y", text="Circle Y angle", slider=True)
        col.separator()

        # Slider angolo x
        col.prop(context.scene.simulation_properties, "alpha_x", text="Circle X angle", slider=True)
        col.separator()

        # Slider raggio 
        col.prop(context.scene.simulation_properties, "radius", text="Circle radius", slider=True)
        col.separator()

        # Pulsante stampa
        col.operator("mesh.print_properties", text="Print values")

        layout.separator()

        row = layout.row()
        row.operator("mesh.reset_all", text="Reset")

        layout.separator()

        # Pulsante play
        row = layout.row()
        row.operator("wm.play_animation", text="Play")



    
def register():
    
    # Registra UI
    bpy.utils.register_class(MainPanel)

    # Registra proprieta'
    bpy.utils.register_class(SimulationProperties)
    bpy.utils.register_class(FloatValuePropertiesGroup)
    bpy.utils.register_class(MachineLearningProperties)

    # Registra operatori
    bpy.utils.register_class(OT_reset_all)
    bpy.utils.register_class(OT_print_properties)
    bpy.utils.register_class(OT_play_animation)


    # Crea proprieta' simulazione
    bpy.types.Scene.simulation_properties = bpy.props.PointerProperty(type=SimulationProperties)
    #bpy.types.Scene.simulation_properties = bpy.props.CollectionProperty(type=SimulationProperties)
    
    # Crea proprieta' machine learning
    bpy.types.Scene.machine_learning_properties = bpy.props.PointerProperty(type=MachineLearningProperties)

    print("///// addon activated /////")


def unregister():
    bpy.utils.unregister_class(MainPanel)

    bpy.utils.unregister_class(SimulationProperties)
    bpy.utils.unregister_class(FloatValuePropertiesGroup)
    bpy.utils.unregister_class(MachineLearningProperties)

    bpy.utils.unregister_class(OT_reset_all)
    bpy.utils.unregister_class(OT_print_properties)
    bpy.utils.unregister_class(OT_play_animation)

    print("///// addon deactivated /////")


if __name__ == "__main__":
    register()


