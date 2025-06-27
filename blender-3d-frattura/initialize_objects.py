import bpy 
import csv
from pathlib import Path

SCALING_PARAMETER = 10

# File con posizioni vertici:
plateVerticesFilename = "//plate_initial_coordinates.csv"
plateEdgesFileName = "//plate_surface_edges.txt"
plateAllEdgesFileName = "//plate_all_edges.txt" 
circleVerticesFilename = "//circle_initial_coordinates.csv"
circleEdgesFilename = "//circle_surface_edges.txt"



def instantiateMeshFromFile(verticesFilename, edgesFilename, objectName, allEdgesFilename="", recenterVertices = False):
    verts = []
    edges = [] # int pairs, each pair contains two indices to the vertices argument. eg: [(1, 2), …]
    faces = []

    verticesFilepath = Path(bpy.path.abspath(verticesFilename))
    edgesFilepath = Path(bpy.path.abspath(edgesFilename))


    with open(verticesFilepath, mode="r") as verticesFile:
        reader = csv.reader(verticesFile)
        next(reader) #skip header
        #line e' cosi': [label, x, y, z], in blender la z e' l'asse verticale di default quindi inverto y e z
        for line in reader:
            verts.append((float(line[1])/SCALING_PARAMETER, float(line[3])/SCALING_PARAMETER, float(line[2])/SCALING_PARAMETER))

    with open(edgesFilepath, mode="r") as edgesFile:
        for line in edgesFile:
            line = line.strip()
            lineArray = line.split(",")
            edges.append((int(lineArray[0]), int(lineArray[1])))


    if (recenterVertices):
        avg = [0, 0, 0]
        tot = len(verts)
        # calcola la media di tutti i vertici
        for v in verts:
            avg[0] += v[0]
            avg[1] += v[1]
            avg[2] += v[2]
        avg[0] /= tot
        avg[1] /= tot
        avg[2] /= tot
        # trasla tutti i vertici di avg
        for i in range(0, len(verts)):
            verts[i] = (verts[i][0]-avg[0], verts[i][1]-avg[1], verts[i][2]-avg[2])
        


    mesh_data = bpy.data.meshes.new(objectName + "_mesh")
    mesh_data.from_pydata(verts, edges, faces)
    mesh_data.update()

    obj = bpy.data.objects.new(objectName, mesh_data)
        
    scene = bpy.context.scene
    scene.collection.objects.link(obj)
    obj.select_set(True)

    #'''
    # Seleziona tutti i vertici e crea faccia
    bpy.context.view_layer.objects.active = obj  # Set object as active
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action = 'SELECT')
    bpy.ops.mesh.edge_face_add()    # Crea faccia
    #bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY') # Triangola faccia
    bpy.ops.object.mode_set(mode = 'OBJECT')
    #'''

    # Salva le posizioni iniziali dei vertici come proprieta' dell'oggetto
    obj.data["vertices_initial"] = {}
    for i in range(0, len(verts)):
        obj.data["vertices_initial"][str(i)] = (verts[i])

    # Salva gli edge iniziali come proprieta' dell'oggetto
    obj.data["edges_initial"] = edges

    # Salva tutti gli edge come proprieta' dell'oggetto

    if (allEdgesFilename != ""):
        allEdges = []
        allEdgesFilepath = Path(bpy.path.abspath(allEdgesFilename))
        with open(allEdgesFilepath, mode="r") as allEdgesFile:
            for line in allEdgesFile:
                line = line.strip()
                lineArray = line.split(",")
                allEdges.append((int(lineArray[0]), int(lineArray[1])))
        obj.data["edges_all"] = allEdges

    return obj




# Istanzia plate
plate = instantiateMeshFromFile(plateVerticesFilename, plateEdgesFileName, "plate", allEdgesFilename=plateAllEdgesFileName)

# Istanzia palla
circle = instantiateMeshFromFile(circleVerticesFilename, circleEdgesFilename, "circle", recenterVertices=True)



