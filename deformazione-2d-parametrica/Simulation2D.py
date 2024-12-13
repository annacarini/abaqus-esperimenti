import os
from abaqus import *
import abaqusConstants
from driverUtils import *
from caeModules import *
import mesh
import numpy as np
from matplotlib import pyplot as plt
import json


class Simulation2D:

    def __init__(self, speed_x, speed_y, palla_density, index):

        # Parametri passati in input
        self.index = index
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.palla_density = palla_density

        # DIMENSIONI OGGETTI
        self.LASTRA_WIDTH = 50
        self.LASTRA_HEIGHT = 6
        self.PALLA_RADIUS = 2.5

        # POSIZIONI INIZIALI
        self.LASTRA_ORIGIN_X = 0
        self.LASTRA_ORIGIN_Y = 0
        self.PALLA_ORIGIN_X = 0
        self.PALLA_ORIGIN_Y = self.PALLA_RADIUS+self.LASTRA_HEIGHT/2

        # MATERIALI
        self.STEEL_DENSITY = ((7.83E-7, ),)
        self.STEEL_ELASTIC = ((200E3, 0.3),)     # (young's modulus, poisson ratio)
        self.STEEL_PLASTIC = ((350, 0), (500, 0.8),)

        # MESH
        self.PALLA_SEED_SIZE = 1
        self.LASTRA_SEED_SX_DX_MIN = 0.2
        self.LASTRA_SEED_SX_DX_MAX = 1.2
        self.LASTRA_SEED_TOP_BOTTOM_MIN = 0.2
        self.LASTRA_SEED_TOP_BOTTOM_MAX = 2

        # ALTRO
        self.TIME_PERIOD = 0.02      # durata simulazione
        self.OUTPUT_FREQUENCY = 40   # quante volte al secondo generare dati in output (credo?)


        # Crea cartella (se non esiste) con nome <index>
        self.folder_name = str(index)
        os.makedirs(self.folder_name, exist_ok=True)

        self.simulationHasRun = False



    def _saveInputDataToFile(self):
        inputData = {
                "index":self.index,
                "density":self.palla_density,
                "speed_x":self.speed_x,
                "speed_y":self.speed_y
            }
        # salvo in un file di nome "<index>_input.json"
        with open(str(self.index)+"_input.json", "w") as outfile: 
            json.dump(inputData, outfile)



    def plotLastraPoints(self, onlyExternal = False, frameIndex=-1):
        
        if (not self.simulationHasRun):
            return

        job_path = str(self.index) + '/Job_' + str(self.index) + '.odb'
        odb = session.openOdb(job_path) # qua dovremmo assicurarci che esista

        if (onlyExternal):
            outputRegion = odb.rootAssembly.instances['LASTRA'].nodeSets['SURFACE-ALL']
        else:
            outputRegion = odb.rootAssembly.instances['LASTRA'].nodeSets['SET-ALL']

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
        plt.title("Simulation " + str(self.index) + ", Frame " + str(frameIndex))


    # STATICA, gli passi l'indice della simulazione
    @staticmethod
    def plotLastraPointsStatic(index, onlyExternal = False, frameIndex=-1):
        job_path = str(index) + '/Job_' + str(index) + '.odb'
        odb = session.openOdb(job_path) # qua dovremmo assicurarci che esista

        if (onlyExternal):
            outputRegion = odb.rootAssembly.instances['LASTRA'].nodeSets['SURFACE-ALL']
        else:
            outputRegion = odb.rootAssembly.instances['LASTRA'].nodeSets['SET-ALL']

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
        plt.title("Simulation " + str(index) + ", Frame " + str(frameIndex))



    def runSimulation(self, saveInputData=True, saveDisplacementCSV=True, saveStressCSV=True, saveDatabase=False, saveJobInput=False):

        # spostati dentro la cartella folder_name
        previous_path = os.getcwd()
        new_path = os.path.join(previous_path, self.folder_name)
        os.chdir(new_path)

        if (saveInputData):
            self._saveInputDataToFile()


        executeOnCaeStartup()

        # crea modello
        model = mdb.models['Model-1']

        #----------- crea PARTI e SET: LASTRA -----------#

        # crea sketch lastra, rettangolo da 50x6 mm
        sketch_lastra = model.ConstrainedSketch(name='sketch-lastra', sheetSize=self.LASTRA_WIDTH)
        sketch_lastra.rectangle((-self.LASTRA_WIDTH/2, -self.LASTRA_HEIGHT/2), (self.LASTRA_WIDTH/2, self.LASTRA_HEIGHT/2))

        # crea lastra usando lo sketch
        part_lastra = model.Part(name='Lastra', dimensionality=abaqusConstants.TWO_D_PLANAR, type=abaqusConstants.DEFORMABLE_BODY)
        part_lastra.BaseShell(sketch=sketch_lastra)

        # crea set che include tutta la lastra, per assegnargli il materiale
        part_lastra.Set(name='set-all', faces=part_lastra.faces.findAt(coordinates=((0, 0, 0), )))

        # crea diversi set per le superfici della lastra, per assegnargli una boundary condition (sotto) e per impostare l'interaction (sopra) 
        # e per gestire il seed della mesh
        part_lastra.Set(name='surface-top', edges=part_lastra.edges.findAt(coordinates=((0, self.LASTRA_HEIGHT/2, 0), )))
        part_lastra.Surface(name='surface-top', end1Edges=part_lastra.edges.findAt(coordinates=((0, self.LASTRA_HEIGHT/2, 0), )))
        part_lastra.Set(name='surface-bottom', edges=part_lastra.edges.findAt(coordinates=((0, -self.LASTRA_HEIGHT/2, 0), )))
        part_lastra.Set(name='surface-left', edges=part_lastra.edges.findAt(coordinates=((-self.LASTRA_WIDTH/2, 0, 0), )))
        part_lastra.Set(name='surface-right', edges=part_lastra.edges.findAt(coordinates=((self.LASTRA_WIDTH/2, 0, 0), )))

        # set tutti i nodi esterni, per l'output
        part_lastra.SetByBoolean(name='surface-all', sets=(part_lastra.sets['surface-top'], part_lastra.sets['surface-bottom'],
                                                           part_lastra.sets['surface-left'], part_lastra.sets['surface-right'] ))


        #----------- crea PARTI e SET: PALLA -----------#

        # crea sketch palla, circonferenza con raggio 2.5 mm
        sketch_palla = model.ConstrainedSketch(name='sketch-palla', sheetSize=2*self.PALLA_RADIUS)
        sketch_palla.CircleByCenterPerimeter((0, 0), (self.PALLA_RADIUS, 0))    # crea un cerchio a partire dal centro e da un punto appartenente alla circonferenza

        # crea palla usando lo sketch
        part_palla = model.Part(name='Palla', dimensionality=abaqusConstants.TWO_D_PLANAR, type=abaqusConstants.DEFORMABLE_BODY)
        part_palla.BaseShell(sketch=sketch_palla)

        # crea set che include tutta la palla, per assegnargli il materiale
        part_palla.Set(name='set-all', faces=part_palla.faces.findAt(coordinates=((0, 0, 0), )))

        # crea set per bordo della palla, per impostare l'interaction
        part_palla.Set(name='surface', edges=part_palla.edges.findAt(coordinates=((self.PALLA_RADIUS, 0, 0), )))
        part_palla.Surface(name='surface', end1Edges=part_palla.edges.findAt(coordinates=((self.PALLA_RADIUS, 0, 0), )))


        #----------- MATERIALI -----------#

        material_lastra = model.Material(name='material-lastra')
        material_lastra.Density(table=self.STEEL_DENSITY)
        material_lastra.Elastic(table=self.STEEL_ELASTIC)
        material_lastra.Plastic(table=self.STEEL_PLASTIC)

        material_palla = model.Material(name='material-palla')
        material_palla.Density(table=((self.palla_density, ), ))
        material_palla.Elastic(table=self.STEEL_ELASTIC)



        #----------- crea SEZIONI e ASSEGNA MATERIALI -----------#

        # crea sezione per la lastra e assegnaci la lastra
        model.HomogeneousSolidSection(name='section-lastra', material='material-lastra', thickness=None)
        part_lastra.SectionAssignment(region=part_lastra.sets['set-all'], sectionName='section-lastra')

        # crea sezione per la palla e assegnaci la palla
        model.HomogeneousSolidSection(name='section-palla', material='material-palla', thickness=None)
        part_palla.SectionAssignment(region=part_palla.sets['set-all'], sectionName='section-palla')



        #----------- ASSEMBLY (istanzia e posiziona parti) -----------#

        model.rootAssembly.DatumCsysByDefault(abaqusConstants.CARTESIAN)
        model.rootAssembly.Instance(name='Lastra', part=part_lastra, dependent=abaqusConstants.ON)
        model.rootAssembly.Instance(name='Palla', part=part_palla, dependent=abaqusConstants.ON).translate((self.PALLA_ORIGIN_X, self.PALLA_ORIGIN_Y, 0))
        #model.rootAssembly.regenerate()



        #----------- STEP -----------#

        step_1 = model.ExplicitDynamicsStep(name='Step-1', previous='Initial', description='',
                                            timePeriod=self.TIME_PERIOD, timeIncrementationMethod=abaqusConstants.AUTOMATIC_GLOBAL)

        # specifica quali campi vogliamo in output e la frequenza
        field = model.FieldOutputRequest('F-Output-1', createStepName='Step-1', variables=('S', 'E', 'U', 'COORD'), frequency=self.OUTPUT_FREQUENCY)



        #----------- RIGID BODY CONSTRAINT per la palla -----------#

        # crea reference point nella coordinata dove si trova il centro della palla
        RP_palla_id = model.rootAssembly.ReferencePoint(point=(self.PALLA_ORIGIN_X, self.PALLA_ORIGIN_Y, 0)).id
        RP_palla_region = regionToolset.Region(referencePoints=(model.rootAssembly.referencePoints[RP_palla_id],))

        # assegna rigid body constraint alla palla associato al reference point
        model.RigidBody(name='constraint-palla-rigid-body', refPointRegion=RP_palla_region, bodyRegion=model.rootAssembly.instances['Palla'].sets['set-all'])



        #----------- BOUNDARY CONDITION -----------#

        # encastre per la superficie sotto della lastra
        bc_encastre = model.EncastreBC(name='BC-Encastre', createStepName='Initial', region=model.rootAssembly.instances['Lastra'].sets['surface-bottom'])



        #----------- PREDEFINED FIELD -----------#

        # velocita' iniziale assegnata alla palla tramite predefined field (associato al suo reference point)
        velocity = model.Velocity(name="Velocity", region=RP_palla_region, velocity1=self.speed_x, velocity2=self.speed_y)


        #----------- INTERACTION: surface-to-surface contact -----------#

        # interaction properties
        interaction_properties = model.ContactProperty('IntProp-1')
        interaction_properties.TangentialBehavior(formulation=abaqusConstants.PENALTY, table=((0.5, ), ), maximumElasticSlip=abaqusConstants.FRACTION, fraction=0.005)
        interaction_properties.NormalBehavior(pressureOverclosure=abaqusConstants.HARD)

        model.SurfaceToSurfaceContactExp(name='Int-1', createStepName='Initial', main=model.rootAssembly.instances['Palla'].surfaces['surface'],
                                        secondary=model.rootAssembly.instances['Lastra'].surfaces['surface-top'], sliding=abaqusConstants.FINITE,
                                        interactionProperty='IntProp-1')




        #----------- MESH: lastra -----------#

        # da interfaccia grafica avevo messo element family = "plate strain" ma qua non trovo l'opzione family
        # e per elemCode devo ancora capire cosa significa e quali altre opzioni ci sono
        elem_type_plate_strain = mesh.ElemType(elemLibrary=abaqusConstants.EXPLICIT, elemCode=abaqusConstants.C3D8R)    

        # assegna element type
        #part_lastra.setElementType(regions=(part_lastra.cells, ), elemTypes=(elem_type_plate_strain, ))

        # seed sui lati dx e sx a single bias (cioe' un gradiente con due valori)
        part_lastra.seedEdgeByBias(biasMethod=abaqusConstants.SINGLE, end1Edges=part_lastra.sets['surface-right'].edges, end2Edges=part_lastra.sets['surface-left'].edges,
                                minSize=self.LASTRA_SEED_SX_DX_MIN, maxSize=self.LASTRA_SEED_SX_DX_MAX)

        # seed sui lati sopra e sotto a double bias (cioe' un gradiente con tre valori)
        part_lastra.seedEdgeByBias(biasMethod=abaqusConstants.DOUBLE, centerEdges=(part_lastra.sets['surface-top'].edges[0], part_lastra.sets['surface-bottom'].edges[0]),
                                minSize=self.LASTRA_SEED_TOP_BOTTOM_MIN, maxSize=self.LASTRA_SEED_TOP_BOTTOM_MAX)

        part_lastra.generateMesh()


        #----------- MESH: palla -----------#

        part_palla.seedPart(size=self.PALLA_SEED_SIZE)
        part_palla.generateMesh()


        #----------- JOB -----------#

        job_name = "Job_" + str(self.index)
        job = mdb.Job(name=job_name, model='Model-1')

        # salva input file ("<nome job>.inp")
        if (saveJobInput):
            job.writeInput()

        # submit the job:
        job.submit()
        job.waitForCompletion()
        self.simulationHasRun = True
        

        #----------- SALVA OUTPUT IN FILE CSV -----------#

        if (saveDisplacementCSV or saveStressCSV):

            # Apri output database
            odb = session.openOdb(job_name + '.odb')

            # Prendi l'ultimo frame
            lastFrame = odb.steps['Step-1'].frames[-1]
            
            # Regione di cui vogliamo i valori
            outputRegion = odb.rootAssembly.instances['LASTRA'].nodeSets['SET-ALL']
            
            outputRegionExternal = odb.rootAssembly.instances['LASTRA'].nodeSets['SURFACE-ALL']


            if (saveDisplacementCSV):
                # Ottieni il displacement solo della regione interessata e salvati i valori dentro un array
                displacement = lastFrame.fieldOutputs['U']

                # tutta la lastra
                displacement_all = displacement.getSubset(region=outputRegion)
                displacement_data = []
                for v in displacement_all.values:
                    displacement_data.append( [v.nodeLabel, v.data[0], v.data[1]] )
                displacement_data_np = np.array(displacement_data)
                np.savetxt(str(self.index) + '_output_displacement.csv', displacement_data_np, delimiter=',', comments='')

                # solo la frontiera                
                displacement_external = displacement.getSubset(region=outputRegionExternal)
                displacement_data = []
                for v in displacement_external.values:
                    displacement_data.append( [v.nodeLabel, v.data[0], v.data[1]] )
                displacement_data_np = np.array(displacement_data)
                np.savetxt(str(self.index) + '_output_displacement_external.csv', displacement_data_np, delimiter=',', comments='')
                

            if (saveStressCSV):
                stress = lastFrame.fieldOutputs['S']
                stress = stress.getScalarField(componentLabel='S11')

                stress_data = []
                for v in stress.values:
                    stress_data.append( [v.elementLabel, v.data] )

                stress_data_np = np.array(stress_data)
                np.savetxt(str(self.index) + '_output_stress.csv', stress_data_np, delimiter=',', comments='')



        #----------- SALVA DATABASE -----------#

        # save the Abaqus model to a .cae file
        if (saveDatabase):
            mdb.saveAs(str(self.index) + '.cae')


        #----------- ELIMINA FILE EXTRA GENERATI DA ABAQUS -----------#

        files_ext = ['.jnl','.inp','.res','.lck','.dat','.msg','.sta','.fil','.sim','.stt',
                     '.mdl','.prt','.ipm','.log','.com','.odb_f','.abq', '.pac', '.sel']
        for file_ex in files_ext:
            file_path = job_name + file_ex
            if os.path.exists(file_path):
                os.remove(file_path)

        # rispostati al path precedente
        os.chdir(previous_path)

