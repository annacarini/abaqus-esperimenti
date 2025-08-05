import os
import sys

from abaqus      import *



def log(message):
    print(message, file = sys.__stdout__)
    return



Mdb()

# Indice simulazione da cui prendere il database
index = 2

folder_name = f'Dynamic_Simulation_{index}'
previous_path = os.getcwd()
new_path = os.path.join(previous_path, folder_name)
os.chdir(new_path)


#'''
cae_file_path = f"{index}.cae"
openMdb(cae_file_path)


MODEL_NAME = f'Simulation_{index}'
model = mdb.models[MODEL_NAME]

circle_surface = model.parts["circle"].sets["surface"]
plate_all = model.parts["plate"].sets["set-all"]
plate_surface = model.parts["plate"].sets["surface-all"]

log(len([elem.label for elem in plate_all.elements]))

#exit()

#'''


# LOADING OUTPUT DATABASE
JOB_NAME = "Simulation_Job_" + str(index)
odb = session.openOdb(JOB_NAME + '.odb')

# GETTING THE FRAMES
firstFrame = odb.steps['Step-1'].frames[0]
lastFrame = odb.steps['Step-1'].frames[-1]

# REGIONS OF INTEREST
plateRegion         = odb.rootAssembly.instances['PLATE'].nodeSets['SET-ALL']
plateRegionExternal = odb.rootAssembly.instances['PLATE'].nodeSets['SURFACE-ALL']
circleRegion = odb.rootAssembly.instances['CIRCLE'].nodeSets['SET-ALL']
circleRegionExternal = odb.rootAssembly.instances['CIRCLE'].nodeSets['SURFACE']



circle_region = odb.steps['Step-1'].historyRegions['Node ASSEMBLY.1']
log("history outputs:")
log(circle_region.historyOutputs)
circle_v2Data = circle_region.historyOutputs['V2_FILTER-CIRCLE-V2'].data

log(circle_v2Data[0])


'''
coordinates_plate_first = firstFrame.fieldOutputs['COORD'].getSubset(region = plateRegion)
coordinates_plate_last = lastFrame.fieldOutputs['COORD'].getSubset(region = plateRegion)

log("nodi lastra prima dell'impatto:")
log(len(coordinates_plate_first.values))
log("nodi lastra dopo l'impatto:")
log(len(coordinates_plate_last.values))
'''

'''
evols_plate_first = firstFrame.fieldOutputs['EVOL'].getSubset(region = plateRegion)
evols_plate_last = lastFrame.fieldOutputs['EVOL'].getSubset(region = plateRegion)

log("nodi lastra prima dell'impatto:")
log(len(evols_plate_first.values))
log("nodi lastra dopo l'impatto:")
log(len(evols_plate_last.values))

log(firstFrame.fieldOutputs['EVOL'].getSubset(region = plateRegion).values)
'''


'''
# ELEMENTI ELIMINATI

first_frame_inactive_elems = []
last_frame_inactive_elems = []

for elemStatus in firstFrame.fieldOutputs['STATUS'].values:
    if (elemStatus.data == 0.0):
        first_frame_inactive_elems.append(elemStatus.elementLabel)

for elemStatus in lastFrame.fieldOutputs['STATUS'].values:
    if (elemStatus.data == 0.0):
        last_frame_inactive_elems.append(elemStatus.elementLabel)

log("tutti gli elementi nel primo frame:")
log(len([elem.elementLabel for elem in firstFrame.fieldOutputs['STATUS'].values]))

log("first frame:")
log(first_frame_inactive_elems)
log("last frame:")
log(last_frame_inactive_elems)
'''



#plate_elems = odb.parts['PLATE'].nodes
#log(plate_elems)



#coordinates_plate_first = firstFrame.elements.getSubset(region = plateRegion)

#log(firstFrame.fieldOutputs)

#history_region = odb.steps['Step-1'].historyRegions['Node ASSEMBLY.1']

#log(odb.steps['Step-1'].historyRegions)
#plate_evol = history_region.historyOutputs['EVOL'].data

#log(history_region.historyOutputs)
#log(plate_evol)