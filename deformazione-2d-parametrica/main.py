import sys
import time
from abaqus import *
import abaqusConstants
from driverUtils import *
from caeModules import *

from Simulation2D import *


def log(message):
    print(message, file=sys.__stdout__)
    return


def main():
    
    index = 0
    density = 2.7E-4

    #sim = Simulation2D(-100, -800, density, 0)
    #sim.runSimulation(saveDisplacementCSV=False)

    for vel_x in range(-100, 101, 100):
        for vel_y in range(-800, -601, 100):
            log("Simulation " + str(index) + ", started at " + time.strftime("%H:%M", time.localtime()))
            sim = Simulation2D(vel_x, vel_y, density, index)
            sim.runSimulation()
            index += 1
    
            
if __name__ == "__main__":
    main()





