
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
import pickle
import numpy as np
import torch

# Classi e funzioni per ML definite negli altri file
from .ML_model import *
from .ML_utils import *



# PER SPOSTARE UN VERTICE:
# bpy.data.objects["plate"].data.vertices[0].co.x = 2.8


# PATH vari
PATH_WEIGHTS = "D:\\TESI\\Blender scripts\\model_weights.pth"


# PARAMETRI
CIRCLE_OBJECT_NAME = "circle"
PLATE_OBJECT_NAME = "plate"
CIRCLE_DEFAULT_RADIUS = 2.5     # Cosi' lo scaling del cerchio lo calcoliamo in base a questo valore di default
TIME_TO_IMPACT = 0.5                # Quanti secondi vogliamo che ci metta la palla a raggiungere la lastra
TIME_TOTAL = 1                  # Quanti secondi vogliamo che duri l'animazione
FPS = 60

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

    '''
    # Crea modello ML
    print("creating model")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    input_seq_len = 72
    input_dim = 4  # Each input is a sequence of 2Dx2 points (x, y)
    d_model = 512  # Embedding dimension
    nhead = 4  # Number of attention heads
    num_encoder_layers = 4  # Number of transformer encoder layers
    dim_feedforward = 512  # Feedforward network dimension
    output_dim = 280  # Each output is a 2D point (x, y)
    dropout = 0.0
    TRANSFORMER_MODEL = Transformer2DPointsModel(input_dim, input_seq_len, d_model, nhead, num_encoder_layers, dim_feedforward, output_dim, dropout).to(device)
    print("model created, loading weights")
    TRANSFORMER_MODEL.load_state_dict(torch.load(PATH_WEIGHTS, weights_only=True, map_location=torch.device('cpu')))
    print("weights loaded")
    '''


bpy.app.handlers.load_post.append(load_handler)




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
        print("Angle: " + str(context.scene.simulation_properties.alpha))
        print("Radius: " + str(context.scene.simulation_properties.radius))
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

    next_frame = 1      # cosi' ricomincio poi da 1

    # Per il movimento della palla
    displacement_x = 0
    displacement_z = 0

    has_collided = False

    # Coordinate al frame prima
    circle_prev_coordinates_1 = []

    # Coordinate due frame prima
    circle_prev_coordinates_2 = []

    # per quando e' a 60 fps
    # invece di usare 1 e 2, uso 1 e 3 (non 2 e 4, perche' a 60 fps la collisione viene rilevata 1 frame prima - cioe' mezzo frame prima a 30 FPS,
    # quindi bisogna sfasarlo di un frame a 60 FPS)
    circle_prev_coordinates_3 = []


    def __init__(self):

        print("creating model")

        if torch.cuda.is_available():
            self.device = "cuda"
            self.using_cuda = True
        else:
            self.device = "cpu"
            self.using_cuda = False

        # Crea modello ML
        self.input_seq_len = 72
        input_dim = 4  # Each input is a sequence of 2Dx2 points (x, y)
        d_model = 512  # Embedding dimension
        nhead = 4  # Number of attention heads
        num_encoder_layers = 4  # Number of transformer encoder layers
        dim_feedforward = 512  # Feedforward network dimension
        output_dim = 280  # Each output is a 2D point (x, y)
        dropout = 0.0
        self.model = Transformer2DPointsModel(input_dim, self.input_seq_len, d_model, nhead, num_encoder_layers, dim_feedforward, output_dim, dropout).to(self.device)
        
        print("model created, loading weights")

        # Carica i pesi
        self.model.load_state_dict(torch.load(PATH_WEIGHTS, weights_only=True, map_location=torch.device('cpu')))

        print("weights loaded")


        ## ********************************************************************************************************************** ##
        # TEMP: carico i displacement da file
        displacementsFilename = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d-frattura\\addons\\output_displacement_external.csv"
        self.displacements = []
        with open(displacementsFilename, mode="r") as displacementsFile:
            reader = csv.reader(displacementsFile)
            next(reader) #skip header
            #line e' cosi': [Id, X_Disp, Y_Disp, Z_Disp], in blender la z e' l'asse verticale di default quindi inverto y e z
            for line in reader:
                self.displacements.append((float(line[1]), float(line[3]), float(line[2])))

        # TEMP: carico gli edge da rimuovere da file
        edgesToRemoveFilename = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d-frattura\\plate_surface_removed_edges.txt"
        self.edges_to_remove = []
        with open(edgesToRemoveFilename, mode="r") as edgesFile:
            for line in edgesFile:
                line = line.strip()
                lineArray = line.split(",")
                self.edges_to_remove.append((int(lineArray[0]), int(lineArray[1])))
    
        ## ********************************************************************************************************************** ##


    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'} or self.next_frame > TIME_TOTAL*FPS:
            self.next_frame = 1
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


                    '''
                    # trasformo coordinate in tensore
                    if (FPS == 60):
                        init_coords_circle_data = np.array(self.circle_prev_coordinates_3) 
                    else:
                        init_coords_circle_data = np.array(self.circle_prev_coordinates_2)             
                    #print("init coords circle data")
                    #print(init_coords_circle_data)
                    init_coords_circle_data = torch.tensor(init_coords_circle_data).float()

                    if (FPS == 60):
                        before_coords_data = np.array(self.circle_prev_coordinates_1) 
                    else:
                        before_coords_data = np.array(self.circle_prev_coordinates_1)  
                    #print("before coords circle data")
                    #print(before_coords_data)
                    before_coords_data = torch.tensor(before_coords_data).float()

                    total_data = torch.cat((init_coords_circle_data,before_coords_data),1)
                    padding = self.input_seq_len
                    if padding is not None:
                        total_data = zero_pad_tensor(total_data,target_size=padding)
                    
                    images = total_data
                    images = images.to(self.device)
                    images = images[None, :, :]

                    print("chiamo modello ML")

                    # passo in input alla rete neurale
                    predicted_displacements = self.model(images,None)

                    # de-normalizzo:
                    norm_values = {
                        "mean":context.scene.machine_learning_properties.getMean(),
                        "std":context.scene.machine_learning_properties.getStd()
                    }
                    predicted_displacements = denormalize_targets(predicted_displacements,norm_values)
                    
                    predicted_displacements = predicted_displacements.cpu().detach().numpy()
                    predicted_displacements = predicted_displacements.reshape(-1,2)

                    #print("predicted displacements:")
                    #print(predicted_displacements)

                    # applico i displacement
                    i = 0
                    for val in predicted_displacements:
                        plate.data.vertices[i].co.x += float(val[0])/SCALING_PARAMETER
                        plate.data.vertices[i].co.z += float(val[1])/SCALING_PARAMETER
                        i += 1
                    '''
                    
                    ## ********************************************************************************************************************** ##
                    

                    #'''
                    # TEMP: applico i displacement da file
                    i = 0
                    for val in self.displacements:
                        plate.data.vertices[i].co.x += float(val[0])/SCALING_PARAMETER
                        plate.data.vertices[i].co.y += float(val[1])/SCALING_PARAMETER
                        plate.data.vertices[i].co.z += float(val[2])/SCALING_PARAMETER
                        i += 1
                    #'''


                    # vertici che devono perdere un edge:
                    plate_vertices_that_lost_an_edge = []
                    for edge in self.edges_to_remove:
                        if (edge[0] not in plate_vertices_that_lost_an_edge):
                            plate_vertices_that_lost_an_edge.append(edge[0])
                        if (edge[1] not in plate_vertices_that_lost_an_edge):
                            plate_vertices_that_lost_an_edge.append(edge[1])

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



                    
                    '''
                    # Elimino i vertici rimasti che non sono collegati a nessun edge
                    vertices_to_be_deleted = []

                    for edge in bm.edges:
                        edge.select_set(True)
                    
                    for vert in bm.verts:
                        if not vert.select:
                            vertices_to_be_deleted.append(vert)
                            #bm.verts.remove(vert)
                    '''



                    # Aggiorna mesh
                    bmesh.update_edit_mesh(me)    

                    #'''
                    # Creo nuovi edge cercandoli nella lista di tutti gli edge
                    plate_all_edges = plate.data["edges_all"]
                    
                    # i nuovi edge da creare sono quelli dentro plate_all_edges che hanno entrambi i vertici tra i vertici a cui e' stato eliminato un edge,
                    # ma al tempo stesso non deve essere stato eliminato un edge proprio tra quei due vertici (se no lo starei andando a ri aggiungere)

                    # scorro tutti gli edge e controllo quelli che contengono entrambi i vertici dentro plate_vertices_that_lost_an_edge ma che non sono in self.edges_to_remove:
                    #edges_to_create = []
                    bm.verts.ensure_lookup_table()
                    for edge in plate_all_edges:
                        if (edge[0] in plate_vertices_that_need_new_edges and edge[1] in plate_vertices_that_need_new_edges):
                            # Creo il nuovo edge solo se non esiste:
                            if not(set(bm.verts[edge[0]].link_edges) & set(bm.verts[edge[1]].link_edges)):
                                #edges_to_create.append(edge)
                                #print(f"({edge[0]},{edge[1]})")
                                bm.edges.new((bm.verts[edge[0]], bm.verts[edge[1]]))
                    
                    #print("edges to create:")
                    #print([(edge[0], edge[1]) for edge in edges_to_create])

                    #'''

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



                print("elapsed time:")
                print(prof)
            

            # prendo la world matrix dell'oggetto, i vertici vanno moltiplicati per quella se no ottengo
            # solo le posizioni locali ignorando i displacement e scaling
            circle_obj = context.scene.objects[CIRCLE_OBJECT_NAME]
            circle_world_matrix = circle_obj.matrix_world.copy()

            # Aggiorna posizioni frame precedenti
            if (FPS == 60):
                self.circle_prev_coordinates_3 = [co for co in self.circle_prev_coordinates_2]
            self.circle_prev_coordinates_2 = [co for co in self.circle_prev_coordinates_1]

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

        circle = bpy.data.objects[CIRCLE_OBJECT_NAME]

        # Valori velocita' raggio e angolo
        velocity = context.scene.simulation_properties.velocity / SCALING_PARAMETER
        alpha_y = context.scene.simulation_properties.alpha_y
        alpha_x = context.scene.simulation_properties.alpha_x
        radius = context.scene.simulation_properties.radius / SCALING_PARAMETER

        # Applica scaling al cerchio
        circle_scaling = context.scene.simulation_properties.radius / CIRCLE_RADIUS_DEFAULT_VALUE
        circle.scale = (circle_scaling, circle_scaling, circle_scaling)

        # Lunghezza traiettoria
        trajectory = abs(TIME_TO_IMPACT * velocity) + radius #+ MARGIN_TRAJECTORY

        # Posiz iniziale
        circle_origin_y = trajectory * math.cos(math.radians(alpha_y)) + radius
        circle_origin_x = - trajectory * math.sin(math.radians(alpha_y)) * math.cos(math.radians(alpha_x))
        circle_origin_z = - trajectory * math.sin(math.radians(alpha_y)) * math.sin(math.radians(alpha_x))

        # Imposta posizione iniziale cerchio
        circle.location = (circle_origin_x, circle_origin_z, circle_origin_y)

        # Calcola spostamenti
        self.displacement_y = -velocity*math.cos(math.radians(alpha_y))/FPS
        self.displacement_x = velocity*math.sin(math.radians(alpha_y)) * math.cos(math.radians(alpha_x)) / FPS      # DA CONTROLLARE
        self.displacement_z = velocity*math.sin(math.radians(alpha_y)) * math.sin(math.radians(alpha_x)) / FPS      # DA CONTROLLARE

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
        #self._timer = wm.event_timer_add(time_step=0.5, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


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
    bl_label = "Simulation Options"
    bl_idname = "ANNA_PT_Simulation_Options_Main_Panel"  # deve essere diverso per ogni classe
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Simulation Options"

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

    '''
    # Crea modello ML
    device = "cuda" if torch.cuda.is_available() else "cpu"
    input_seq_len = 72
    input_dim = 4  # Each input is a sequence of 2Dx2 points (x, y)
    d_model = 512  # Embedding dimension
    nhead = 4  # Number of attention heads
    num_encoder_layers = 4  # Number of transformer encoder layers
    dim_feedforward = 512  # Feedforward network dimension
    output_dim = 280  # Each output is a 2D point (x, y)
    dropout = 0.0
    model = Transformer2DPointsModel(input_dim, input_seq_len, d_model, nhead, num_encoder_layers, dim_feedforward, output_dim, dropout).to(device)
    '''

    register()


