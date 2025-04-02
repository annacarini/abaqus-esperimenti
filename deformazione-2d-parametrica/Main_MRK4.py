import sys
import os
if os.getcwd() not in sys.path: sys.path.append( os.getcwd() )
import time
import random
import csv
import SceneDrawer


from abaqus            import *
from driverUtils       import *
from caeModules        import *
from Simulation2D_MRK4 import *


def log(message):
    print(message, file = sys.__stdout__)
    return


def Main():
    
    RADIUS_RANGE = [1.5, 4]             # il raggio non puo' essere troppo piccolo se no mi sa che la palla passa attraverso i nodi della lastra
    VELOCITY_RANGE = [200, 1500]
    ALPHA_RANGE = [-60, 60]             # DEGREE


    # Con questi range definiti sopra, i valori estremi della posizione iniziale della palla sono:
    # A velocita' 1500 e angolo 0, la palla avra' Y = (2/30)*1500 = 100
    # A velocita' 1500 e angolo 60, la palla avra' X = -100*sin(60) = -86.6
    # Quindi le immagini generate devono avere la Y che arriva fino a 100 e la X che va da -87 a 87

    # Vogliamo circa 1000 simulazioni per raggio, e circa 6 raggi diversi tra 1.5 e 4  =>  6000 simulazioni scegliendo sempre tutti i valori in modo random
    SIMULATIONS_TOT = 6000

    # Creo file per salvare info su tutte le simulazioni: tempo impiegato, se e' terminata, ecc
    INFO_FILE_PATH = "Simulations_Info.csv"
    with open(INFO_FILE_PATH, 'w', newline='') as info_csv:
        info_csv_writer = csv.writer(info_csv)
        info_csv_writer.writerow(["INDEX", "SIMULATION_TIME", "SIMULATION_LENGTH", "COMPLETED", "INIT_SPEED", "ANGLE", "CIRCLE_RADIUS"])

    # NOTA:
    # SIMULATION_TIME = tempo impiegato ad eseguire la simulazione
    # SIMULATION_LENGTH = durata della simulazione, cioè tempo che impiega la palla a fermarsi

    idx_start = 5879

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

        
            previous_path = os.getcwd()
            os.chdir(sim.get_simulation_folder())
            # Crea e salva immagine situazione iniziale (= 2/30 secondi prima dell'impatto)
            SceneDrawer.drawImage(
                imageName = str(idx) + "_init.png",
                plateNodesFilename = str(idx) + "_initial_coordinates_plate.csv",
                plateEdgesFilename = "plate_surface_edges.txt",
                circleNodesFilename = str(idx) + "_initial_coordinates_circle.csv", 
                circleEdgesFilename = "circle_surface_edges.txt"
            )
            # Crea e salva immagine 1/30 secondi prima dell'impatto
            SceneDrawer.drawImage(
                imageName = str(idx) + "_before_impact.png",
                plateNodesFilename = str(idx) + "_before_impact_coordinates_plate.csv",
                plateEdgesFilename = "plate_surface_edges.txt",
                circleNodesFilename = str(idx) + "_before_impact_coordinates_circle.csv", 
                circleEdgesFilename = "circle_surface_edges.txt"
            )
            os.chdir(previous_path)
            

            # Salva info
            simulation_time = str(time.time() - start)
            with open(INFO_FILE_PATH, 'a', newline='') as info_csv:
                info_csv_append = csv.writer(info_csv)
                info_csv_append.writerow([idx, simulation_time, simulation_length, simulation_completed, velocity, alpha, radius])
            


if __name__ == "__main__":

    Main()





