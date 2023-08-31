bl_info = {
	"name": "Phänotyp",
	"description": "Genetic algorithm for architectural structures",
	"author": "bewegende Architektur e.U. and Karl Deix",
	"version": (0,2,5),
	"blender": (3,5,1),
	"location": "3D View > Tools",
}

import bpy
from bpy.props import (IntProperty, FloatProperty, BoolProperty, StringProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)
from bpy.app.handlers import persistent

from phaenotyp import basics, panel, operators, material, geometry, calculation, ga, report, progress

'''
The __init__ file is the main-file to be registert from blender.
It contains and handles all blender properties as well as the panel.
'''

def viz_update(self, context):
	'''
	Triggers the update of the vizulisation.
	:param self: Passed from the panel.
	:param context: Passed from the panel.
	'''
	scene = context.scene
	phaenotyp = scene.phaenotyp
	geometry.update_geometry_post()

class phaenotyp_properties(PropertyGroup):
	'''
	Is holding all variables for the panel.
	'''
	use_scipy: BoolProperty(
		name = 'use_scipy',
		description = "Scipy is available! Calculation will be much faster. Anyway: Try to uncheck if something is crashing",
		default = True
	)

	calculation_type: EnumProperty(
		name = "calculation_type",
		description = "Calculation types",
		items = [
				("-", "-", ""),
				("geometrical", "Geometrical", ""),
				("force_distribution", "Force distribution", ""),
				("first_order", "First order (choose this if unsure)", ""),
				("first_order_linear", "First order linear", ""),
				("second_order", "Second order", "")
				],
		default = "-",
		update = basics.force_distribution_info
		)

	type_of_joints: EnumProperty(
		name="type_of_joints:",
		description="Released Moments",
		items=[
				("-", "-", ""),
				("release_moments", "Release moments", ""),
				("fixed_joints", "Fixed joints (choose this if unsure)", "")
			   ]
		)
	
	Do: FloatProperty(
		name = "Do",
		description = "Diameter of pipe outside in cm",
		default = 6.0,
		min = 0.1,
		max = 100.0
		)

	Di: FloatProperty(
		name = "Di",
		description = "Diameter of pipe inside in cm. Needs to be smaller than Diameter outside",
		default = 5.0,
		min = 0.1,
		max = 100.0
		)

	member_type: EnumProperty(
		name = "member_type",
		description = "Type of member",
		items = [
				("full", "Full", ""),
				("tension_only", "Tension only", ""),
				("comp_only", "Compression only", "")
			   ]
		)
	
	material: EnumProperty(
		name = "material",
		description = "Predefined materials",
		items = material.dropdown
		)

	E: IntProperty(
		name = "E",
		description = "Elasticity modulus in kN/cm²",
		default = 21000,
		min = 15000,
		max = 50000
		)

	G: IntProperty(
		name = "G",
		description = "Shear modulus kN/cm²",
		default = 8100,
		min = 10000,
		max = 30000
		)

	rho: FloatProperty(
		name = "rho",
		description = "Density in g/cm3",
		default = 7.85,
		min = 0.01,
		max = 30.0
		)

	psf_members: FloatProperty(
		name = "rho",
		description = "Partial safety factor",
		default = 1.35,
		min = 0.8,
		max = 1.5
		)
	
	acceptable_sigma: FloatProperty(
		name = "acceptable_sigma",
		description = "Acceptable sigma kN/cm²",
		default = 16.0,
		min = 0.01,
		max = 30.0
		)

	acceptable_shear: FloatProperty(
		name = "acceptable_shear",
		description = "Acceptable shear kN/cm²",
		default = 9.5,
		min = 0.01,
		max = 30.0
		)

	acceptable_torsion: FloatProperty(
		name = "acceptable_torsion",
		description = "Acceptable torsion kN/cm²",
		default = 10.5,
		min = 0.01,
		max = 30.0
		)

	acceptable_sigmav: FloatProperty(
		name = "acceptable_sigmav kN/cm²",
		description = "Acceptable sigmav",
		default = 10.5,
		min = 23.5,
		max = 30.0
		)

	kn_custom: StringProperty(
		name = "kn_custom",
		description = "kn of custom material",
		default = "16.5, 15.8, 15.3, 14.8, 14.2, 13.5, 12.7, 11.8, 10.7, 9.5, 8.2, 6.9, 5.9, 5.1, 4.4, 3.9, 3.4, 3.1, 2.7, 2.5, 2.2, 2.0, 1.9, 1.7, 1.6"
		)

	loc_x: BoolProperty(name = 'loc_x', default = True)
	loc_y: BoolProperty(name = 'loc_y', default = True)
	loc_z: BoolProperty(name = 'loc_z', default = True)
	rot_x: BoolProperty(name = 'rot_x', default = False)
	rot_y: BoolProperty(name = 'rot_y', default = False)
	rot_z: BoolProperty(name = 'rot_z', default = False)
	   
	thickness: FloatProperty(
		name = "thickness",
		description = "Thickness in cm",
		default = 25.0,
		min = 0.01,
		max = 100.0
		)

	material_quads: EnumProperty(
		name = "material",
		description = "Predefined materials",
		items = material.dropdown_quads
		)
	
	E_quads: IntProperty(
		name = "E",
		description = "Elasticity modulus in kN/cm²",
		default = 1500,
		min = 500,
		max = 50000
		)

	G_quads: IntProperty(
		name = "G",
		description = "Shear modulus kN/cm²",
		default = 400,
		min = 100,
		max = 25000
		)
		
	nu_quads: FloatProperty(
		name = "nu",
		description = "Poisson's ratio",
		default = 0.17,
		min = 0.01,
		max = 30.0
		)

	rho_quads: FloatProperty(
		name = "rho",
		description = "Density in g/cm3",
		default = 1.0,
		min = 0.01,
		max = 30.0
		)

	psf_quads: FloatProperty(
		name = "rho",
		description = "Partial safety factor",
		default = 1.35,
		min = 0.8,
		max = 1.5
		)
	
	load_type: EnumProperty(
		name = "load_type",
		description = "Load types",
		items = [
				("vertices", "Vertices", ""),
				("edges", "Edges", ""),
				("faces", "Faces", "")
			   ],
		update = basics.set_selection_for_load,
		)

	load_FX: FloatProperty(
		name = "load_FX",
		description = "Axial in x-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_FY: FloatProperty(
		name = "load_FY",
		description = "Axial in y-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_FZ: FloatProperty(
		name = "load_FZ",
		description = "Axial in z-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_MX: FloatProperty(
		name = "load_MX",
		description = "Moment in x-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_MY: FloatProperty(
		name = "load_MY",
		description = "Moment in y-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_MZ: FloatProperty(
		name = "load_MZ",
		description = "Moment in z-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_Fx: FloatProperty(
		name = "load_Fx",
		description = "Local axial in x-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_Fy: FloatProperty(
		name = "load_Fy",
		description = "Local axial in y-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_Fz: FloatProperty(
		name = "load_Fz",
		description = "Local axial in z-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)
	
	load_normal: FloatProperty(
		name = "load_normal",
		description = "Load in normal-Direction in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_projected: FloatProperty(
		name = "load_projected",
		description = "Load projected on floor in kN",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	load_area_z: FloatProperty(
		name = "load_area_z",
		description = "Load of full area in z-direction",
		default = 0.0,
		min = -1000,
		max = 1000.0
		)

	psf_loads: FloatProperty(
		name = "rho",
		description = "Partial safety factor",
		default = 1.5,
		min = 0.8,
		max = 4
		)
	
	generation_size: IntProperty(
		name = "generation_size",
		description="Size of generation for GA",
		default = 20,
		min = 10,
		max = 1000
		)

	elitism: IntProperty(
		name = "elitism",
		description="Size of elitism for GA",
		default = 2,
		min = 1,
		max = 100
		)

	generation_amount: IntProperty(
		name = "generation_amount",
		description="Amount of generations",
		default = 10,
		min = 1,
		max = 250
		)

	fitness_volume: FloatProperty(
		name = "volume",
		description = "Volume of the enclosed parts of the structure",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_volume_invert: BoolProperty(
		name = 'volume invert',
		description = "Activate to maximize the volume",
		default = False
	)

	fitness_area: FloatProperty(
		name = "area",
		description = "Area of all faces of the structure",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_area_invert: BoolProperty(
		name = 'area invert',
		description = "Activate to maximize the area",
		default = False
	)

	fitness_weight: FloatProperty(
		name = "weight",
		description = "Weight the structure (without loads)",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_weight_invert: BoolProperty(
		name = 'weight invert',
		description = "Activate to maximize the weight",
		default = False
	)

	fitness_rise: FloatProperty(
		name = "rise",
		description = "Rise of the structure (distances between lowest and highest vertex)",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_rise_invert: BoolProperty(
		name = 'rise invert',
		description = "Activate to maximize the rise",
		default = False
	)

	fitness_span: FloatProperty(
		name = "span",
		description = "Span distance of the structure (highest distance between supports)",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_span_invert: BoolProperty(
		name = 'span invert',
		description = "Activate to maximize the span",
		default = False
	)

	fitness_cantilever: FloatProperty(
		name = "cantilever",
		description = "Cantilever of the structure (lowest distance from all vertices to all supports)",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_cantilever_invert: BoolProperty(
		name = 'cantilever invert',
		description = "Activate to maximize the cantilever",
		default = False
	)

	fitness_average_sigma: FloatProperty(
		name = "average sigma",
		description = "Average sigma of all members",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_average_strain_energy: FloatProperty(
		name = "average strain energy",
		description = "Average strain energy of all members",
		default = 1.0,
		min = 0.0,
		max = 1.0
		)

	fitness_deflection: FloatProperty(
		name = "deflection",
		description = "Average deflection of the elements",
		default = 0.0,
		min = 0.0,
		max = 1.0
		)

	fitness_deflection_invert: BoolProperty(
		name = 'deflection invert',
		description = "Activate to maximize the deflection",
		default = False
	)
	
	mate_type: EnumProperty(
		name = "mate_type",
		description = "Type of mating",
		items = [
				("direct", "direct", ""),
				("morph", "morph", "")
			   ]
		)

	ranking: IntProperty(
		name = "ranking",
		description="Show results from best to worth fitness",
		default = 0,
		min = 0,
		max = 250
		)

	forces_fd: EnumProperty(
		name = "forces_fd",
		description = "Force types",
		items = [
					("sigma", "Sigma", ""),
					("axial", "Axial", ""),
					("utilization", "Utilization", "")
				],
		update = viz_update
		)

	forces_pn: EnumProperty(
		name = "forces_pn",
		description = "Force types",
		items = [
					("sigma", "Sigma", ""),
					("axial", "Axial", ""),
					("moment_y", "Moment Y", ""),
					("moment_z", "Moment Z", ""),
					("moment_h", "Moment H", ""),
					("shear_y", "Shear Y", ""),
					("shear_z", "Shear y", ""),
					("torque", "Torque", ""),
					("lever_arm", "Lever arm", ""),
					("utilization", "Utilization", ""),
					("normal_energy", "Normal energy", ""),
					("moment_energy", "Moment energy", ""),
					("strain_energy", "Strain energy", "")
				],
		update = viz_update
		)

	forces_quads: EnumProperty(
		name = "forces_quads",
		description = "Force types",
		items = [
					("membrane_x", "Membrane X", ""),
					("membrane_y", "Membrane Y", ""),
					("membrane_xy", "Membrane XY", ""),
					("moment_x", "Moment X", ""),
					("moment_y", "Moment Y", ""),
					("moment_xy", "Moment XY", ""),
					("shear_x", "Shear_X", ""),
					("shear_y", "Shear_Y", "")
				],
		update = viz_update,
		default = "membrane_xy"
		)
		
	viz_scale: FloatProperty(
		name = "viz_scale",
		description = "scale",
		update = viz_update,
		subtype = "PERCENTAGE",
		default = 50,
		min = 0.001,
		max = 100
		)

	viz_deflection: FloatProperty(
		name = "viz_scale",
		description = "deflected / original",
		update = viz_update,
		subtype = "PERCENTAGE",
		default = 50,
		min = 0.001,
		max = 100
		)

	assimilate_length: FloatProperty(
		name = "assimilate_length",
		description = "Target length for assimilation",
		default = 4,
		min = 0.1,
		max = 100
		)

	assimilate_strength: FloatProperty(
		name = "assimilate_strength",
		description = "Strength of assimilation",
		default = 1,
		min = 0.1,
		max = 10
		)

	assimilate_iterations: IntProperty(
		name = "assimilate_iterations",
		description = "Iterations of assimilation",
		default = 10,
		min = 1,
		max = 100
		)
	
	assimilate_update: BoolProperty(
		name = 'Update after frame change',
		default = False
	)
	
	actuator_length: FloatProperty(
		name = "actuator_length",
		description = "Target length for actuator",
		default = 4,
		min = 0.1,
		max = 100
		)
 
	actuator_strength: FloatProperty(
		name = "actuator_strength",
		description = "Strength of actuator",
		default = 1,
		min = 0.1,
		max = 10
		)

	actuator_iterations: IntProperty(
		name = "actuator_iterations",
		description = "Iterations of actuator",
		default = 10,
		min = 1,
		max = 100
		)
	
	actuator_update: BoolProperty(
		name = 'Update after frame change',
		default = False
	)

	goal_strength: FloatProperty(
		name = "goal_strength",
		description = "Strength of goal",
		default = 1,
		min = 0.1,
		max = 10
		)

	goal_iterations: IntProperty(
		name = "goal_iterations",
		description = "Iterations of goal",
		default = 10,
		min = 1,
		max = 100
		)
	
	goal_update: BoolProperty(
		name = 'Update after frame change',
		default = False
	)
		
	gravity_strength: FloatProperty(
		name = "gravity_strength",
		description = "Gravity of wool",
		default = 1.0,
		min = 0.01,
		max = 10.0
		)

	link_strength: FloatProperty(
		name = "link_strength",
		description = "Strength of links",
		default = 0.1,
		min = 0.01,
		max = 10.0
		)
		
	bonding_threshold: FloatProperty(
		name = "bonding_threshold",
		description = "Threshold of bonding",
		default = 1.0,
		min = 0.01,
		max = 10.0
		)
		
	bonding_strength: FloatProperty(
		name = "bonding_strength",
		description = "Target length for actuator",
		default = 1.0,
		min = 0.01,
		max = 10.0
		)
		
	wool_iterations: IntProperty(
		name = "wool_iterations",
		description = "Iterations of wool",
		default = 10,
		min = 1,
		max = 100
		)

	wool_update: BoolProperty(
		name = 'Update after frame change',
		default = False
	)
	
	shyness_threshold: FloatProperty(
		name = "shyness_threshold",
		description = "Threshold of crown shyness",
		default = 1.0,
		min = 0.01,
		max = 10.0
		)

	shyness_strength: FloatProperty(
		name = "shyness_strength",
		description = "Strength of crown shyness",
		default = 0.2,
		min = 0.01,
		max = 10.0
		)

	growth_strength: FloatProperty(
		name = "growth_strength",
		description = "Strength of growth",
		default = 0.1,
		min = 0.01,
		max = 10.0
		)
	
	crown_iterations: IntProperty(
		name = "crown_iterations",
		description = "Iterations of crown shyness",
		default = 10,
		min = 1,
		max = 100
		)

	crown_update: BoolProperty(
		name = 'Update after frame change',
		default = False
	)
	
	mode: EnumProperty(
		name = "mode",
		description = "Select mode to start",
		items = [
					("transformation", "Transformation", ""),
					("single_frame", "Single frame", ""),
					("animation", "Animation", ""),
					("bruteforce", "Bruteforce", ""),
					("gradient_descent", "Gradient descent", ""),
					("genetic_algorithm", "Genetic algorithm", "")
			   ],
		default = "single_frame"
		)

	optimization_fd: EnumProperty(
		name = "optimization",
		description = "Enables sectional optimization after each frame",
		items = [
					("none", "None", ""),
					("approximate", "Approximate", "")
				]
		)

	optimization_pn: EnumProperty(
		name = "optimization",
		description = "Enables sectional optimization after each frame",
		items = [
					("none", "None", ""),
					("simple", "Simple", ""),
					("utilization", "Utilization", ""),
					("complex", "Complex", "")
				]
		)

	optimization_amount: IntProperty(
		name = "optimization_amount",
		description = "Amount of optimization to run for each member",
		default = 3,
		min = 1,
		max = 100
		)

	animation_optimization_type: EnumProperty(
		name = "animation_optimization_type",
		description = "Optimize each frame by amount or create gradient with amount",
		items = [
				("each_frame", "Each frame", ""),
				("gradient", "Gradient", "")
			   ]
		)

	selection_type: EnumProperty(
		name = "selection_type",
		description = "Member or Quad",
		items = [
					("member", "Member", ""),
					("quad", "Quad", "")
				]
		)
	
	selection_key_fd: EnumProperty(
		name = "selection_key_fd",
		description = "Key for selection",
		items = [
					("id", "id", ""),
					("Do", "Do", ""),
					("Di", "Di", ""),
					("weight", "weight", ""),
					("length", "length", ""),
					("sigma", "Sigma", ""),
					("axial", "Axial", ""),
					("utilization", "Utilization", "")
				],
		default = "Do"
		)

	selection_key_pn: EnumProperty(
		name = "selection_key_pn",
		description = "Key for selection",
		items = [
					("id", "Id", ""),
					("Do", "Do", ""),
					("Di", "Di", ""),
					("weight", "weight", ""),
					("length", "Length", ""),
					("max_long_stress", "Max long stress", ""),
					("max_tau_shear", "Max tau shear", ""),
					("max_tau_torsion", "Max tau torsion", ""),
					("max_sum_tau", "Max sum tau", ""),
					("max_sigmav", "Max sigmav", ""),
					("max_sigma", "Max sigma", ""),
					("max_lever_arm", "Max lever arm", ""),
					("utilization", "Utilization", "")
				],
		default = "Do"
		)

	selection_key_quads: EnumProperty(
		name = "selection_key_quads",
		description = "Key for selection",
		items = [
					("id", "Id", ""),
					("thickness", "Thickness", ""),
					("membrane_x", "Membrane X", ""),
					("membrane_y", "Membrane Y", ""),
					("membrane_xy", "Membrane XY", ""),
					("moment_x", "Moment X", ""),
					("moment_y", "Moment Y", ""),
					("moment_xy", "Moment XY", ""),
					("shear_x", "Shear_X", ""),
					("shear_y", "Shear_Y", "")
				],
		default = "thickness"
		)
	
	selection_compare: EnumProperty(
		name = "selection_compare",
		description = "Type of comparsion",
		items = [
					("Equal", "Equal", ""),
					("Greater", "Greater", ""),
					("Less", "Less", "")
				]
		)

	selection_value: StringProperty(
		name = "selection_value",
		description = "Value for selection",
		default = "0"
		)

	selection_threshold: StringProperty(
		name = "selection_threshold",
		description = "Threshold for selection",
		default = "0"
		)

	gd_delta: FloatProperty(
		name = "gd_delta",
		description="Step size for gradient",
		default = 0.1,
		min = 0.01,
		max = 0.2
		)

	gd_learning_rate: FloatProperty(
		name = "gd_learning_rate",
		description="Learning rate.",
		default = 0.05,
		min = 0.05,
		max = 0.5
		)

	gd_abort: FloatProperty(
		name = "gd_abort",
		description="Abort criterion",
		default = 0.01,
		min = 0.001,
		max = 0.1
		)

	gd_max_iteration: IntProperty(
		name = "gd_max_iteration",
		description="Max number of iteration to avoid endless loop",
		default = 100,
		min = 10,
		max = 1000
		)

class WM_OT_set_structure(Operator):
	'''
	Is calling set_structure from the module called operators.
	Check out further info in there.
	'''
	bl_label = "set_structure"
	bl_idname = "wm.set_structure"
	bl_description = "Please select an object in Object-Mode and press set"

	def execute(self, context):
		operators.set_structure()
		return {"FINISHED"}

class WM_OT_fix_structure(Operator):
	'''
	Is calling fix_structure from the module called operators.
	Check out further info in there.
	'''
	bl_label = "fix_structure"
	bl_idname = "wm.fix_structure"
	bl_description = "Is running delete loose parts and merge by distance."

	def execute(self, context):
		operators.fix_structure()
		return {"FINISHED"}

class WM_OT_set_support(Operator):
	'''
	Is calling set_supports from the module called operators.
	Check out further info in there.
	'''
	bl_label = "set_support"
	bl_idname = "wm.set_support"
	bl_description = "Please select vertices and press set, to define them as support (Be sure, that you are in Edit Mode of the Structure)"

	def execute(self, context):
		operators.set_support()
		return {"FINISHED"}

class WM_OT_set_member(Operator):
	'''
	Is calling set_member from the module called operators.
	Check out further info in there.
	'''
	bl_label = "set_member"
	bl_idname = "wm.set_member"
	bl_description = "Please select edges in Edit-Mode and press set, to define profiles"

	def execute(self, context):
		operators.set_member()
		return {"FINISHED"}

class WM_OT_set_quad(Operator):
	'''
	Is calling set_quad from the module called operators.
	Check out further info in there.
	'''
	bl_label = "set_quad"
	bl_idname = "wm.set_quad"
	bl_description = "Please select faces in Edit-Mode and press set, to define surfaces"

	def execute(self, context):
		operators.set_quad()
		return {"FINISHED"}
		
class WM_OT_set_load(Operator):
	'''
	Is calling set_load from the module called operators.
	Check out further info in there.
	'''
	bl_label = "set_load"
	bl_idname = "wm.set_load"
	bl_description = "Add load to selected vertices, edges, or faces"

	def execute(self, context):
		operators.set_load()
		return {"FINISHED"}

class WM_OT_assimilate(Operator):
	'''
	Is calling assimilate from the module called operators.
	Check out further info in there.
	'''
	bl_label = "assimilate"
	bl_idname = "wm.assimilate"
	bl_description = "Assimilate length of members."

	def execute(self, context):
		operators.assimilate()
		return {"FINISHED"}

class WM_OT_actuator(Operator):
	'''
	Is calling actuator from the module called operators.
	Check out further info in there.
	'''
	bl_label = "actuator"
	bl_idname = "wm.actuator"
	bl_description = "Extend or retract to given length."

	def execute(self, context):
		operators.actuator()
		return {"FINISHED"}

class WM_OT_reach_goal(Operator):
	'''
	Is calling reach_goal from the module called operators.
	Check out further info in there.
	'''
	bl_label = "reach_goal"
	bl_idname = "wm.reach_goal"
	bl_description = "Reach goal."

	def execute(self, context):
		operators.reach_goal()
		return {"FINISHED"}

class WM_OT_wool_threads(Operator):
	'''
	Is calling wool threads inspired by Frei Otto from the module called operators.
	Check out further info in there.
	'''
	bl_label = "wool_threads"
	bl_idname = "wm.wool_threads"
	bl_description = "Wool threads."

	def execute(self, context):
		operators.wool_threads()
		return {"FINISHED"}

class WM_OT_crown_shyness(Operator):
	'''
	Is calling crown_shyness from the module called operators.
	Check out further info in there.
	'''
	bl_label = "crown_shyness"
	bl_idname = "wm.crown_shyness"
	bl_description = "Crown shyness."

	def execute(self, context):
		operators.crown_shyness()
		return {"FINISHED"}

class WM_OT_store_co(Operator):
	'''
	Is calling store_co from the module called operators.
	Check out further info in there.
	'''
	bl_label = "store_co"
	bl_idname = "wm.store_co"
	bl_description = "Store co."

	def execute(self, context):
		operators.store_co()
		return {"FINISHED"}

class WM_OT_restore_co(Operator):
	'''
	Is calling restore_co from the module called operators.
	Check out further info in there.
	'''
	bl_label = "restore_co"
	bl_idname = "wm.restore_co"
	bl_description = "Restore co."

	def execute(self, context):
		operators.restore_co()
		return {"FINISHED"}
		
class WM_OT_calculate_single_frame(Operator):
	'''
	Is calling calculate_single_frame from the module called operators.
	Check out further info in there.
	'''
	bl_label = "calculate_single_frame"
	bl_idname = "wm.calculate_single_frame"
	bl_description = "Calulate single frame"

	def execute(self, context):
		operators.calculate_single_frame()
		return {"FINISHED"}

class WM_OT_calculate_animation(Operator):
	'''
	Is calling animation from the module called operators.
	Check out further info in there.
	'''
	bl_label = "calculate_animation"
	bl_idname = "wm.calculate_animation"
	bl_description = "Calulate animation"

	def execute(self, context):
		operators.calculate_animation()
		return {"FINISHED"}

class WM_OT_optimize_approximate(Operator):
	'''
	Is calling optimize_approximate from the module called operators.
	Check out further info in there.
	'''
	bl_label = "optimize_approximate"
	bl_idname = "wm.optimize_approximate"
	bl_description = "Approximate sectional performance"

	def execute(self, context):
		operators.optimize_approximate()
		return {"FINISHED"}

class WM_OT_optimize_simple(Operator):
	'''
	Is calling optimize_simple from the module called operators.
	Check out further info in there.
	'''
	bl_label = "optimize_simple"
	bl_idname = "wm.optimize_simple"
	bl_description = "Simple sectional performance"

	def execute(self, context):
		operators.optimize_simple()
		return {"FINISHED"}

class WM_OT_optimize_utilization(Operator):
	'''
	Is calling optimize_utilization from the module called operators.
	Check out further info in there.
	'''
	bl_label = "optimize_utilization"
	bl_idname = "wm.optimize_utilization"
	bl_description = "utilization sectional performance"

	def execute(self, context):
		operators.optimize_utilization()
		return {"FINISHED"}

class WM_OT_optimize_complex(Operator):
	'''
	Is calling optimize_complex from the module called operators.
	Check out further info in there.
	'''
	bl_label = "optimize_complex"
	bl_idname = "wm.optimize_complex"
	bl_description = "Complex sectional performance"

	def execute(self, context):
		operators.optimize_complex()
		return {"FINISHED"}

class WM_OT_decimate(Operator):
	'''
	Is calling decimate from the module called operators.
	Check out further info in there.
	'''
	bl_label = "topolgy_decimate"
	bl_idname = "wm.topolgy_decimate"
	bl_description = "Decimate topological performance"

	def execute(self, context):
		operators.topolgy_decimate()
		return {"FINISHED"}

class WM_OT_bf_start(Operator):
	'''
	Is calling bf_start from the module called operators.
	Check out further info in there.
	'''
	bl_label = "bf_start"
	bl_idname = "wm.bf_start"
	bl_description = "Start bruteforce over selected shape keys."

	def execute(self, context):
		operators.bf_start()
		return {"FINISHED"}

class WM_OT_ga_start(Operator):
	'''
	Is calling ga_start from the module called operators.
	Check out further info in there.
	'''
	bl_label = "ga_start"
	bl_idname = "wm.ga_start"
	bl_description = "Start genetic muatation over selected shape keys."

	def execute(self, context):
		operators.ga_start()
		return {"FINISHED"}

class WM_OT_gd_start(Operator):
	'''
	Is calling gd_start from the module called operators.
	Check out further info in there.
	'''
	bl_label = "gd_start"
	bl_idname = "wm.gd_start"
	bl_description = "Start gradient descent over selected shape keys."

	def execute(self, context):
		operators.gd_start()
		return {"FINISHED"}

class WM_OT_ranking(Operator):
	'''
	Is calling ranking from the module called operators.
	Check out further info in there.
	'''
	bl_label = "ranking"
	bl_idname = "wm.ranking"
	bl_description = "Go to indivual by ranking."

	def execute(self, context):
		operators.ranking()
		return {"FINISHED"}

class WM_OT_render_animation(Operator):
	'''
	Is calling render_animation from the module called operators.
	Check out further info in there.
	'''
	bl_label = "render_animation"
	bl_idname = "wm.render_animation"
	bl_description = "Go to indivual by ranking."

	def execute(self, context):
		operators.render_animation()
		return {"FINISHED"}

class WM_OT_text(Operator):
	'''
	Is calling text from the module called operators.
	Check out further info in there.
	'''
	bl_label = "text"
	bl_idname = "wm.text"
	bl_description = "Generate output at the selected vertex"

	def execute(self, context):
		operators.text()
		return {"FINISHED"}

class WM_OT_selection(Operator):
	'''
	Is calling selection from the module called operators.
	Check out further info in there.
	'''
	bl_label = "selection"
	bl_idname = "wm.selection"
	bl_description = "Select edges by given key and value"

	def execute(self, context):
		operators.selection()
		return {"FINISHED"}

class WM_OT_report_members(Operator):
	'''
	Is calling report_members from the module called operators.
	Check out further info in there.
	'''
	bl_label = "report_members"
	bl_idname = "wm.report_members"
	bl_description = "Generate report as html-format"

	def execute(self, context):
		operators.report_members()
		return {"FINISHED"}

class WM_OT_report_frames(Operator):
	'''
	Is calling report_frames from the module called operators.
	Check out further info in there.
	'''
	bl_label = "report_frames"
	bl_idname = "wm.report_frames"
	bl_description = "Generate report as html-format"

	def execute(self, context):
		operators.report_frames()
		return {"FINISHED"}

class WM_OT_report_quads(Operator):
	'''
	Is calling report_quads from the module called operators.
	Check out further info in there.
	'''
	bl_label = "report_quads"
	bl_idname = "wm.report_quads"
	bl_description = "Generate report as html-format"

	def execute(self, context):
		operators.report_quads()
		return {"FINISHED"}
		
class WM_OT_report_combined(Operator):
	'''
	Is calling report_combined from the module called operators.
	Check out further info in there.
	'''
	bl_label = "report_combined"
	bl_idname = "wm.report_combined"
	bl_description = "Generate report as html-format"

	def execute(self, context):
		operators.report_combined()
		return {"FINISHED"}

class WM_OT_report_chromosomes(Operator):
	'''
	Is calling report_chromosomes from the module called operators.
	Check out further info in there.
	'''
	bl_label = "report_chromosomes"
	bl_idname = "wm.report_chromosomes"
	bl_description = "Generate report as html-format"

	def execute(self, context):
		operators.report_chromosomes()
		return {"FINISHED"}

class WM_OT_report_tree(Operator):
	'''
	Is calling report_tree from the module called operators.
	Check out further info in there.
	'''
	bl_label = "report_tree"
	bl_idname = "wm.report_tree"
	bl_description = "Generate report as html-format"

	def execute(self, context):
		operators.report_tree()
		return {"FINISHED"}

class WM_OT_reset(Operator):
	'''
	Is calling reset from the module called operators.
	Check out further info in there.
	'''
	bl_label = "reset"
	bl_idname = "wm.reset"
	bl_description = "Reset Phaenotyp"

	def execute(self, context):
		operators.reset()
		return {"FINISHED"}

class OBJECT_PT_Phaenotyp(Panel):
	'''
	Panel for Phaenotyp.
	'''
	bl_label = "Phänotyp 0.2.5"
	bl_idname = "OBJECT_PT_custom_panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Phänotyp"

	@classmethod
	def poll(self,context):
		'''
		To hide the panel if no object is available.
		'''
		return context.object is not None

	def draw(self, context):
		'''
		Is running all functions from the module called panel.
		'''
		layout = self.layout
		scene = context.scene
		phaenotyp = scene.phaenotyp
		frame = scene.frame_current
		
		# try to create panels
		# this will make the restart-button also available
		# if there is an error during the other panels
		# for example: the file has been created with an older version
		try:
			# prepare everything
			panel.structure(layout)
			panel.scipy(layout)
			panel.calculation_type(layout)
			panel.supports(layout)
			panel.members(layout)
			panel.quads(layout)
			panel.loads(layout)
			panel.file(layout)
			panel.mode(layout)

			# select and run mode
			selected_mode = eval("panel." + phaenotyp.mode)
			selected_mode(layout)

			# fitness und optimization als Funktion?

			# run if there is a result
			data = scene.get("<Phaenotyp>")
			if data:
				result = data["done"].get(str(frame))
				if result:
					# hide previous boxes
					# (to avoid confusion, if user is changing the setup
					# the setup and the result would not match
					# new setup needs new calculation by pressing reset
					# or by changing frame)
					data["panel_grayed"]["scipy"] = True
					data["panel_grayed"]["supports"] = True
					data["panel_grayed"]["members"] = True
					data["panel_grayed"]["loads"] = True

					panel.visualization(layout)
					panel.text(layout)
					panel.info(layout)
					panel.selection(layout)
					panel.report(layout)
					
		except Exception as error:
			# run error panel
			panel.error(layout, basics.phaenotyp_version)
		
		panel.reset(layout)

classes = (
	phaenotyp_properties,

	WM_OT_set_structure,
	WM_OT_fix_structure,
	WM_OT_set_support,
	WM_OT_set_member,
	WM_OT_set_quad,
	WM_OT_set_load,

	WM_OT_assimilate,
	WM_OT_actuator,
	WM_OT_reach_goal,
	WM_OT_wool_threads,
	WM_OT_crown_shyness,
	WM_OT_store_co,
	WM_OT_restore_co,

	WM_OT_calculate_single_frame,
	WM_OT_calculate_animation,

	WM_OT_optimize_approximate,
	WM_OT_optimize_simple,
	WM_OT_optimize_utilization,
	WM_OT_optimize_complex,
	WM_OT_decimate,

	WM_OT_bf_start,
	WM_OT_ga_start,
	WM_OT_gd_start,
	WM_OT_ranking,
	WM_OT_render_animation,

	WM_OT_text,
	WM_OT_selection,

	WM_OT_report_members,
	WM_OT_report_frames,
	WM_OT_report_quads,
	WM_OT_report_combined,
	WM_OT_report_chromosomes,
	WM_OT_report_tree,

	WM_OT_reset,
	OBJECT_PT_Phaenotyp
)

@persistent
def update_post(scene):
	# only run if Phanotyp is used
	data_available = scene.get("<Phaenotyp>")

	if data_available:
		phaenotyp = scene.phaenotyp
		data = scene["<Phaenotyp>"]

		# only run if member is available
		members_available = data.get("members")
		if members_available:
			members = data["members"]
			frame = scene.frame_current

			result = data["done"].get(str(frame))
			if result:
				geometry.update_geometry_post()

		# apply chromosome if available
		# (to change the shape-key, the result will be correct allready)
		individuals = data.get("individuals")
		if individuals:
			shape_keys = data["structure"].data.shape_keys.key_blocks
			chromosome = individuals[str(frame)]["chromosome"]
			geometry.set_shape_keys(shape_keys, chromosome)
		
		# update translation
		obj = data.get("structure")
		if obj:
			geometry.update_translation()
	
@persistent
def undo(scene):
	'''
	Is handeling the steps when a user is running undo.
	'''
	# only run if Phanotyp is used
	scene = bpy.context.scene
	data_available = scene.get("<Phaenotyp>")
	if data_available:
		phaenotyp = scene.phaenotyp
		frame = scene.frame_current
		data = scene["<Phaenotyp>"]
		structure = data["structure"]
		result = data["done"].get(str(frame))
		# reset only if user is trying to undo during definition
		if structure and not result:
			bpy.ops.object.mode_set(mode = 'OBJECT')
			operators.print_data("Reset because user hit undo.")
			operators.reset()
			bpy.ops.ed.undo_push()

def register():
	'''
	Register all blender specific stuff.
	'''
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

	bpy.types.Scene.phaenotyp = PointerProperty(type=phaenotyp_properties)
	bpy.app.handlers.frame_change_post.append(update_post)
	bpy.app.handlers.undo_pre.append(undo)

def unregister():
	'''
	Unregister all blender specific stuff.
	'''
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)

	del bpy.types.Scene.phaenotyp
	bpy.app.handlers.frame_change_post.remove(update_post)
	bpy.app.handlers.undo_pre.remove(undo)

if __name__ == "__main__":
	'''
	Run mainloop and register all blender specific stuff.
	'''
	register()
