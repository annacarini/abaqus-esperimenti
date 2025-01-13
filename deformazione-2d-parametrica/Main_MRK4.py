import sys
import os
if os.getcwd() not in sys.path: sys.path.append( os.getcwd() )
import time
import abaqusConstants


from abaqus            import *
from driverUtils       import *
from caeModules        import *
from Simulation2D_MRK4 import *


def log(message):
    
    print(message, file = sys.__stdout__)
    
    return


def Main():
    
    DENSITY  = 2.7E-4
    ALPHAS   = [0]             #DEGREE
    VELOCITY = 1000

    sim = Simulation2D( DENSITY )


    for idx, alpha in enumerate(ALPHAS, 0):
        
        # log("Simulation " + str(index) + ", started at " + time.strftime("%H:%M", time.localtime()))
        
        sim.runSimulation( CIRCLE_ORIGIN_X = 0,
                           CIRCLE_ORIGIN_Y = 5,
                           CIRCLE_VELOCITY = VELOCITY,
                           ALPHA           = alpha,
                           SUMULATION_ID   = idx,
                           SAVEDATABASE    = True )
        
        
        # plotPlatePoints( simulation_folder = sim.get_simulation_folder(), 
                         # onlyExternal      = False, 
                         # frameIndex        = -1 )

        
            
if __name__ == "__main__":

    Main()





