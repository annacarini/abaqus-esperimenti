import os
import sys
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

    def __init__( self, circle_radius ):

        # PARAMETERS
        self.index          = None
        self.circle_speed_x = None
        self.circle_speed_y = None
        self.circle_speed_z = None
        self.circle_radius = circle_radius
        self.circle_impact_angle_x = None
        self.circle_impact_angle_y = None
 
 
         # OBJECT DIMENSION
        self.plate_width         = 50
        self.plate_height        = 4


        # INITIAL POSITIONS
        self.plate_origin_x  = 0
        self.plate_origin_y  = 0
        self.circle_origin_x = 0
        self.circle_origin_y = 0


        # MATERIALS
        self.circle_density = 2.7E-4
        self.steel_density = ((8e-6, ),)
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
        self.plate_seed_sx_dx_min      = 0.2
        self.plate_seed_sx_dx_max      = 1.2
        self.plate_seed_top_bottom_min = 0.2
        self.plate_seed_top_bottom_max = 2


        # MISCELLANEA
        self.time_period      = None                        # SIMULATION ELAPSED TIME
        self.output_frequency = 40                          # FREQUENCY OUTPUT




    def runSimulation( self,
                       CIRCLE_VELOCITY,
                       ALPHA_Y,
                       ALPHA_X,
                       SUMULATION_ID,
                       SAVEINPUTDATA      = True, 
                       SAVECIRCLEVELOCITY = True,
                       SAVEDISPLACEMENT   = True, 
                       SAVEEDGES          = True,
                       SAVECOORDINATES    = True,
                       SAVESTRESS         = False, 
                       SAVEDATABASE       = False, 
                       SAVEJOBINPUT       = False ):
              

        #*************************
        #RESETTING THE ENVIRONMENT
        #*************************   
        Mdb()


        self.index                 = SUMULATION_ID

        # Calcolo le velocita'
        self.circle_speed_y        = - CIRCLE_VELOCITY * math.cos(math.radians(ALPHA_Y))
        self.circle_speed_x        = CIRCLE_VELOCITY * math.sin(math.radians(ALPHA_Y)) * math.cos(math.radians(ALPHA_X))
        self.circle_speed_z        = CIRCLE_VELOCITY * math.sin(math.radians(ALPHA_Y)) * math.sin(math.radians(ALPHA_X))

        self.circle_impact_angle_y   = ALPHA_Y
        self.circle_impact_angle_x   = ALPHA_X

        self.simulation_time_perc  = 0.1            #PERCENTAGE


        # vogliamo che il tempo che ci mette la palla a raggiungere la lastra sia sempre 2/30 secondi
        # sappiamo la velocita', l'angolo, il punto di impatto e il tempo totale, dobbiamo calcolare la posizione
        # iniziale (x e y) della palla

        # Time for the circle to reach the plate, fixed
        self.TIME_TO_IMPACT = 2/30

        # Length of the trajectory that we need for the circle to take the desired time to reach the plate
        #self.trajectory = abs(self.TIME_TO_IMPACT * CIRCLE_VELOCITY) + self.circle_radius
        self.trajectory = 3

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
        self.time_period = 0.01
        
        
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
        
        
        #if SAVEINPUTDATA:
        #    self._saveInputDataToFile()


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
                                                 sheetSize = 2*self.circle_radius )
                                                 
                                                
        sketch_circle.ArcByCenterEnds( center = (0, 0), 
                                       point1 = (0, self.circle_radius),
                                       point2 = (0, -self.circle_radius),
                                       direction = abaqusConstants.CLOCKWISE )
        
        sketch_circle.Line( point1 = (0, self.circle_radius),
                            point2 = (0, -self.circle_radius))
        
        # crea asse di rotazione per la sfera
        sketch_circle_rotation_line = sketch_circle.ConstructionLine( point1 = (0, self.circle_radius), point2 = (0, -self.circle_radius))
        
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
        material_circle.Density( table = ( ( self.circle_density, ), ) )
        material_circle.Elastic( table = self.steel_elastic )



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
        # TODO



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


        #log(part_plate.edges.findAt((self.plate_width/2, -self.plate_height/2, 0)))

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
                                   minSize    = self.plate_seed_sx_dx_min, 
                                   maxSize    = self.plate_seed_sx_dx_max )


        part_plate.generateMesh()



        #----------- MESH: circle -----------#

        part_circle.seedPart( size = self.circle_seed_size )

        # questa parte si puo' meshare solo se gli elementi hanno una forma tetraedrica, e gli va detto esplicitamente
        part_circle.setMeshControls(regions = part_circle.cells, elemShape = abaqusConstants.TET)

        part_circle.generateMesh()




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
        #job.submit()
        #job.waitForCompletion()




        #----------- SAVING DATABASE -----------#
        
        #***************************************
        # SAVING THE ABAQUS MODEL TO A .CAE FILE
        #***************************************
        if SAVEDATABASE:
            mdb.saveAs(str(self.index) + '.cae')






########## DA TOGLIERE ##########

idx = 1
radius = 2.5
velocity = 1000
alpha_Y = 0 #60
alpha_X = 0 #45

sim = Simulation3D( radius )
sim.runSimulation(
    CIRCLE_VELOCITY = velocity,
    ALPHA_Y         = alpha_Y,
    ALPHA_X         = alpha_X,
    SUMULATION_ID   = idx,
    SAVEDATABASE    = True
)