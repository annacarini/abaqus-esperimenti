from abaqus import *
import abaqusConstants
from abaqusConstants import *
import regionToolset
import mesh
import visualization
import time

# Create a new model
model_name = 'BarAndMassDynamic'
model = mdb.Model(name=model_name)

# Parameters
bar_length = 50.0
bar_height = 10.0
circle_radius = 5.0
material_density = 7800.0  # Density of steel in kg/m^3
young_modulus = 210e9  # Young's modulus in Pa
poisson_ratio = 0.3  # Poisson's ratio

# Create a part: the bar
sketch = model.ConstrainedSketch(name='BarSketch', sheetSize=200.0)
sketch.rectangle(point1=(0.0, 0.0), point2=(bar_length, bar_height))
bar_part = model.Part(name='Bar', dimensionality=TWO_D_PLANAR, type=DEFORMABLE_BODY)
bar_part.BaseShell(sketch=sketch)

# Create a part: the circular mass
sketch = model.ConstrainedSketch(name='CircleSketch', sheetSize=200.0)
sketch.CircleByCenterPerimeter(center=(25, 50),  # Position the mass above the bar
                               point1=(25, 25))
circle_part = model.Part(name='Mass', dimensionality=TWO_D_PLANAR, type=DEFORMABLE_BODY)
circle_part.BaseShell(sketch=sketch)

# Define material properties
material = model.Material(name='Steel')
material.Density(table=((material_density,),))
material.Elastic(table=((young_modulus, poisson_ratio),))

# Assign material properties to the bar
bar_section = model.HomogeneousSolidSection(name='BarSection', material='Steel', thickness=1.0)
bar_region = bar_part.Set(name='BarRegion', faces=bar_part.faces[:])
bar_part.SectionAssignment(region=bar_region, sectionName='BarSection')

# Assign material properties to the mass
mass_section = model.HomogeneousSolidSection(name='MassSection', material='Steel', thickness=1.0)
mass_region = circle_part.Set(name='MassRegion', faces=circle_part.faces[:])
circle_part.SectionAssignment(region=mass_region, sectionName='MassSection')

# Create assembly
assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)
assembly.Instance(name='BarInstance', part=bar_part, dependent=ON)
assembly.Instance(name='MassInstance', part=circle_part, dependent=ON)

# Apply constraints: Fix the left end of the bar
left_edge = assembly.instances['BarInstance'].edges.findAt(((0.0, bar_height / 2, 0.0),))
assembly.Set(edges=left_edge, name='FixedEnd')
model.DisplacementBC(name='FixedBC', createStepName='Initial', region=assembly.sets['FixedEnd'], u1=0.0, u2=0.0)

# Create a dynamic step for the simulation
model.ImplicitDynamicsStep(name='DynamicStep', previous='Initial', timePeriod=100.0, 
                           maxNumInc=1000, initialInc=0.1, minInc=1e-3)

# Apply gravity in the dynamic step
model.Gravity(name='GravityLoad', createStepName='DynamicStep', comp2=-9.81)

# Mesh the parts
bar_part.seedPart(size=1, deviationFactor=0.1, minSizeFactor=0.1)  # Adjust size as needed
bar_part.generateMesh()

circle_part.seedPart(size=5, deviationFactor=0.1, minSizeFactor=0.1)  # Adjust size as needed
circle_part.generateMesh()

# Define a surface on the top of the bar for contact
bar_top_edge = assembly.instances['BarInstance'].edges.findAt(((bar_length / 2, bar_height, 0.0),))
assembly.Surface(name='BarSurface', side1Edges=bar_top_edge)

# Define the surface on the mass for contact
mass_edges = assembly.instances['MassInstance'].edges.getSequenceFromMask(mask=('[#1 ]',), )
if len(mass_edges) > 0:
    assembly.Surface(name='MassSurface', side1Edges=mass_edges)
    print("MassSurface successfully created.")
else:
    print("No edges found for MassSurface.")

# Create contact interaction between bar and mass
contact_property = model.ContactProperty('FrictionlessContact')
contact_property.TangentialBehavior(formulation=FRICTIONLESS)

model.SurfaceToSurfaceContactStd(name='Contact',
                                 createStepName='DynamicStep',
                                 main=assembly.surfaces['BarSurface'],
                                 secondary=assembly.surfaces['MassSurface'],
                                 sliding=FINITE,
                                 interactionProperty='FrictionlessContact')

# Submit the job for dynamic simulation
job_name = 'BarWithMassDynamicSimulation'
mdb.Job(name=job_name, model=model_name, type=ANALYSIS, numCpus=1, numDomains=1, parallelizationMethodExplicit=DOMAIN)
mdb.jobs[job_name].submit(consistencyChecking=ON)
mdb.jobs[job_name].waitForCompletion()

""" # Open the results in the viewport
odb_path = job_name + '.odb'
odb = session.openOdb(name=odb_path)

# Accessing the last frame to extract stress and displacement
step = odb.steps['DynamicStep']
if len(step.frames) > 0:
    last_frame = step.frames[-1]
    stress = last_frame.fieldOutputs['S']
    displacement = last_frame.fieldOutputs['U']
    print("Stress output:", stress)
    print("Displacement output:", displacement)
else:
    print("No frames available for step 'DynamicStep'.")
 """