import matplotlib.pyplot as plt
import csv


def drawImage(imageName, plateNodesFilename, plateEdgesFilename, circleNodesFilename, circleEdgesFilename):


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

    fig = plt.figure()
    fig.tight_layout()

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

    plt.axis('scaled')
    plt.axis('off')
    #plt.show()
    fig.savefig(imageName)
