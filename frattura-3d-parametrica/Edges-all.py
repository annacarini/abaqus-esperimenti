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


cae_file_path = f"{index}.cae"
openMdb(cae_file_path)

MODEL_NAME = f'Simulation_{index}'
model = mdb.models[MODEL_NAME]


plate_surface = model.parts["plate"].sets["surface-all"]
plate_connectivity = [elem.connectivity for elem in plate_surface.elements]
plate_surface_nodes_labels = [node.label for node in plate_surface.nodes]



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

plate_surface_edges = []
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
        
            # mettili in ordine crescente
            if (first_node < second_node):
                edge = f"{plate_surface_nodes_indices[first_node]},{plate_surface_nodes_indices[second_node]}"
            else:
                edge = f"{plate_surface_nodes_indices[second_node]},{plate_surface_nodes_indices[first_node]}"

            if (not edge in plate_surface_edges):
                plate_surface_edges.append(edge)


with open('plate_all_edges.txt', mode='wt', encoding='utf-8') as plateEdgesFile:
    for line in plate_surface_edges:
        print(line, file = plateEdgesFile)

