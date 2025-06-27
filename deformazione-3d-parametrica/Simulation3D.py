import os
import sys
import time
import abaqusConstants
import mesh
import numpy           as np
import json
import math
import pandas          as pd
import pathlib
    
    
from abaqus      import *
from driverUtils import *
from caeModules  import *



def log(message):
    print(message, file = sys.__stdout__)
    return


class Simulation3D():

    def __init__( self ):

        # PARAMETERS
        self.index          = None
        self.circle_speed   = None
        self.circle_speed_x = None
        self.circle_speed_y = None
        self.circle_speed_z = None
        self.circle_radius = None
        self.circle_impact_angle_x = None
        self.circle_impact_angle_y = None
 
 
         # OBJECT DIMENSION
        self.plate_width         = 40
        self.plate_height        = 2.5
        self.CIRCLE_BASE_RADIUS  = 2.5      # la seed size la calcolo usando questo come riferimento


        # INITIAL POSITIONS
        self.plate_origin_x  = 0
        self.plate_origin_y  = 0
        self.circle_origin_x = 0
        self.circle_origin_y = 0


        # MATERIAL: lead
        self.lead_density = ((1.153e-5,),)
        self.lead_elastic = ((1.4e4, 0.42),)

        # MATERIAL: 304 stainless steel
        self.steel_density = ((8e-6,),)
        self.steel_elastic = ((196.5e3, 0.3),)                # (YOUNG'S MODULUS, POISSON RATIO)
        self.steel_plastic = (
            (215, 0),
            (496.8, 0.0975),
            (687.6, 0.1965),
            (893.6, 0.2955),
            (1086.6, 0.3945)
        )


        # MESH
        self.circle_seed_size          = 1
        self.plate_seed_sides_min      = 0.5
        self.plate_seed_sides_max      = 1
        self.plate_seed_top_bottom_min = 0.5
        self.plate_seed_top_bottom_max = 2


        # MISCELLANEA
        self.time_period      = None                        # SIMULATION ELAPSED TIME
        self.output_frequency = 40                          # FREQUENCY OUTPUT



    def _saveInputDataToFile(self):
        
        inputData = { "index"                 : self.index,
                      "circle_speed_x"        : self.circle_speed_x,
                      "circle_speed_y"        : self.circle_speed_y,
                      "circle_speed_z"        : self.circle_speed_z,
                      "circle_speed"          : self.circle_speed,
                      "circle_impact_angle_x" : self.circle_impact_angle_x,
                      "circle_impact_angle_y" : self.circle_impact_angle_y,
                      "circle_radius"         : self.circle_radius }
                      
        # salvo in un file di nome "<index>_input.json"
        filename = os.path.join( self.new_path, self.folder_name + "_input.json" )
        
        with open( filename, "w") as outfile: 
            json.dump(inputData, outfile)



    def runSimulation( self,
                       CIRCLE_RADIUS,
                       CIRCLE_VELOCITY,
                       ALPHA_Y,
                       ALPHA_X,
                       SIMULATION_ID,
                       SAVEINPUTDATA        = True, 
                       SAVECIRCLEVELOCITY   = True,
                       SAVEDISPLACEMENT     = True, 
                       SAVECOORDINATES      = True,
                       SAVEDATABASE         = True, 
                       SAVEPLATECOORDINATES = False,
                       SAVEJOBINPUT         = False ):
              

        #*************************
        #RESETTING THE ENVIRONMENT
        #*************************   
        Mdb()

        # salva parametri
        self.index = SIMULATION_ID
        self.circle_radius = CIRCLE_RADIUS
        self.circle_speed = CIRCLE_VELOCITY
        self.circle_impact_angle_y = ALPHA_Y
        self.circle_impact_angle_x = ALPHA_X


        # Calcolo le velocita'
        self.circle_speed_y = - CIRCLE_VELOCITY * math.cos(math.radians(ALPHA_Y))
        self.circle_speed_x = CIRCLE_VELOCITY * math.sin(math.radians(ALPHA_Y)) * math.cos(math.radians(ALPHA_X))
        self.circle_speed_z = CIRCLE_VELOCITY * math.sin(math.radians(ALPHA_Y)) * math.sin(math.radians(ALPHA_X))


        self.simulation_time_perc = 0.1            #PERCENTAGE


        # vogliamo che il tempo che ci mette la palla a raggiungere la lastra sia sempre 2/30 secondi
        # sappiamo la velocita', l'angolo, il punto di impatto e il tempo totale, dobbiamo calcolare la posizione
        # iniziale (x e y) della palla

        # Time for the circle to reach the plate, fixed
        self.TIME_TO_IMPACT = 2/30

        # Length of the trajectory that we need for the circle to take the desired time to reach the plate
        self.trajectory = abs(self.TIME_TO_IMPACT * CIRCLE_VELOCITY) + self.circle_radius

        # The initial X and Y of the circle are computed using the desired trajectory length and the angle
        self.circle_origin_y = self.trajectory * math.cos(math.radians(ALPHA_Y)) + self.circle_radius
        self.circle_origin_x = - self.trajectory * math.sin(math.radians(ALPHA_Y)) * math.cos(math.radians(ALPHA_X))
        self.circle_origin_z = - self.trajectory * math.sin(math.radians(ALPHA_Y)) * math.sin(math.radians(ALPHA_X))

        #log("circle x: " + str(self.circle_origin_x))
        #log("circle y: " + str(self.circle_origin_y))


        # Crea cartella (se non esiste) con nome <index>
        self.folder_name   = f'Dynamic_Simulation_{self.index}'
        self.previous_path = os.getcwd()
        self.new_path      = os.path.join( self.previous_path, self.folder_name)
        
        
        
        os.makedirs( self.new_path, 
                     exist_ok = True )
        
        
        # SIMULATION ELAPSED TIME
        self.time_period = self.TIME_TO_IMPACT
        #self.time_period += self.simulation_time_perc*self.time_period
        self.time_period += abs(self.circle_speed_y/15000)
        
        # TEMP
        #self.time_period = 0.07
        
        
        #************************
        # CHECKING FOR INPUT DATA
        #************************
        if ( self.circle_origin_y - self.circle_radius ) <= 0:
            log( 'Circle is too close to the plate.' )
            return (0, False)
            
            
        #***********************
        #CHANGING WORK DIRECTORY
        #***********************
        os.chdir( self.new_path )
        
        
        if SAVEINPUTDATA:
            self._saveInputDataToFile()



        #****************
        #CREATING A MODEL
        #****************
        MODEL_NAME = f'Simulation_{self.index}'
        model      = mdb.Model( name = MODEL_NAME )
    
    
        #***********************
        #DELETING STANDARD MODEL
        #***********************
        del mdb.models['Model-1']



        #----------- crea PARTI e SET: plate -----------#

        # crea sketch plate, rettangolo da 50x4 mm
        sketch_plate = model.ConstrainedSketch( name      = 'sketch-plate', 
                                                 sheetSize = self.plate_width )
                                                 
                                                 
        sketch_plate.rectangle( ( -self.plate_width/2, 0 ), 
                                (  self.plate_width/2, -self.plate_height ) )
                                 

        # crea plate usando lo sketch
        part_plate = model.Part( name           = 'plate', 
                                 dimensionality = abaqusConstants.THREE_D, 
                                 type           = abaqusConstants.DEFORMABLE_BODY )
                                                     
        part_plate.BaseSolidExtrude(sketch = sketch_plate, depth=self.plate_width)


        # set con tutta la lastra, per il materiale
        part_plate.Set( name  = 'set-all', 
                        cells = part_plate.cells )
        
        # crea diversi set per le superfici della plate, per assegnargli una boundary condition (sotto) e per impostare l'interaction (sopra) 
        # e per gestire il seed della mesh
        part_plate.Set( name = 'surface-top',    faces = part_plate.faces.findAt( coordinates = ( (0, 0, self.plate_width/2), ) ) )
        part_plate.Set( name = 'surface-bottom', faces = part_plate.faces.findAt( coordinates = ( (0, -self.plate_height, self.plate_width/2), ) ) )
        part_plate.Set( name = 'surface-west',   faces = part_plate.faces.findAt( coordinates = ( (-self.plate_width/2, -self.plate_height/2, self.plate_width/2), ) ) )
        part_plate.Set( name = 'surface-east',  faces = part_plate.faces.findAt( coordinates = ( (self.plate_width/2, -self.plate_height/2, self.plate_width/2), ) ) )
        part_plate.Set( name = 'surface-north',   faces = part_plate.faces.findAt( coordinates = ( (0, -self.plate_height/2, 0), ) ) )
        part_plate.Set( name = 'surface-south',  faces = part_plate.faces.findAt( coordinates = ( (0, -self.plate_height/2, self.plate_width), ) ) )
        
        # superficie per l'interaction
        part_plate.Surface( name = 'surface-top', side1Faces = part_plate.faces.findAt(coordinates = ( (0, 0, self.plate_width/2), )  ) )

        # set tutte  le superfici esterni, per l'output
        part_plate.Set( name = 'surface-all', faces = part_plate.faces )
        


        #----------- crea PARTI e SET: palla -----------#

        # crea sketch sfera, circonferenza con raggio circle_radius
        sketch_circle = model.ConstrainedSketch( name      = 'sketch-circle', 
                                                 sheetSize = 2*self.CIRCLE_BASE_RADIUS )
                                                 
                                                
        sketch_circle.ArcByCenterEnds( center = (0, 0), 
                                       point1 = (0, self.CIRCLE_BASE_RADIUS),
                                       point2 = (0, -self.CIRCLE_BASE_RADIUS),
                                       direction = abaqusConstants.CLOCKWISE )
        
        sketch_circle.Line( point1 = (0, self.CIRCLE_BASE_RADIUS),
                            point2 = (0, -self.CIRCLE_BASE_RADIUS))
        
        # crea asse di rotazione per la sfera
        sketch_circle_rotation_line = sketch_circle.ConstructionLine( point1 = (0, self.CIRCLE_BASE_RADIUS), point2 = (0, -self.CIRCLE_BASE_RADIUS))
        
        # assegna asse di rotazione
        sketch_circle.assignCenterline(sketch_circle_rotation_line)

        # crea palla usando lo sketch
        part_circle = model.Part( name           = 'circle', 
                                  dimensionality = abaqusConstants.THREE_D, 
                                  type           = abaqusConstants.DEFORMABLE_BODY )
                                                 
        part_circle.BaseSolidRevolve( sketch = sketch_circle, angle = 360 )


        # crea datum planes per partizionare la superficie della sfera in 8 (serve dopo per il meshing)
        part_circle_xy_plane = part_circle.DatumPlaneByPrincipalPlane(principalPlane = abaqusConstants.XYPLANE, offset = 0.0)
        part_circle_xz_plane = part_circle.DatumPlaneByPrincipalPlane(principalPlane = abaqusConstants.XZPLANE, offset = 0.0)
        part_circle_yz_plane = part_circle.DatumPlaneByPrincipalPlane(principalPlane = abaqusConstants.YZPLANE, offset = 0.0)

        # partiziona superficie
        part_circle.PartitionFaceByDatumPlane(faces = part_circle.faces, datumPlane = part_circle.datums[part_circle_xy_plane.id])
        part_circle.PartitionFaceByDatumPlane(faces = part_circle.faces, datumPlane = part_circle.datums[part_circle_xz_plane.id])
        part_circle.PartitionFaceByDatumPlane(faces = part_circle.faces, datumPlane = part_circle.datums[part_circle_yz_plane.id])

        # set con tutta la palla, per il materiale e per il reference point
        part_circle.Set( name  = 'set-all', 
                        cells = part_circle.cells )

        # crea set per la superficie della palla, per impostare l'interaction
        part_circle.Set( name = 'surface', faces = part_circle.faces )    
        part_circle.Surface( name = 'surface', side1Faces = part_circle.faces )



        #----------- MATERIALI -----------#

        material_plate = model.Material( name = 'material-plate' )
        material_plate.Density( table = self.steel_density )
        material_plate.Elastic( table = self.steel_elastic )
        material_plate.Plastic( table = self.steel_plastic )
        
        
        material_circle = model.Material( name = 'material-circle' )
        material_circle.Density( table = self.lead_density )
        material_circle.Elastic( table = self.lead_elastic )



        #----------- crea SEZIONI e ASSEGNA MATERIALI -----------#

        # CREA SEZIONE PER LA LASTRA E ASSEGNACI LA LASTRA
        model.HomogeneousSolidSection( name      = 'section-plate', 
                                       material  = 'material-plate', 
                                       thickness = None )
                                       
        part_plate.SectionAssignment( region      = part_plate.sets['set-all'], 
                                      sectionName = 'section-plate' )       

        # CREA SEZIONE PER LA PALLA E ASSEGNACI LA PALLA
        model.HomogeneousSolidSection( name      = 'section-circle', 
                                       material  = 'material-circle', 
                                       thickness = None )
        
        
        part_circle.SectionAssignment( region      = part_circle.sets['set-all'], 
                                       sectionName = 'section-circle' )





        #----------- ASSEMBLY (istanzia e posiziona parti) -----------#

        model.rootAssembly.DatumCsysByDefault(abaqusConstants.CARTESIAN)
        model.rootAssembly.Instance( name      = 'plate', 
                                     part      = part_plate, 
                                     dependent = abaqusConstants.ON ).translate((0, 0, - self.plate_width/2))
                                     
                                     
        model.rootAssembly.Instance( name      = 'circle', 
                                     part      = part_circle, 
                                     dependent = abaqusConstants.ON).translate(( self.circle_origin_x, self.circle_origin_y, self.circle_origin_z ))



        #----------- STEP -----------#

        step_1 = model.ExplicitDynamicsStep( name                     = 'Step-1', 
                                             previous                 = 'Initial', description='',
                                             timePeriod               = self.time_period, 
                                             timeIncrementationMethod = abaqusConstants.AUTOMATIC_GLOBAL )
    
    
        # specifica quali campi vogliamo in output e la frequenza
        field = model.FieldOutputRequest( name           = 'F-Output-1', 
                                          createStepName = 'Step-1', 
                                          variables      = ('S', 'E', 'U', 'COORD'), 
                                          frequency      = self.output_frequency )
        


        #----------- RIGID BODY CONSTRAINT per la palla -----------#

        # crea reference point nella coordinata dove si trova il centro della palla
        RP_circle_id     = model.rootAssembly.ReferencePoint( point = ( self.circle_origin_x, self.circle_origin_y, self.circle_origin_z) ).id
        
        RP_circle_region = regionToolset.Region( referencePoints = ( model.rootAssembly.referencePoints[RP_circle_id], ) )
        RP_circle_set    = model.rootAssembly.Set( name = "circle-rp", referencePoints = ( model.rootAssembly.referencePoints[RP_circle_id], ))
        
        
        # assegna rigid body constraint alla palla associato al reference point
        model.RigidBody( name           = 'constraint-circle-rigid-body', 
                         refPointRegion = RP_circle_region, 
                         bodyRegion     = model.rootAssembly.instances['circle'].sets['set-all'] )


        #----------- FILTER per fermare l'analisi quando la palla si ferma o rimbalza verso l'alto -----------#
        
        # crea filtro
        filter = model.ButterworthFilter( name           = "Filter-1",
                                        # cutoffFrequency = frequency above which the filter attenuates at least half of the input signal
                                        # => l'ho scelta a caso alta, da rivedere
                                         cutoffFrequency = 10000,
                                         operation       = abaqusConstants.MAX,
                                         limit           = 0,         # se la palla ha velocita' verticale zero o si e' fermata o sta per rimbalzare
                                         halt            = True )      # per far fermare l'analisi quando il valore limit e' raggiunto
    
        # aggiungi una history output request per la velocita' verticale della palla, in modo da potergli applicare un filtro
        model.HistoryOutputRequest( name           = 'H-Output-Circle-V2', 
                                    createStepName = 'Step-1', 
                                    region         = RP_circle_set,
                                    variables      = ('V2',),        # velocita' verticale
                                    frequency      = 200,
                                    filter         = "Filter-1" )
        

        #----------- BOUNDARY CONDITION -----------#

        # crea un set con tutti i lati della lastra
        part_plate.SetByBoolean( name = 'surface-sides', 
                                 sets = ( part_plate.sets['surface-north'],  part_plate.sets['surface-south'],
                                          part_plate.sets['surface-west'],  part_plate.sets['surface-east'] ) )


        bc_sides = model.DisplacementBC( name           = 'FixedBC', 
                                        createStepName = 'Initial', 
                                        region         = model.rootAssembly.instances['plate'].sets['surface-sides'], 
                                        u1 = 0.0, 
                                        u2 = 0.0, 
                                        u3 = 0.0 )


        #----------- PREDEFINED FIELD -----------#

        # velocita' iniziale assegnata alla palla tramite predefined field (associato al suo reference point)
        velocity = model.Velocity( name      = "Velocity", 
                                   region    = RP_circle_region, 
                                   velocity1 = self.circle_speed_x, 
                                   velocity2 = self.circle_speed_y,
                                   velocity3 = self.circle_speed_z )



        #----------- INTERACTION: surface-to-surface contact -----------#

        # interaction properties
        interaction_properties = model.ContactProperty('IntProp-1')
        interaction_properties.TangentialBehavior( formulation        = abaqusConstants.PENALTY, 
                                                   table              = ((0.5, ), ), 
                                                   maximumElasticSlip = abaqusConstants.FRACTION, 
                                                   fraction           = 0.005 )
        
        
        interaction_properties.NormalBehavior( pressureOverclosure = abaqusConstants.HARD )

        model.SurfaceToSurfaceContactExp( name                = 'Int-1', 
                                          createStepName      = 'Initial', 
                                          main                = model.rootAssembly.instances['circle'].surfaces['surface'],
                                          secondary           = model.rootAssembly.instances['plate'].surfaces['surface-top'], 
                                          sliding             = abaqusConstants.FINITE,
                                          interactionProperty = 'IntProp-1' )



        #----------- MESH: plate -----------#  

        # LIBRERIA ELEMENTI 3D:
        # https://classes.engineering.wustl.edu/2009/spring/mase5513/abaqus/docs/v6.6/books/usb/default.htm?startat=pt06ch22s01ael03.html#usb-elm-e3delem

        edge_top_north = part_plate.edges.findAt((0, 0, 0))
        edge_top_south = part_plate.edges.findAt((0, 0, self.plate_width))
        edge_top_east = part_plate.edges.findAt((self.plate_width/2, 0, self.plate_width/2))
        edge_top_west = part_plate.edges.findAt((-self.plate_width/2, 0, self.plate_width/2))

        edge_bottom_north = part_plate.edges.findAt((0, -self.plate_height, 0))
        edge_bottom_south = part_plate.edges.findAt((0, -self.plate_height, self.plate_width))
        edge_bottom_east = part_plate.edges.findAt((self.plate_width/2, -self.plate_height, self.plate_width/2))
        edge_bottom_west = part_plate.edges.findAt((-self.plate_width/2, -self.plate_height, self.plate_width/2))

        edge_ne = part_plate.edges.findAt((self.plate_width/2, -self.plate_height/2, 0))
        edge_nw = part_plate.edges.findAt((-self.plate_width/2, -self.plate_height/2, 0))
        edge_se = part_plate.edges.findAt((self.plate_width/2, -self.plate_height/2, self.plate_width))
        edge_sw = part_plate.edges.findAt((-self.plate_width/2, -self.plate_height/2, self.plate_width))

        #log(edge_ne)
        #return
        
        # seed sugli edge orizzontali a double bias (cioe' un gradiente con tre valori)
        part_plate.seedEdgeByBias( biasMethod   = abaqusConstants.DOUBLE, 
                                    centerEdges = (edge_top_north, edge_top_south, edge_top_east, edge_top_west,
                                                   edge_bottom_north, edge_bottom_south, edge_bottom_east, edge_bottom_west),
                                    minSize     = self.plate_seed_top_bottom_min, 
                                    maxSize     = self.plate_seed_top_bottom_max )
        

        
        # seed sugli edge verticali a single bias (cioe' un gradiente con due valori)
        part_plate.seedEdgeByBias( biasMethod = abaqusConstants.SINGLE, 
                                   end2Edges = (edge_ne, edge_sw), 
                                   end1Edges  = (edge_nw, edge_se), 
                                   minSize    = self.plate_seed_sides_min, 
                                   maxSize    = self.plate_seed_sides_max )

        part_plate.generateMesh()


        #----------- MESH: circle -----------#

        part_circle.seedPart( size = self.circle_seed_size )

        # questa parte si puo' meshare solo se gli elementi hanno una forma tetraedrica, e gli va detto esplicitamente
        part_circle.setMeshControls(regions = part_circle.cells, elemShape = abaqusConstants.TET)

        part_circle.generateMesh()


        # scalo la mesh
        scale = self.circle_radius / self.CIRCLE_BASE_RADIUS

        for n in range(0,len(part_circle.nodes)):
            coords = part_circle.nodes[n].coordinates

            # scale the nodes
            new_coords = [coord * scale for coord in coords]

            # change the nodes of current part
            part_circle.editNode(coordinate1=new_coords[0], coordinate2=new_coords[1],coordinate3=new_coords[2],
                nodes=part_circle.nodes[n])


        '''
        # printa quanti nodi ha la palla
        log("radius " + str(self.circle_radius))
        log("quantita' nodi palla:" + str(len(part_circle.nodes)))
        '''



        #----------- JOB -----------#

        JOB_NAME = "Simulation_Job_" + str(self.index)
        job      = mdb.Job( name  = JOB_NAME, 
                            model = MODEL_NAME )
        
        
        #****************************************
        # SAVING INPUT FILE AS ("<NOME JOB>.INP")
        #****************************************
        if SAVEJOBINPUT:
            job.writeInput()




        #*******************
        # SUBMITTING THE JOB:
        #*******************
        #log("submitting the job")
        job.submit()
        job.waitForCompletion()



        # Check if simulation has completed, i.e. if the circle has stopped
        circle_region = session.openOdb(JOB_NAME + '.odb').steps['Step-1'].historyRegions['Node ASSEMBLY.1']
        circle_v2Data = circle_region.historyOutputs['V2_FILTER-1'].data
        (simulation_length, circle_final_velocity) = circle_v2Data[-1]

        # Variable that says whether simulation has completed
        simulation_completed = (circle_final_velocity >= 0.0)



        #----------- SAVING OUTPUT IN FILE CSV -----------#

        # LOADING DATABASE
        odb = session.openOdb(JOB_NAME + '.odb')

        # GETTING THE FRAMES
        firstFrame = odb.steps['Step-1'].frames[0]
        lastFrame = odb.steps['Step-1'].frames[-1]


        # Frame 1/30 secondi prima dell'impatto
        frameOne30BeforeImpact = None

        for frame in odb.steps['Step-1'].frames:
            # visto che la simulazione e' fatta nel dominio del tempo (il campo domain di Step e' AbaqusConstants.TIME),
            # allora frameValue e' il tempo del frame
            if (frame.frameValue >= 1/30):
                #log("found frame one")
                frameOne30BeforeImpact = frame
                break

        if (frameOne30BeforeImpact == None):
            log("frame one not found")


        # REGIONS OF INTEREST
        #outputRegion         = odb.rootAssembly.instances['PLATE'].nodeSets['SET-ALL']
        outputRegionExternal = odb.rootAssembly.instances['PLATE'].nodeSets['SURFACE-ALL']
        #outputRegionCircle = odb.rootAssembly.instances['CIRCLE'].nodeSets['SET-ALL']
        outputRegionCircleExternal = odb.rootAssembly.instances['CIRCLE'].nodeSets['SURFACE']


        # SAVING CIRCLE VELOCITY
        if SAVECIRCLEVELOCITY:
            
            region = odb.steps['Step-1'].historyRegions['Node ASSEMBLY.1']
            v2Data = region.historyOutputs['V2_FILTER-1'].data
            
            velocity_df = pd.DataFrame( { 'Time'     : [ time for time, _ in v2Data ] ,
                                        'Velocity' : [ v2   for _, v2   in v2Data ] } )
            
            velocity_output_filename = os.path.join(self.new_path, str(self.index) + '_circle_velocity_y.csv')
        
        
            velocity_df.to_csv(velocity_output_filename, index = False)



        # SAVING COORDINATES OF PLATE
        if SAVEPLATECOORDINATES:

            # ****** Initial coordinates ******
            coordinates_plate = firstFrame.fieldOutputs['COORD'].getSubset(region = outputRegionExternal)
            coordinates_plate_df = pd.DataFrame( { 'Id'       : [ values.nodeLabel for values in coordinates_plate.values ],
                                                    'X_Coord' : [ values.data[0]   for values in coordinates_plate.values ],
                                                    'Y_Coord' : [ values.data[1]   for values in coordinates_plate.values ],
                                                    'Z_Coord' : [ values.data[2]   for values in coordinates_plate.values ] } )
            coordinate_plate_filename = os.path.join(self.new_path, 'plate_initial_coordinates.csv')
            coordinates_plate_df.to_csv(coordinate_plate_filename, index = False)



        # SAVING COORDINATES OF SPHERE
        if SAVECOORDINATES:

            # ****** Initial coordinates = 2/30 seconds before impact ******
            coordinates_circle_1 = firstFrame.fieldOutputs['COORD'].getSubset(region = outputRegionCircleExternal)
            coordinates_circle_1_df = pd.DataFrame( { 'Id'      : [ values.nodeLabel for values in coordinates_circle_1.values ],
                                                      'X_Coord' : [ values.data[0]   for values in coordinates_circle_1.values ],
                                                      'Y_Coord' : [ values.data[1]   for values in coordinates_circle_1.values ],
                                                      'Z_Coord' : [ values.data[2]   for values in coordinates_circle_1.values ] } )
            coordinate_circle_1_filename = os.path.join(self.new_path, str(self.index) + '_input_coordinates_circle_1.csv')
            coordinates_circle_1_df.to_csv(coordinate_circle_1_filename, index = False)


            # ****** Coordinates 1/30 seconds before impact ******
            if (frameOne30BeforeImpact != None):
                coordinates_circle_2 = frameOne30BeforeImpact.fieldOutputs['COORD'].getSubset( region = outputRegionCircleExternal )                
                coordinates_circle_2_df = pd.DataFrame( { 'Id'    : [ values.nodeLabel for values in coordinates_circle_2.values ],
                                                        'X_Coord' : [ values.data[0]   for values in coordinates_circle_2.values ],
                                                        'Y_Coord' : [ values.data[1]   for values in coordinates_circle_2.values ],
                                                        'Z_Coord' : [ values.data[2]   for values in coordinates_circle_2.values ] } )
                coordinate_circle_2_filename = os.path.join(self.new_path, str(self.index) + '_input_coordinates_circle_2.csv')
                coordinates_circle_2_df.to_csv(coordinate_circle_2_filename, index = False)




        # SAVING PLATE DISPLACEMENTS
        if SAVEDISPLACEMENT:
            # solo la frontiera                
            displacement_external = lastFrame.fieldOutputs['U'].getSubset( region = outputRegionExternal )
            
            displacement_external_df = pd.DataFrame( { 'Id'     : [ values.nodeLabel for values in displacement_external.values ],
                                                        'X_Disp' : [ values.data[0]   for values in displacement_external.values ],
                                                        'Y_Disp' : [ values.data[1]   for values in displacement_external.values ],
                                                        'Z_Disp' : [ values.data[2]   for values in displacement_external.values ] } )
            
            displacement_external_output_filename = os.path.join( self.new_path, str(self.index) + '_output_displacement_external.csv' )

            displacement_external_df.to_csv( displacement_external_output_filename, index = False )



        #----------- SAVING DATABASE -----------#
        
        if SAVEDATABASE:
            mdb.saveAs(str(self.index) + '.cae')


        #----------- ELIMINA FILE EXTRA GENERATI DA ABAQUS -----------#

        files_ext = [ '.jnl',   '.sel', '.res', 
                      '.lck',   '.dat', '.msg', 
                      '.sta',   '.fil', '.sim',
                      '.stt',   '.mdl', '.prt', 
                      '.ipm',   '.log', '.com', 
                      '.odb_f', '.abq', '.pac',
                      '.rpy' ]

        if (not SAVEJOBINPUT):
            files_ext.append('.inp')              
        
        for file_ex in files_ext:
            
            file_path = JOB_NAME + file_ex

            if os.path.exists(file_path):
                os.remove(file_path)

        if os.path.exists("abq.app_cache"):
            os.remove("abq.app_cache")


        #******************************
        # RETURNING TO PARENT DIRECTORY
        #******************************
        os.chdir( self.previous_path )

        return (simulation_length, simulation_completed)



'''
########## DA TOGLIERE ##########

idx = 3
radius = 4.5
velocity = 8000
alpha_Y = 0 #38
alpha_X = 0 #-180

start = time.time()

sim = Simulation3D()
(simulation_length, simulation_completed) = sim.runSimulation(
    CIRCLE_RADIUS   = radius,
    CIRCLE_VELOCITY = velocity,
    ALPHA_Y         = alpha_Y,
    ALPHA_X         = alpha_X,
    SUMULATION_ID   = idx,
    SAVEPLATECOORDINATES = True
)

simulation_time = str(time.time() - start)

log("sim length: " + str(simulation_length))
log("completed: " + str(simulation_completed))
log("sim total time: " + simulation_time)
'''