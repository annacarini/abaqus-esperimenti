import sys
import os
if os.getcwd() not in sys.path: sys.path.append( os.getcwd() )
import time
import random
import csv


from abaqus            import *
from driverUtils       import *
from caeModules        import *

from Simulation3D import *


def log(message):
    print(message, file = sys.__stdout__)
    return


def Main():
    idx = 1
    radius = 2.5
    velocity = 1000
    alpha_Y = 60
    alpha_X = 45

    sim = Simulation3D()
    sim.runSimulation(
        CIRCLE_RADIUS   = radius,
        CIRCLE_VELOCITY = velocity,
        ALPHA_Y         = alpha_Y,
        ALPHA_X         = alpha_X,
        SUMULATION_ID   = idx,
        SAVEDATABASE    = True
    )



def Main2():
    
    # Creo file per salvare info su tutte le simulazioni: tempo impiegato, se e' terminata, ecc
    INFO_FILE_PATH = "Simulations_Info.csv"
    with open(INFO_FILE_PATH, 'w', newline='') as info_csv:
        info_csv_writer = csv.writer(info_csv)
        info_csv_writer.writerow(["INDEX", "SIMULATION_TIME", "SIMULATION_LENGTH", "COMPLETED", "INIT_SPEED", "ANGLE_X", "ANGLE_Y", "CIRCLE_RADIUS"])


    idx = 0
    radius = 2.5
    velocity = 1000
    alpha_Y = 60
    alpha_X = 45

    log("Simulation " + str(idx))

    start = time.time()

    sim = Simulation3D()
    (simulation_length, simulation_completed) = sim.runSimulation(
        CIRCLE_RADIUS   = radius,
        CIRCLE_VELOCITY = velocity,
        ALPHA_Y         = alpha_Y,
        ALPHA_X         = alpha_X,
        SUMULATION_ID   = idx,
        SAVEDATABASE    = True
    )

    # Salva info
    simulation_time = str(time.time() - start)
    with open(INFO_FILE_PATH, 'a', newline='') as info_csv:
        info_csv_append = csv.writer(info_csv)
        info_csv_append.writerow([idx, simulation_time, simulation_length, simulation_completed, velocity, alpha_X, alpha_Y, radius])

    

    '''

    RADIUS_RANGE = [1.5, 4]             # il raggio non puo' essere troppo piccolo se no mi sa che la palla passa attraverso i nodi della lastra
    VELOCITY_RANGE = [200, 1500]
    ALPHA_RANGE = [-60, 60]             # DEGREE

    # Vogliamo circa 1000 simulazioni per raggio, e circa 6 raggi diversi tra 1.5 e 4  =>  6000 simulazioni scegliendo sempre tutti i valori in modo random
    SIMULATIONS_TOT = 1


    # NOTA:
    # SIMULATION_TIME = tempo impiegato ad eseguire la simulazione
    # SIMULATION_LENGTH = durata della simulazione, cioè tempo che impiega la palla a fermarsi


    idx_start = 0

    for idx in range(idx_start, SIMULATIONS_TOT):
            
            log("Simulation " + str(idx))

            start = time.time()

            radius = random.uniform(RADIUS_RANGE[0], RADIUS_RANGE[1])
            velocity = random.uniform(VELOCITY_RANGE[0], VELOCITY_RANGE[1])
            alpha = random.uniform(ALPHA_RANGE[0], ALPHA_RANGE[1])

            sim = Simulation2D( radius )
            (simulation_length, simulation_completed) = sim.runSimulation(
                CIRCLE_VELOCITY = velocity,
                ALPHA           = alpha,
                SUMULATION_ID   = idx,
                SAVEDATABASE    = True
            )

        
            
            # Salva info
            simulation_time = str(time.time() - start)
            with open(INFO_FILE_PATH, 'a', newline='') as info_csv:
                info_csv_append = csv.writer(info_csv)
                info_csv_append.writerow([idx, simulation_time, simulation_length, simulation_completed, velocity, alpha, radius])
    '''


if __name__ == "__main__":

    Main()





