import os
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
from matplotlib  import pyplot as plt
    
    
def plotPlatePoints( simulation_folder, 
                     onlyExternal = False, 
                     frameIndex   = -1 ):

    job_folder = pathlib.Path( simulation_folder )
    job_path   = list( job_folder.glob( '*.odb' ) )
    job_path   = pathlib.Path( simulation_folder ) / job_path[0]
    
    if not job_path.exists():
        print( f'Database file does not exist.' )
        
        
    odb = session.openOdb( job_path.as_posix() )

    if onlyExternal:
        outputRegion = odb.rootAssembly.instances['PLATE'].nodeSets['SURFACE-ALL']
        
    else:
        outputRegion = odb.rootAssembly.instances['PLATE'].nodeSets['SET-ALL']


    frame  = odb.steps['Step-1'].frames[frameIndex]
    points = frame.fieldOutputs['COORD']

    points = points.getSubset( region = outputRegion )
    
    points_coords_df = pd.DataFrame( { 'Id'      : [ v.nodeLabel for v in points.values ],
                                       'X_Coord' : [ v.data[0]  for v in points.values ],
                                       'Y_Coord' : [ v.data[1]  for v in points.values ]  } )
    
    xs = points_coords_df.loc[:, 'X_Coord']
    ys = points_coords_df.loc[:, 'Y_Coord']
    
    fig = plt.figure()
    
    plt.scatter(xs, ys)
    plt.title("Simulation, Frame " + str(frameIndex))
    
    

class Simulation2D():

    def __init__( self, 
                  circle_density ):

        # PARAMETERS
        self.index          = None
        self.circle_speed_x = None
        self.circle_speed_y = None
        self.circle_density = circle_density
        self.circle_impact_angle = None
 
 
         # OBJECT DIMENSION
        self.plate_width         = 50
        self.plate_height        = 4
        self.circle_radius       = 2.5


        # INITIAL POSITIONS
        self.plate_origin_x  = 0
        self.plate_origin_y  = 0
        self.circle_origin_x = 0
        self.circle_origin_y = 0


        # MATERIAL
        self.steel_density = ((7.83e-7, ),)
        self.steel_elastic = ((200e3, 0.3),)                # (YOUNG'S MODULUS, POISSON RATIO)
        self.steel_plastic = ((350, 0), (500, 0.8),)


        # MESH
        self.circle_seed_size          = 1
        self.plate_seed_sx_dx_min      = 0.2
        self.plate_seed_sx_dx_max      = 1.2
        self.plate_seed_top_bottom_min = 0.2
        self.plate_seed_top_bottom_max = 2


        # MISCELLANEA
        self.time_period      = None                        # SIMULATION ELAPSED TIME
        self.output_frequency = 40                          # FREQUENCY OUTPUT


    def _saveInputDataToFile(self):
        
        inputData = { "index"               : self.index,
                      "density"             : self.circle_density,
                      "circle_speed_x"      : self.circle_speed_x,
                      "circle_speed_y"      : self.circle_speed_y,
                      "circle_impact_angle" : self.circle_impact_angle }
                      
        # salvo in un file di nome "<index>_input.json"
        filename = os.path.join( self.new_path, self.folder_name + "_input.json" )
        with open( filename, "w") as outfile: 
            
            json.dump(inputData, outfile)
            
            
    def runSimulation( self,
                       CIRCLE_ORIGIN_X,
                       CIRCLE_ORIGIN_Y,
                       CIRCLE_VELOCITY,
                       ALPHA,
                       SUMULATION_ID,
                       SAVEINPUTDATA      = True, 
                       SAVECIRCLEVELOCITY = True,
                       SAVEDISPLACEMENT   = True, 
                       SAVEINITIALCOORD   = False,
                       SAVESTRESS         = True, 
                       SAVEDATABASE       = False, 
                       SAVEJOBINPUT       = False ):
                           
                           
        #*************************
        #RESETTING THE ENVIRONMENT
        #*************************   
        Mdb()
        
        
        # spostati dentro la cartella folder_name
        self.index                 = SUMULATION_ID
        self.circle_speed_x        = +CIRCLE_VELOCITY*math.sin( math.radians( ALPHA ) )
        self.circle_speed_y        = -CIRCLE_VELOCITY*math.cos( math.radians( ALPHA ) )
        self.circle_origin_x       = CIRCLE_ORIGIN_X
        self.circle_origin_y       = CIRCLE_ORIGIN_Y
        self.circle_impact_angle   = ALPHA
        self.circle_plate_distance = ( self.circle_origin_y - self.circle_radius )
        self.simulation_time_perc  = 0.1                                                                                    #PERCENTAGE
        self.translation           = self.circle_origin_y/math.cos( math.radians( ALPHA ) ) if ALPHA != 0 else 0
        self.translation           = self.translation*math.sin(  math.radians( ALPHA ) )    if ALPHA != 0 else 0
        self.trajectory            = math.sqrt( (self.circle_origin_y - self.circle_radius)*( self.circle_origin_y - self.circle_radius ) + 
                                                self.translation*self.translation )
        
        # Crea cartella (se non esiste) con nome <index>
        self.folder_name   = f'Dynamic_Simulation_{self.index}'
        self.previous_path = os.getcwd()
        self.new_path      = os.path.join( self.previous_path, self.folder_name)
        
        
        
        os.makedirs( self.new_path, 
                     exist_ok = True )
        
        
        # SIMULATION ELAPSED TIME
        self.time_period  = abs( self.trajectory / CIRCLE_VELOCITY )
        #self.time_period += self.simulation_time_perc*self.time_period
        self.time_period += abs(self.circle_speed_y/15000)
        
    
        message = f'New folder name : {self.new_path}'
        print( len(message)*'*' )
        print( message )
        # print( f"Y coordinate of the circle's center...: {self.circle_origin_y:8.4f}" )
        # print( f'Translation...........................: {self.translation:8.4f}' )
        print( len(message)*'*' )
        
        
        #************************
        # CHECKING FOR INPUT DATA
        #************************
        if ( self.circle_origin_y - self.circle_radius ) <= ( self.plate_height/2 ):
            
            print( 'Circle is too close to the plate.' )
            return
            
            
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

        # crea sketch plate, rettangolo da 50x6 mm
        sketch_plate = model.ConstrainedSketch( name      = 'sketch-plate', 
                                                 sheetSize = self.plate_width )
                                                 
                                                 
        sketch_plate.rectangle( ( -self.plate_width/2, 0 ), 
                                (  self.plate_width/2, -self.plate_height ) )
                                 

        # crea plate usando lo sketch
        part_plate = model.Part( name           = 'plate', 
                                 dimensionality = abaqusConstants.TWO_D_PLANAR, 
                                 type           = abaqusConstants.DEFORMABLE_BODY )
                                  
                                  
        part_plate.BaseShell( sketch = sketch_plate )
        
        
        # crea set che include tutta la plate, per assegnargli il materiale
        part_plate.Set( name  = 'set-all', 
                        faces = part_plate.faces.findAt( coordinates = ( (0, 0, 0), ) ) )
                         

        # crea diversi set per le superfici della plate, per assegnargli una boundary condition (sotto) e per impostare l'interaction (sopra) 
        # e per gestire il seed della mesh
        part_plate.Set( name = 'surface-top',    edges = part_plate.edges.findAt( coordinates = ( (0,                   0, 0), ) ) )
        part_plate.Set( name = 'surface-bottom', edges = part_plate.edges.findAt( coordinates = ( (0,                  -self.plate_height, 0), ) ) )
        part_plate.Set( name = 'surface-left',   edges = part_plate.edges.findAt( coordinates = ( (-self.plate_width/2, 0,                   0), ) ) )
        part_plate.Set( name = 'surface-right',  edges = part_plate.edges.findAt( coordinates = ( (self.plate_width/2,  0,                   0), ) ) )
        part_plate.Surface( name = 'surface-top', end1Edges = part_plate.edges.findAt(coordinates = ( (0,                   0, 0), )  ) )

        # set tutti i nodi esterni, per l'output
        part_plate.SetByBoolean( name = 'surface-all', 
                                 sets = ( part_plate.sets['surface-top'],  part_plate.sets['surface-bottom'],
                                          part_plate.sets['surface-left'],  part_plate.sets['surface-right'] ) )


        #----------- crea PARTI e SET: circle -----------#

        # crea sketch circle, circonferenza con raggio 2.5 mm
        sketch_circle = model.ConstrainedSketch( name      = 'sketch-circle', 
                                                 sheetSize = 2*self.circle_radius )
                                                 
                                                 
        sketch_circle.CircleByCenterPerimeter( center = (0, 0), 
                                               point1 = (self.circle_radius, 0) )
        
        
        # crea palla usando lo sketch
        part_circle = model.Part( name           = 'circle', 
                                  dimensionality = abaqusConstants.TWO_D_PLANAR, 
                                  type           = abaqusConstants.DEFORMABLE_BODY )
                                  
                                  
        part_circle.BaseShell( sketch = sketch_circle )


        # crea set che include tutta la palla, per assegnargli il materiale
        part_circle.Set( name  = 'set-all', 
                         faces = part_circle.faces.findAt( coordinates = ((0, 0, 0), )))


        # crea set per bordo della palla, per impostare l'interaction
        part_circle.Set( name  =  'surface', 
                         edges = part_circle.edges.findAt( coordinates = ((self.circle_radius, 0, 0), )))
                         
                         
        part_circle.Surface( name      = 'surface', 
                             end1Edges = part_circle.edges.findAt( coordinates = ((self.circle_radius, 0, 0), )))


        #----------- MATERIALI -----------#

        material_plate = model.Material( name = 'material-plate' )
        material_plate.Density( table = self.steel_density )
        material_plate.Elastic( table = self.steel_elastic )
        material_plate.Plastic( table = self.steel_plastic )
        
        
        material_circle = model.Material( name = 'material-circle' )
        material_circle.Density( table = ( ( self.circle_density, ), ) )
        material_circle.Elastic( table = self.steel_elastic )
        
        
        #----------- crea SEZIONI e ASSEGNA MATERIALI -----------#

        # CREA SEZIONE PER LA PLATE E ASSEGNACI LA PLATE
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
                                     dependent = abaqusConstants.ON )
                                     
                                     
        model.rootAssembly.Instance( name      = 'circle', 
                                     part      = part_circle, 
                                     dependent = abaqusConstants.ON).translate( ( ( - self.translation ), self.circle_origin_y, 0 ) )
                                     
                                     
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
        
        
        #----------- RIGID BODY CONSTRAINT per la circle -----------#

        # crea reference point nella coordinata dove si trova il centro della palla
        RP_circle_id     = model.rootAssembly.ReferencePoint( point = ( self.circle_origin_x - self.translation, self.circle_origin_y, 0) ).id
        
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


        bc_left = model.DisplacementBC( name           = 'FixedBC_Left', 
                                        createStepName = 'Initial', 
                                        region         = model.rootAssembly.instances['plate'].sets['surface-left'], 
                                        u1             = 0.0, 
                                        u2             = 0.0 )
                                                 
                                                 
        bc_right = model.DisplacementBC( name           = 'FixedBC_Right', 
                                         createStepName = 'Initial', 
                                         region         = model.rootAssembly.instances['plate'].sets['surface-right'], 
                                         u1             = 0.0, 
                                         u2             = 0.0 )


        #----------- PREDEFINED FIELD -----------#

        # velocita' iniziale assegnata alla palla tramite predefined field (associato al suo reference point)
        velocity = model.Velocity( name      = "Velocity", 
                                   region    = RP_circle_region, 
                                   velocity1 = self.circle_speed_x, 
                                   velocity2 = self.circle_speed_y )


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

        # da interfaccia grafica avevo messo element family = "plate strain" ma qua non trovo l'opzione family
        # e per elemCode devo ancora capire cosa significa e quali altre opzioni ci sono
        elem_type_plate_strain = mesh.ElemType( elemLibrary = abaqusConstants.EXPLICIT, 
                                                elemCode    = abaqusConstants.C3D8R )    

        # assegna element type
        #part_plate.setElementType(regions=(part_plate.cells, ), elemTypes=(elem_type_plate_strain, ))

        # seed sui lati dx e sx a single bias (cioe' un gradiente con due valori)
        part_plate.seedEdgeByBias( biasMethod = abaqusConstants.SINGLE, 
                                   end1Edges  = part_plate.sets['surface-right'].edges, 
                                   end2Edges  = part_plate.sets['surface-left'].edges,
                                   minSize    = self.plate_seed_sx_dx_min, 
                                   maxSize    = self.plate_seed_sx_dx_max )


        # seed sui lati sopra e sotto a double bias (cioe' un gradiente con tre valori)
        part_plate.seedEdgeByBias( biasMethod   = abaqusConstants.DOUBLE, 
                                    centerEdges = (part_plate.sets['surface-top'].edges[0], part_plate.sets['surface-bottom'].edges[0] ),
                                    minSize     = self.plate_seed_top_bottom_min, 
                                    maxSize     = self.plate_seed_top_bottom_max )

        part_plate.generateMesh()


        #----------- MESH: circle -----------#

        part_circle.seedPart( size = self.circle_seed_size )
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
        job.submit()
        job.waitForCompletion()
        

        #----------- SAVING OUTPUT IN FILE CSV -----------#

        if SAVECIRCLEVELOCITY or SAVEDISPLACEMENT or SAVESTRESS or SAVEINITIALCOORD:
    
    
            #*****************
            # LOADING DATABASE
            #*****************
            odb = session.openOdb(JOB_NAME + '.odb')
    
    
            #*****************************
            # GETTING FIRST FRAME AVAILABLE
            #*****************************
            firstFrame = odb.steps['Step-1'].frames[0]
            
            
            #*****************************
            # GETTING LAST FRAME AVAILABLE
            #*****************************
            lastFrame = odb.steps['Step-1'].frames[-1]
            
            
            #********************
            # REGIONS OF INTEREST
            #********************
            outputRegion         = odb.rootAssembly.instances['PLATE'].nodeSets['SET-ALL']
            outputRegionExternal = odb.rootAssembly.instances['PLATE'].nodeSets['SURFACE-ALL']
            
            
            #******************************
            # SAVING VELOCITY OF THE CIRCLE
            #******************************
            if SAVECIRCLEVELOCITY:
                
                region = odb.steps['Step-1'].historyRegions['Node ASSEMBLY.1']
                v2Data = region.historyOutputs['V2_FILTER-1'].data
                
                velocity_df = pd.DataFrame( { 'Time'     : [ time for time, _ in v2Data ] ,
                                              'Velocity' : [ v2   for _, v2   in v2Data ] } )
                
                velocity_output_filename = os.path.join( self.new_path, 'circle_velocity_y.csv' )
            
            
                velocity_df.to_csv( velocity_output_filename, index = False )
            
            
            #******************************
            # SAVING VELOCITY OF THE CIRCLE
            #******************************
            if SAVEINITIALCOORD:
                
                coordinates = firstFrame.fieldOutputs['COORD'].getSubset( region = outputRegion )
                
                initial_coordinates_df = pd.DataFrame( { 'Id'      : [ values.nodeLabel for values in coordinates.values ],
                                                         'X_Coord' : [ values.data[0]   for values in coordinates.values ],
                                                         'Y_Coord' : [ values.data[1]   for values in coordinates.values ] } )
                
                coordinate_output_filename = os.path.join( self.new_path, 'initial_coordinates.csv' )
                
                initial_coordinates_df.to_csv( coordinate_output_filename, index = False )
            
            
            #******************************************
            # SAVING DISPLACEMENTS OF A SPECIFIC REGION
            #******************************************
            if SAVEDISPLACEMENT:
                
                #***************************************************
                # GETTING THE DISPLACEMENT OF THE REGION OF INTEREST
                #***************************************************
                displacement = lastFrame.fieldOutputs['U'].getSubset( region = outputRegion )
                
                displacement_df = pd.DataFrame( { 'Id'     : [ values.nodeLabel for values in displacement.values ],
                                                  'X_Disp' : [ values.data[0]   for values in displacement.values ],
                                                  'Y_Disp' : [ values.data[1]   for values in displacement.values ] } )
                
                displacement_output_filename = os.path.join( self.new_path, 'output_displacement.csv' )

                displacement_df.to_csv( displacement_output_filename, index = False )

                
                # solo la frontiera                
                displacement_external = lastFrame.fieldOutputs['U'].getSubset( region = outputRegionExternal )
                
                displacement_external_df = pd.DataFrame( { 'Id'     : [ values.nodeLabel for values in displacement_external.values ],
                                                            'X_Disp' : [ values.data[0]   for values in displacement_external.values ],
                                                            'Y_Disp' : [ values.data[1]   for values in displacement_external.values ] } )
                
                displacement_external_output_filename = os.path.join( self.new_path, 'output_displacement_external.csv' )

                displacement_external_df.to_csv( displacement_external_output_filename, index = False )
                
                
                
            if SAVESTRESS:
                
                #*********************************************
                # GETTING THE STRESS OF THE REGION OF INTEREST
                #*********************************************

                stress = lastFrame.fieldOutputs['S'].getScalarField( componentLabel = 'S11' )


                stress_df = pd.DataFrame( { 'Id'   : [ values.nodeLabel for values in stress.values ],
                                            'Data' : [ values.data      for values in stress.values ] } )
                
                
                stress_output_filename = os.path.join( self.new_path, 'output_stress.csv' )
                
                stress_df.to_csv( stress_output_filename, index = False )


        #----------- SAVING DATABASE -----------#
        
        #***************************************
        # SAVING THE ABAQUS MODEL TO A .CAE FILE
        #***************************************
        if SAVEDATABASE:

            mdb.saveAs(str(self.index) + '.cae')


        #----------- ELIMINA FILE EXTRA GENERATI DA ABAQUS -----------#

        files_ext = [ '.jnl',   '.sel', '.res', 
                      '.lck',   '.dat', '.msg', 
                      '.sta',   '.fil', '.sim',
                      '.stt',   '.mdl', '.prt', 
                      '.ipm',   '.log', '.com', 
                      '.odb_f', '.abq', '.pac' ]

        if (not SAVEJOBINPUT):
            files_ext.append('.inp')              
        

        #***********************
        # REMOVING USELESS FILES
        #***********************
        for file_ex in files_ext:
            
            file_path = JOB_NAME + file_ex

            if os.path.exists(file_path):
                os.remove(file_path)
                    
        
        #******************************
        # RETURNING TO PARENT DIRECTORY
        #******************************
        os.chdir( self.previous_path )
        
        
    def get_simulation_folder( self ):
        
        return self.new_path