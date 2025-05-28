import bpy 
import csv
from pathlib import Path

SCALING_PARAMETER = 10

# File con posizioni vertici:
plateVerticesFilename = "//plate_initial_coordinates.csv"
circleVerticesFilename = "//circle_initial_coordinates.csv"



def instantiateMeshFromFile(filename, objectName, recenterVertices = False):
    verts = []
    faces_list = []

    filepath = Path(bpy.path.abspath(filename))

    with open(filepath, mode="r") as file:
        reader = csv.reader(file)
        next(reader) #skip header
        #line e' cosi': [label, x, y], la z la metto io a zero
        for line in reader:
            verts.append((float(line[1])/SCALING_PARAMETER, 0, float(line[2])/SCALING_PARAMETER))
            faces_list.append(int(line[0]))

    faces = [tuple(faces_list)] 

    edges = []
    faces = []

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

    # Seleziona tutti i vertici e crea faccia
    bpy.context.view_layer.objects.active = obj  # Set object as active
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action = 'SELECT')
    bpy.ops.mesh.edge_face_add()    # Crea faccia
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY') # Triangola faccia
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # Salva le posizioni iniziali dei vertici come proprieta' dell'oggetto
    for i in range(0, len(verts)):
        obj.data[str(i)] = (verts[i])

    return obj




# Istanzia plate
plate = instantiateMeshFromFile(plateVerticesFilename, "plate")

# Istanzia circle
circle = instantiateMeshFromFile(circleVerticesFilename, "circle", True)


# Correggi centro del circle

