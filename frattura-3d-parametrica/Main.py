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
    
    RADIUS_RANGE = [2.5, 4.5]             
    VELOCITY_RANGE = [6000, 11000]
    ALPHA_Y_RANGE = [0, 60]             # DEGREE
    ALPHA_X_RANGE = [-180, 180]


    idx_start = 4500
    SIMULATIONS_TOT = 5000

    # NOTA:
    # SIMULATION_TIME = tempo impiegato ad eseguire la simulazione
    # SIMULATION_LENGTH = durata della simulazione, cioè tempo che impiega la palla a fermarsi

    # Creo file per salvare info su tutte le simulazioni: tempo impiegato, se e' terminata, ecc
    INFO_FILE_PATH = "Simulations_Info.csv"
    with open(INFO_FILE_PATH, 'w', newline='') as info_csv:
        info_csv_writer = csv.writer(info_csv)
        info_csv_writer.writerow(["INDEX", "SIMULATION_TIME", "SIMULATION_LENGTH", "NO_FRACTURE", "INIT_SPEED", "ANGLE_X", "ANGLE_Y", "CIRCLE_RADIUS"])


    for idx in range(idx_start, SIMULATIONS_TOT):
            
            log("Simulation " + str(idx))

            start = time.time()

            # Scegli parametri random
            radius = random.uniform(RADIUS_RANGE[0], RADIUS_RANGE[1])
            velocity = random.uniform(VELOCITY_RANGE[0], VELOCITY_RANGE[1])
            alpha_X = random.uniform(ALPHA_X_RANGE[0], ALPHA_X_RANGE[1])
            alpha_Y = random.uniform(ALPHA_Y_RANGE[0], ALPHA_Y_RANGE[1])

            # Esegui la simulazione
            sim = Simulation3D()
            (simulation_length, simulation_completed) = sim.runSimulation(
                CIRCLE_RADIUS   = radius,
                CIRCLE_VELOCITY = velocity,
                ALPHA_Y         = alpha_Y,
                ALPHA_X         = alpha_X,
                SIMULATION_ID   = idx
            )
        
            # Salva info
            simulation_time = str(time.time() - start)
            with open(INFO_FILE_PATH, 'a', newline='') as info_csv:
                info_csv_append = csv.writer(info_csv)
                info_csv_append.writerow([idx, simulation_time, simulation_length, simulation_completed, velocity, alpha_X, alpha_Y, radius])


if __name__ == "__main__":
    Main()





