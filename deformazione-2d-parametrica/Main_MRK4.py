import sys
import os
if os.getcwd() not in sys.path: sys.path.append( os.getcwd() )
import time
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
    
    DENSITY  = 2.7E-4
    ALPHAS   = [0, 20]             # DEGREE
    VELOCITIES = [600]   # temporaneo, poi lo cambiamo in velocity_min e velocity_max

    sim = Simulation2D( DENSITY )


    # Creo file per salvare info su tutte le simulazioni: tempo impiegato, se e' terminata, ecc
    INFO_FILE_PATH = "Simulations_Info.csv"
    with open(INFO_FILE_PATH, 'w', newline='') as info_csv:
        info_csv_writer = csv.writer(info_csv)
        info_csv_writer.writerow(["INDEX", "SIMULATION_TIME", "SIMULATION_LENGTH", "COMPLETED", "INIT_SPEED", "ANGLE"])


    # NOTA:
    # SIMULATION_TIME = tempo impiegato ad eseguire la simulazione
    # SIMULATION_LENGTH = durata della simulazione, cioè tempo che impiega la palla a fermarsi

    idx = 0


    for alpha in ALPHAS:
        for velocity in VELOCITIES:
        
            # log("Simulation " + str(index) + ", started at " + time.strftime("%H:%M", time.localtime()))
            
            start = time.time()

            (simulation_length, simulation_completed) = sim.runSimulation(
                CIRCLE_VELOCITY = velocity,
                ALPHA           = alpha,
                SUMULATION_ID   = idx,
                SAVEDATABASE    = True
            )

            simulation_time = str(time.time() - start)

            # Salva info
            with open(INFO_FILE_PATH, 'a', newline='') as info_csv:
                info_csv_append = csv.writer(info_csv)
                info_csv_append.writerow([idx, simulation_time, simulation_length, simulation_completed, velocity, alpha])
            

        
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
            

            idx = idx + 1
            


if __name__ == "__main__":

    Main()





