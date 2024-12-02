# abqpy installato per python 3.10 cosi':
# py -V:3.10 -m pip install -U abqpy==2024.*

import sys
from abaqus import *
import abaqusConstants
from driverUtils import *
from caeModules import *
import mesh


def log(message):
    print(message, file=sys.__stdout__)
    return

# DIMENSIONI OGGETTI
lastra_width = 50
lastra_height = 6
palla_radius = 2.5

# POSIZIONI INIZIALI
lastra_origin_x = 0
lastra_origin_y = 0
palla_origin_x = 0
palla_origin_y = palla_radius+lastra_height/2


# this function will be executed each time we open Abaqus
executeOnCaeStartup()

# crea modello
model = mdb.models['Model-1']


#----------- crea PARTI e SET: LASTRA -----------#

# crea sketch lastra, rettangolo da 50x6 mm
sketch_lastra = model.ConstrainedSketch(name='sketch-lastra', sheetSize=lastra_width)
sketch_lastra.rectangle((-lastra_width/2, -lastra_height/2), (lastra_width/2, lastra_height/2))

# crea lastra usando lo sketch
part_lastra = model.Part(name='Lastra', dimensionality=abaqusConstants.TWO_D_PLANAR, type=abaqusConstants.DEFORMABLE_BODY)
part_lastra.BaseShell(sketch=sketch_lastra)

# crea set che include tutta la lastra, per assegnargli il materiale
part_lastra.Set(name='set-all', faces=part_lastra.faces.findAt(coordinates=((0, 0, 0), )))

# crea diversi set per le superfici della lastra, per assegnargli una boundary condition (sotto) e per impostare l'interaction (sopra) 
# e per gestire il seed della mesh
part_lastra.Set(name='surface-top', edges=part_lastra.edges.findAt(coordinates=((0, lastra_height/2, 0), )))
part_lastra.Surface(name='surface-top', end1Edges=part_lastra.edges.findAt(coordinates=((0, lastra_height/2, 0), )))
part_lastra.Set(name='surface-bottom', edges=part_lastra.edges.findAt(coordinates=((0, -lastra_height/2, 0), )))
part_lastra.Set(name='surface-left', edges=part_lastra.edges.findAt(coordinates=((-lastra_width/2, 0, 0), )))
part_lastra.Set(name='surface-right', edges=part_lastra.edges.findAt(coordinates=((lastra_width/2, 0, 0), )))



#----------- crea PARTI e SET: PALLA -----------#

# crea sketch palla, circonferenza con raggio 2.5 mm
sketch_palla = model.ConstrainedSketch(name='sketch-palla', sheetSize=5)
sketch_palla.CircleByCenterPerimeter((0, 0), (palla_radius, 0))    # crea un cerchio a partire dal centro e da un punto appartenente alla circonferenza

# crea palla usando lo sketch
part_palla = model.Part(name='Palla', dimensionality=abaqusConstants.TWO_D_PLANAR, type=abaqusConstants.DEFORMABLE_BODY)
part_palla.BaseShell(sketch=sketch_palla)

# crea set che include tutta la palla, per assegnargli il materiale
part_palla.Set(name='set-all', faces=part_palla.faces.findAt(coordinates=((0, 0, 0), )))

# crea set per bordo della palla, per impostare l'interaction
part_palla.Set(name='surface', edges=part_palla.edges.findAt(coordinates=((palla_radius, 0, 0), )))
part_palla.Surface(name='surface', end1Edges=part_palla.edges.findAt(coordinates=((palla_radius, 0, 0), )))


#----------- MATERIALI -----------#

material_lastra = model.Material(name='material-lastra')
material_lastra.Density(table=((7.83E-7, ), ))
material_lastra.Elastic(table=((200E3, 0.3), ))
material_lastra.Plastic(table=((350, 0), (500, 0.8),))      # materiale da rivedere

material_palla = model.Material(name='material-palla')
material_palla.Density(table=((2.7E-4, ), ))
material_palla.Elastic(table=((200E3, 0.3), ))             # forse e' inutile perche' poi gli do un rigid body constraint?



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
model.rootAssembly.Instance(name='Palla', part=part_palla, dependent=abaqusConstants.ON).translate((palla_origin_x, palla_origin_y, 0))
#model.rootAssembly.regenerate()



#----------- STEP -----------#

step_1 = model.ExplicitDynamicsStep(name='Step-1', previous='Initial', description='',
                                    timePeriod=0.02, timeIncrementationMethod=abaqusConstants.AUTOMATIC_GLOBAL)

# specifica quali campi vogliamo in output e la frequenza
field = model.FieldOutputRequest('F-Output-1', createStepName='Step-1', variables=('S', 'E', 'U'), frequency=40)



#----------- RIGID BODY CONSTRAINT per la palla -----------#

# crea reference point nella coordinata dove si trova il centro della palla
RP_palla_id = model.rootAssembly.ReferencePoint(point=(0, 5.5, 0)).id
RP_palla_region = regionToolset.Region(referencePoints=(model.rootAssembly.referencePoints[RP_palla_id],))

# assegna rigid body constraint alla palla associato al reference point
model.RigidBody(name='constraint-palla-rigid-body', refPointRegion=RP_palla_region, bodyRegion=model.rootAssembly.instances['Palla'].sets['set-all'])



#----------- BOUNDARY CONDITION -----------#

# encastre per la superficie sotto della lastra
bc_encastre = model.EncastreBC(name='BC-Encastre', createStepName='Initial', region=model.rootAssembly.instances['Lastra'].sets['surface-bottom'])

'''
# velocita' assegnata alla palla tramite boundary condition
# (non corretto perche' questa BC si puo' assegnare solo allo step 1, ma in questo modo la palla deve per forza arrivare
# a quello step avendo questa velocita', nonostante l'impatto con la lastra -> viene aggiunta energia per compensare)
bc_velocity = model.VelocityBC(name='BC-Velocity', createStepName='Initial', region=RP_palla_region, v1=abaqusConstants.SET, v2=abaqusConstants.SET)
bc_velocity.setValuesInStep(stepName='Step-1', v1=0, v2=-1000)   # VELOCITA' PALLA: 0 lungo l'asse x, -1000 lungo l'asse y
'''

#----------- PREDEFINED FIELD -----------#

# velocita' iniziale assegnata alla palla tramite predefined field (associato al suo reference point)
palla_velocity_x = 0
palla_velocity_y = -1000
velocity = model.Velocity(name="Velocity", region=RP_palla_region, velocity1=palla_velocity_x, velocity2=palla_velocity_y)


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
part_lastra.seedEdgeByBias(biasMethod=abaqusConstants.SINGLE, end1Edges=part_lastra.sets['surface-right'].edges, end2Edges=part_lastra.sets['surface-left'].edges, minSize=0.2, maxSize=1.2)

# seed sui lati sopra e sotto a double bias (cioe' un gradiente con tre valori)
part_lastra.seedEdgeByBias(biasMethod=abaqusConstants.DOUBLE, centerEdges=(part_lastra.sets['surface-top'].edges[0], part_lastra.sets['surface-bottom'].edges[0]), minSize=0.2, maxSize=2)

part_lastra.generateMesh()


#----------- MESH: palla -----------#

part_palla.seedPart(size=1)
part_palla.generateMesh()


#----------- JOB -----------#

job = mdb.Job(name='Job-1', model='Model-1')

# salva input file (<nome job>.inp)
job.writeInput()

'''
# submit the job:
job.submit()
job.waitForCompletion()
'''


#----------- SALVA DATABASE -----------#

# save the Abaqus model to a .cae file
mdb.saveAs('deformazione-2d-script.cae')


