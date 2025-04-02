import matplotlib.pyplot as plt
import csv


# Bisognera' controllare se questi range sono abbastanza/troppo grandi
MIN_X = -90
MAX_X = 90
MIN_Y = -10     # il lato sotto della lastra e' a -5
MAX_Y = 110


def drawImage(imageName, plateNodesFilename, plateEdgesFilename, circleNodesFilename, circleEdgesFilename):

    plt.clf()       # cancella plot, necessario se no chiamando la funzione piu volte di fila mi mantiene i plot precedenti
    plt.axis('scaled')
    plt.xlim([MIN_X, MAX_X]) 
    plt.ylim([MIN_Y, MAX_Y])

    # crea dizionario delle coordinate dei nodi del plate
    with open(plateNodesFilename, mode='r') as infile:
        reader = csv.reader(infile)
        next(reader)    # skip header
        plateNodes = {row[0]:[row[1], row[2]] for row in reader}


    # crea dizionario delle coordinate dei nodi del circle
    with open(circleNodesFilename, mode='r') as infile:
        reader = csv.reader(infile)
        next(reader)    # skip header
        circleNodes = {row[0]:[row[1], row[2]] for row in reader}


    # disegna plate
    with open(plateEdgesFilename, mode='r') as infile:
        reader = csv.reader(infile)
        for row in reader:
            firstNode = plateNodes[row[0]]
            secondNode = plateNodes[row[1]]
            x_values = [float(firstNode[0]), float(secondNode[0])]
            y_values = [float(firstNode[1]), float(secondNode[1])]
            plt.plot(x_values, y_values, 'red')


    # disegna circle
    with open(circleEdgesFilename, mode='r') as infile:
        reader = csv.reader(infile)
        for row in reader:
            firstNode = circleNodes[row[0]]
            secondNode = circleNodes[row[1]]
            x_values = [float(firstNode[0]), float(secondNode[0])]
            y_values = [float(firstNode[1]), float(secondNode[1])]
            plt.plot(x_values, y_values, 'red')


    plt.axis('off')
    #plt.show()     # nota: se faccio "show" prima di savefig, salva un'immagine vuota
    plt.savefig(imageName)


'''
folderName = "Dynamic_Simulation_0/"
drawImage(
                imageName = "before_impact.png",
                plateNodesFilename = folderName + "0_before_impact_coordinates_plate.csv",
                plateEdgesFilename = folderName + "plate_surface_edges.txt",
                circleNodesFilename = folderName + "0_before_impact_coordinates_circle.csv", 
                circleEdgesFilename = folderName + "circle_surface_edges.txt"
            )
'''