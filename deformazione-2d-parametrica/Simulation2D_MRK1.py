import os
import abaqusConstants
import mesh
import numpy           as np
import json
import math

from abaqus      import *
from driverUtils import *
from caeModules  import *


class Simulation2D():

    def __init__( self, 
                  circle_density ):

        # PARAMETERS
        self.index          = None
        self.circle_speed_x = None
        self.circle_speed_y = None
        self.circle_density = circle_density
 
 
         # OBJECT DIMENSION
        self.plate_width         = 50
        self.plate_height        = 4
        self.circle_radius       = 2.5
        self.circle_impact_angle = None


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
                       SAVEINPUTDATA       = True, 
                       SAVEDISPLACEMENTCSV = True, 
                       SAVESTRESSCSV       = True, 
                       SAVEDATABASE        = False, 
                       SAVEJOBINPUT        = False ):



        #*************************
        #RESETTING THE ENVIRONMENT
        #*************************   
        Mdb()
        
        
        self.index                 = SUMULATION_ID
        self.circle_speed_x        = CIRCLE_VELOCITY*math.cos( math.radians( ALPHA + 90 ) )
        self.circle_speed_y        = CIRCLE_VELOCITY*math.sin( math.radians( ALPHA + 90 ) )
        self.circle_origin_x       = CIRCLE_ORIGIN_X
        self.circle_origin_y       = CIRCLE_ORIGIN_Y
        self.circle_impact_angle   = ALPHA
        self.circle_plate_distance = ( self.circle_origin_y - self.circle_radius - self.plate_height/2 )
        self.simulation_time_perc  = 0.1                                                                  #percentage
        BETA                       = ( 90 - ALPHA )
        
        self.translation           = -np.sign(ALPHA)*self.circle_origin_y*math.atan( math.radians( BETA ) ) if ALPHA != 0 else 0
        self.trajectory            = math.sqrt( (self.circle_origin_y - self.circle_radius)*( self.circle_origin_y - self.circle_radius ) + self.translation*self.translation )
        
        # Crea cartella (se non esiste) con nome <index>
        self.folder_name   = f'Dynamic_Simulation_{self.index}'
        self.previous_path = os.getcwd()
        self.new_path      = os.path.join( self.previous_path, self.folder_name)
        
        
        os.makedirs( self.new_path, 
                     exist_ok = True )
        
        
        # SIMULATION ELAPSED TIME
        # self.time_period  = abs( self.circle_plate_distance / CIRCLE_VELOCITY )
        self.time_period  = abs( self.trajectory / CIRCLE_VELOCITY )
        # self.time_period += self.simulation_time_perc*self.time_period
        
    
        message = f'New folder name : {self.new_path}'
        print( len(message)*'*' )
        print( message )
        # print( f'Traslation    : {self.translation}' )
        # print( f'Trajectory    : {self.trajectory}' )
        # print( f'Circle Origin : {self.circle_origin_y}' )
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


        # executeOnCaeStartup()

        
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
                                                 
                                                 
        sketch_plate.rectangle( ( -self.plate_width/2, -self.plate_height/2 ), 
                                (  self.plate_width/2,  self.plate_height/2 ) )
                                 

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
        part_plate.Set(name='surface-top', edges=part_plate.edges.findAt(coordinates=((0, self.plate_height/2, 0), )))
        part_plate.Surface(name='surface-top', end1Edges=part_plate.edges.findAt(coordinates=((0, self.plate_height/2, 0), )))
        part_plate.Set(name='surface-bottom', edges=part_plate.edges.findAt(coordinates=((0, -self.plate_height/2, 0), )))
        part_plate.Set(name='surface-left', edges=part_plate.edges.findAt(coordinates=((-self.plate_width/2, 0, 0), )))
        part_plate.Set(name='surface-right', edges=part_plate.edges.findAt(coordinates=((self.plate_width/2, 0, 0), )))

        # set tutti i nodi esterni, per l'output
        part_plate.SetByBoolean(name='surface-all', sets=(part_plate.sets['surface-top'], part_plate.sets['surface-bottom'],
                                                           part_plate.sets['surface-left'], part_plate.sets['surface-right'] ))


        #----------- crea PARTI e SET: circle -----------#

        # crea sketch circle, circonferenza con raggio 2.5 mm
        sketch_circle = model.ConstrainedSketch( name      = 'sketch-circle', 
                                                 sheetSize = 2*self.circle_radius )
                                                 
                                                 
        sketch_circle.CircleByCenterPerimeter( center = (0, 0), 
                                               point1 = (self.circle_radius, 0) )
        
        
        # crea circle usando lo sketch
        part_circle = model.Part( name           = 'circle', 
                                  dimensionality = abaqusConstants.TWO_D_PLANAR, 
                                  type           = abaqusConstants.DEFORMABLE_BODY )
                                  
                                  
        part_circle.BaseShell( sketch = sketch_circle )


        # crea set che include tutta la circle, per assegnargli il materiale
        part_circle.Set( name  = 'set-all', 
                         faces = part_circle.faces.findAt( coordinates = ((0, 0, 0), )))


        # crea set per bordo della circle, per impostare l'interaction
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

        # crea sezione per la plate e assegnaci la plate
        model.HomogeneousSolidSection( name      = 'section-plate', 
                                       material  = 'material-plate', 
                                       thickness = None )
                                       
        part_plate.SectionAssignment( region      = part_plate.sets['set-all'], 
                                      sectionName = 'section-plate' )

        # crea sezione per la circle e assegnaci la circle
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
                                     dependent = abaqusConstants.ON).translate( ( ( self.circle_origin_x + self.translation ), self.circle_origin_y, 0 ) )
                                     
                                     

        #model.rootAssembly.regenerate()


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
        RP_circle_id     = model.rootAssembly.ReferencePoint( point = ( self.circle_origin_x + self.translation, self.circle_origin_y, 0) ).id
        
        RP_circle_region = regionToolset.Region( referencePoints = ( model.rootAssembly.referencePoints[RP_circle_id], ) )

        # assegna rigid body constraint alla circle associato al reference point
        model.RigidBody( name           = 'constraint-circle-rigid-body', 
                         refPointRegion = RP_circle_region, 
                         bodyRegion     = model.rootAssembly.instances['circle'].sets['set-all'] )



        #----------- BOUNDARY CONDITION -----------#

        # encastre per la superficie sotto della plate
        # bc_encastre = model.EncastreBC( name           = 'BC-Encastre', 
                                        # createStepName = 'Initial', 
                                        # region         = model.rootAssembly.instances['plate'].sets['surface-bottom'] )

        bc_left_encastre = model.DisplacementBC( name           = 'FixedBC_Left', 
                                                 createStepName = 'Initial', 
                                                 region         = model.rootAssembly.instances['plate'].sets['surface-left'], 
                                                 u1             = 0.0, 
                                                 u2             = 0.0 )
                                                 
                                                 
        bc_right_encastre = model.DisplacementBC( name           = 'FixedBC_Right', 
                                                  createStepName = 'Initial', 
                                                  region         = model.rootAssembly.instances['plate'].sets['surface-right'], 
                                                  u1             = 0.0, 
                                                  u2             = 0.0 )


        #----------- PREDEFINED FIELD -----------#

        # velocita' iniziale assegnata alla circle tramite predefined field (associato al suo reference point)
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
        #elem_type_plate_strain = mesh.ElemType( elemLibrary = abaqusConstants.EXPLICIT, 
        #                                        elemCode    = abaqusConstants.C3D8R )    

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
        
        
        # salva input file ("<nome job>.inp")
        if SAVEJOBINPUT:
            
            job.writeInput()
        
    
        # submit the job:
        job.submit()
        job.waitForCompletion()
        

        #----------- SALVA OUTPUT IN FILE CSV -----------#

        if SAVEDISPLACEMENTCSV or SAVESTRESSCSV:

            # Apri output database
            odb = session.openOdb(JOB_NAME + '.odb')

            # Prendi l'ultimo frame
            lastFrame = odb.steps['Step-1'].frames[-1]
            
            
            # Regioni di cui vogliamo i valori
            outputRegion = odb.rootAssembly.instances['PLATE'].nodeSets['SET-ALL']
            outputRegionExternal = odb.rootAssembly.instances['PLATE'].nodeSets['SURFACE-ALL']

            if SAVEDISPLACEMENTCSV:
                
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


            if SAVESTRESSCSV:
                
                stress = lastFrame.fieldOutputs['S']
                stress = stress.getScalarField(componentLabel='S11')

                stress_data = []
                for v in stress.values:
                    stress_data.append( [v.elementLabel, v.data] )

                stress_data_np = np.array(stress_data)
                np.savetxt( str(self.index) + '_output_stress.csv', stress_data_np, delimiter = ',', comments = '' )



        #----------- SAVING DATABASE -----------#

        # save the Abaqus model to a .cae file
        if SAVEDATABASE:

            mdb.saveAs(str(self.index) + '.cae')


        #----------- ELIMINA FILE EXTRA GENERATI DA ABAQUS -----------#

        files_ext = [ '.jnl',   '.inp', '.res', 
                      '.lck',   '.dat', '.msg', 
                      '.sta',   '.fil', '.sim',
                      '.stt',   '.mdl', '.prt', 
                      '.ipm',   '.log', '.com', 
                      '.odb_f', '.abq', '.pac', '.sel' ]
                      
                     
        for file_ex in files_ext:
            
            file_path = JOB_NAME + file_ex
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass            

        # RETURNING TO PARENT DIRECTORY
        os.chdir( self.previous_path )