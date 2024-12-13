import sys
import time
from abaqus import *
import abaqusConstants
from driverUtils import *
from caeModules import *
from matplotlib import pyplot as plt
from matplotlib import interactive

from Simulation2D import *


def log(message):
    print(message, file=sys.__stdout__)
    return


        
def main():
    
    index = 0
    density = 2.7E-4


    # Run simulazione 0, con plot dei punti all'inizio e alla fine

    '''
    sim0 = Simulation2D(-100, -800, density, 0)
    sim0.runSimulation(saveDisplacementCSV=True)

    # Scatter dei punti di frontiera all'INIZIO della simulazione 0
    sim0.plotLastraPoints(onlyExternal=False, frameIndex=0)

    # Scatter dei punti di frontiera alla FINE della simulazione 0
    sim0.plotLastraPoints(onlyExternal=False, frameIndex=-1)

    plt.show()
    '''


    # Loop di simulazioni

    '''
    for vel_x in range(-100, 101, 100):
        for vel_y in range(-800, -601, 100):
            log("Simulation " + str(index) + ", started at " + time.strftime("%H:%M", time.localtime()))
            sim = Simulation2D(vel_x, vel_y, density, index)
            sim.runSimulation()
            index += 1
    '''

    # Plot della simulazione 0, direttamente caricando l'output database gia' generato
    Simulation2D.plotLastraPointsStatic(0, onlyExternal=False, frameIndex=0)       # tutti i punti, all'INIZIO della simulazione 0
    Simulation2D.plotLastraPointsStatic(0, onlyExternal=False, frameIndex=-1)      # tutti i punti, alla FINE della simulazione 0

    Simulation2D.plotLastraPointsStatic(0, onlyExternal=True, frameIndex=0)       # solo punti ESTERNI, all'INIZIO della simulazione 0
    Simulation2D.plotLastraPointsStatic(0, onlyExternal=True, frameIndex=-1)      # solo punti ESTERNI, alla FINE della simulazione 0

    plt.show()


if __name__ == "__main__":
    main()





