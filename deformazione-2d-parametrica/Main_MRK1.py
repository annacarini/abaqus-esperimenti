import sys
import os
if os.getcwd() not in sys.path: sys.path.append( os.getcwd() )
import time
import abaqusConstants
from matplotlib import pyplot as plt
import abaqus

from abaqus            import *
from driverUtils       import *
from caeModules        import *
from Simulation2D_MRK1 import *


def log(message):
    
    print(message, file = sys.__stdout__)
    
    return


def plotPlatePoints(simulationID, onlyExternal = False, frameIndex=-1):

    job_path = "Dynamic_Simulation_" + str(simulationID) + '/Simulation_Job_' + str(simulationID) + '.odb'     # tipo "Dynamic_Simulation_15/Simulation_Job_15.odb"
    odb = session.openOdb(job_path) # qua dovremmo assicurarci che esista

    if (onlyExternal):
        outputRegion = odb.rootAssembly.instances['PLATE'].nodeSets['SURFACE-ALL']
    else:
        outputRegion = odb.rootAssembly.instances['PLATE'].nodeSets['SET-ALL']

    frame = odb.steps['Step-1'].frames[frameIndex]

    points = frame.fieldOutputs['COORD']

    points = points.getSubset(region=outputRegion)
    points_coords = []
    for v in points.values:
        points_coords.append( [v.nodeLabel, v.data[0], v.data[1]] )

    xs = [p[1] for p in points_coords]
    ys = [p[2] for p in points_coords]
    
    fig = plt.figure()
    plt.scatter(xs, ys)
    plt.title("Simulation " + str(simulationID) + ", Frame " + str(frameIndex))


import time

def Main():
    


    DENSITY  = 2.7E-4
    ALPHAS   = [0]
    VELOCITY = -120000 #max value -120000

    
    sim = Simulation2D( DENSITY )
    
    sim.runSimulation( CIRCLE_ORIGIN_X = 0,
                        CIRCLE_ORIGIN_Y = 20,
                        CIRCLE_VELOCITY = VELOCITY,
                        ALPHA           = 0,
                        SUMULATION_ID   = 0, 
                        SAVEDATABASE=True
                   )
            
    start = time.time() 
    #plotPlatePoints(0, False, 0)
    #plotPlatePoints(0, False, -1) #disabilitato perché abaqus rimane "hanging"
    #plt.show()

    for idx,VELOCITY in enumerate(range(-1000,-120000,-1000)):    
        # log("Simulation " + str(index) + ", started at " + time.strftime("%H:%M", time.localtime()))
        
        sim.runSimulation( CIRCLE_ORIGIN_X = 0,
                           CIRCLE_ORIGIN_Y = 20,
                           CIRCLE_VELOCITY = VELOCITY,
                           ALPHA           = 0,
                           SUMULATION_ID   = idx,   
                           SAVEDATABASE=True)
 
    with open("timing.txt", "w") as text_file:
        text_file.write("Total Process time: " + str(time.time() - start))    
            
if __name__ == "__main__":

    Main()





