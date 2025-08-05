import os
import sys

from abaqus      import *



def log(message):
    print(message, file = sys.__stdout__)
    return



Mdb()

# Indice simulazione da cui prendere il database
index = 0

folder_name = f'Dynamic_Simulation_{index}'
previous_path = os.getcwd()
new_path = os.path.join(previous_path, folder_name)
os.chdir(new_path)


# PRENDI LA LISTA DI ELEMENTI SOPPRESSI

JOB_NAME = "Simulation_Job_" + str(index)
odb = session.openOdb(JOB_NAME + '.odb')

lastFrame = odb.steps['Step-1'].frames[-1]

plateRegion = odb.rootAssembly.instances['PLATE'].nodeSets['SET-ALL']

last_frame_inactive_elems = []
for elemStatus in lastFrame.fieldOutputs['STATUS'].values:
    if (elemStatus.data == 0.0):
        last_frame_inactive_elems.append(elemStatus.elementLabel)


# PRENDI LA LISTA DI EDGE

cae_file_path = f"{index}.cae"
openMdb(cae_file_path)

MODEL_NAME = f'Simulation_{index}'
model = mdb.models[MODEL_NAME]

plate_surface = model.parts["plate"].sets["surface-all"]

plate_connectivity = [elem.connectivity for elem in plate_surface.elements]
plate_surface_nodes_labels = [node.label for node in plate_surface.nodes]

# superfici della lastra
plate_surface_top = model.parts["plate"].sets["surface-top"]
plate_surface_bottom = model.parts["plate"].sets["surface-bottom"]
plate_surface_north = model.parts["plate"].sets["surface-north"]
plate_surface_south = model.parts["plate"].sets["surface-south"]
plate_surface_east = model.parts["plate"].sets["surface-east"]
plate_surface_west = model.parts["plate"].sets["surface-west"]

# nodi delle singole superfici della lastra
plate_surface_top_nodes_labels = [node.label for node in plate_surface_top.nodes]
plate_surface_bottom_nodes_labels = [node.label for node in plate_surface_bottom.nodes]
plate_surface_north_nodes_labels = [node.label for node in plate_surface_north.nodes]
plate_surface_south_nodes_labels = [node.label for node in plate_surface_south.nodes]
plate_surface_east_nodes_labels = [node.label for node in plate_surface_east.nodes]
plate_surface_west_nodes_labels = [node.label for node in plate_surface_west.nodes]



# Nota: nella "connectivity" degli elementi i label dei nodi partono da 0, mentre i label dei nodi dentro "nodes" partono da 1
# (Confermato qua: https://imechanica.org/node/17245) 
# Quindi da connectivity devo aumentare tutti i label di 1 prima di scartare quelli non presenti dentro "plate_surface_nodes_labels"



# dalla connectivity gli edge li ottengo come lista di tuple di label tipo [(5,18),...]. il problema e' che questi label hanno senso
# solo per abaqus, non per blender. a blender passo un array di vertici con tutte le coordinate, e i label degli edge devono
# corrispondere all'indice di ogni vertice dentro questo array. quindi devo modificare la lista di edge in modo che i label
# diventino l'indice di ogni vertice nella lista di vertici


# creo un dizionario che associa a ogni vertice nella lista di nodi il proprio indice
plate_surface_nodes_indices = {}
i = 0
for label in plate_surface_nodes_labels:
    plate_surface_nodes_indices[label] = i
    i += 1

# (preso sempre da qua: https://classes.engineering.wustl.edu/2009/spring/mase5513/abaqus/docs/v6.6/books/usb/default.htm?startat=pt06ch22s01ael03.html#usb-elm-e3delem)
# Hexahedron (brick) element faces
# Face 1	1 – 2 – 3 – 4 face          -> 0,1,2,3
# Face 2	5 – 8 – 7 – 6 face          -> 4,7,6,5
# Face 3	1 – 5 – 6 – 2 face          -> 0,4,5,1
# Face 4	2 – 6 – 7 – 3 face          -> 1,5,6,2
# Face 5	3 – 7 – 8 – 4 face          -> 2,6,7,3
# Face 6	4 – 8 – 5 – 1 face          -> 3,7,4,0
# quindi per gli elementi esaedrici C3D8 che ho usato per la lastra, le 6 facce sono composte dai nodi messi come descritto sopra
# (ogni elemento ha 8 vertici, quindi i label sopra vanno da 1 a 8, non da 0 a 7)


plate_surface_edges = []           # qui metto tutti gli edge superficiali
plate_surface_edges_not_removed = []    # qui metto tutti gli edge superficiali che appartengono ad elementi non rimossi

for elem in plate_surface.elements:

    connectivity = elem.connectivity

    face1 = [connectivity[0], connectivity[1], connectivity[2], connectivity[3]]
    face2 = [connectivity[4], connectivity[7], connectivity[6], connectivity[5]]
    face3 = [connectivity[0], connectivity[4], connectivity[5], connectivity[1]]
    face4 = [connectivity[1], connectivity[5], connectivity[6], connectivity[2]]
    face5 = [connectivity[2], connectivity[6], connectivity[7], connectivity[3]]
    face6 = [connectivity[3], connectivity[7], connectivity[4], connectivity[0]]

    faces = [face1, face2, face3, face4, face5, face6]

    for face in faces:

        for i in range(0,len(face)):

            first_node = face[i] + 1
            second_node = face[(i+1)%len(face)] + 1 # nodo dopo, o primo nodo se first_node e' l'ultimo
        
            # se sia first_node che second_node sono sulla superficie, aggiungi la tupla a edges
            if ((first_node in plate_surface_top_nodes_labels and second_node in plate_surface_top_nodes_labels) or
                (first_node in plate_surface_bottom_nodes_labels and second_node in plate_surface_bottom_nodes_labels) or
                (first_node in plate_surface_east_nodes_labels and second_node in plate_surface_east_nodes_labels) or
                (first_node in plate_surface_west_nodes_labels and second_node in plate_surface_west_nodes_labels) or
                (first_node in plate_surface_north_nodes_labels and second_node in plate_surface_north_nodes_labels) or
                (first_node in plate_surface_south_nodes_labels and second_node in plate_surface_south_nodes_labels)):
                
                # mettili in ordine crescente
                if (first_node < second_node):
                    #edge = f"{plate_surface_nodes_indices[first_node]},{plate_surface_nodes_indices[second_node]}"
                    edge = (plate_surface_nodes_indices[first_node], plate_surface_nodes_indices[second_node])
                else:
                    #edge = f"{plate_surface_nodes_indices[second_node]},{plate_surface_nodes_indices[first_node]}"
                    edge = (plate_surface_nodes_indices[second_node], plate_surface_nodes_indices[first_node])


                # controlla se non l'ho gia' inserito nella lista di tutti gli edge
                if (not edge in plate_surface_edges):
                    plate_surface_edges.append(edge)
                
                # se non appartiene ad un elemento rimosso
                if (not edge in plate_surface_edges_not_removed) and (not elem.label in last_frame_inactive_elems):
                    plate_surface_edges_not_removed.append(edge)


# ottengo gli edge rimossi come differenza tra tutti gli edge e quelli appartenenti ad elementi non rimossi
plate_surface_edges_removed = []
plate_vertices_of_removed_edges = []
for edge in plate_surface_edges:
    if (not edge in plate_surface_edges_not_removed):
        #log(edge)
        plate_surface_edges_removed.append(f"{edge[0]},{edge[1]}")
        if (edge[0] not in plate_vertices_of_removed_edges):
            plate_vertices_of_removed_edges.append(edge[0])
        if (edge[1] not in plate_vertices_of_removed_edges):
            plate_vertices_of_removed_edges.append(edge[1])


# itero su tutti i vertici della superficie della lastra, e per ogni vertice metto 1 se appartiene a un edge rimosso, 0 altrimenti
plate_surface_vertices_removed_info = []
#log(plate_vertices_of_removed_edges)
for n in plate_surface_nodes_labels:
    if (n in plate_vertices_of_removed_edges):
        plate_surface_vertices_removed_info.append(1)
    else:
        plate_surface_vertices_removed_info.append(0)


'''
with open('plate_surface_removed_edges.txt', mode='wt', encoding='utf-8') as plateEdgesFile:
    for line in plate_surface_edges_removed:
        print(line, file = plateEdgesFile)
'''
        
with open('plate_surface_vertices_removed_info.txt', mode='wt', encoding='utf-8') as plateVerticesFile:
    for line in plate_surface_vertices_removed_info:
        print(line, file = plateVerticesFile)





# IMPORTANTE:
# Non devo vedere quali edge appartengono ad elementi rimossi e togliere quelli,
# ma piuttosto vedere quali edge NON appartengono ad elementi rimossi e TENERE quelli,
# e poi rimuoverli dalla lista di tutti gli edge. La differenza è che più elementi condividono
# gli edge, e se elimino tutti gli edge di un elemento rimosso vado a togliere anche gli edge
# degli elementi adiacenti non rimossi, bucando la figura