bl_info = {
	"name": "Phänotyp",
	"description": "Genetic algorithm for architectural structures",
	"author": "bewegende Architektur e.U. and Karl Deix",
	"version": (0,3,1),
	"blender": (4,5,0),
	"location": "3D View > Tools",
}

'''
The __init__ file is the main-file to be registert from blender.
It contains and handles all blender properties as well as the panel.
'''

import bpy, blf, time
import traceback
from bpy.props import IntProperty, FloatProperty, BoolProperty, StringProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import Panel, Menu, Operator, PropertyGroup, UIList
from bpy.app.handlers import persistent

from phaenotyp import basics, panel, operators, material, geometry, calculation, ga, report, progress

# pass infos to basics to keep control of used version
# the phaenotyp_version is stored in saved files
basics.blender_version = bl_info["blender"]
basics.phaenotyp_version = bl_info["version"]

# timer to run jobs
class phaenotyp_jobs(bpy.types.Operator):
	bl_idname = "wm.phaenotyp_jobs"
	bl_label = "Timer to run jobs"

	#_timer = None

	def modal(self, context, event):
		if event.type == 'TIMER':
			jobs = basics.jobs
			# if job available
			if len(jobs) > 0:
				# get job and arguments
				entry = jobs[0]
				
				# if argument
				if len(entry) == 2:
					job = entry[0]
					arg = entry[1]
					# run job with argument
					job(arg)
				
				else:
					# without
					job = entry[0]
					job()
				
				# delete job when done
				jobs.pop(0)
				
				# update time
				now = time.time()				
				basics.time_elapsed = now - basics.time_started
				basics.jobs_percentage = 100 - (100 / basics.jobs_total * len(jobs))
				jobs_done = basics.jobs_total - len(jobs)
				time_for_job = basics.avoid_div_zero(basics.time_elapsed, jobs_done)
				jobs_left = basics.jobs_total - jobs_done
				basics.time_left = time_for_job * jobs_left
				context.scene.phaenotyp.jobs_percentage = int(basics.jobs_percentage)
				
			else:
				# if webinterface not running, close window
				# otherwise is_running_jobs is set by stop_stop
				if progress.http.active == False:
					basics.is_running_jobs = False
				
				geometry.update_geometry_post()
				
				return {'CANCELLED'}

		return {'PASS_THROUGH'}

	def execute(self, context):
		wm = context.window_manager
		self._timer = wm.event_timer_add(0.1, window=context.window)
		
		# set variable to hide other panels
		basics.is_running_jobs = True
		
		# add infos to basics
		basics.jobs_total = len(basics.jobs)
		basics.time_started = time.time()
		
		wm.modal_handler_add(self)
		return {'RUNNING_MODAL'}

	def cancel(self, context):
		wm = context.window_manager
		wm.event_timer_remove(self._timer)

# timer to run webinterface
class phaenotyp_webinterface(bpy.types.Operator):
	bl_idname = "wm.phaenotyp_webinterface"
	bl_label = "Timer to run webinterface"

	#_timer = None

	def modal(self, context, event):
		if event.type == 'TIMER':
			if progress.http.active == True:
				progress.http.hosting()
			
			else:
				return {'CANCELLED'}

		return {'PASS_THROUGH'}

	def execute(self, context):
		wm = context.window_manager
		self._timer = wm.event_timer_add(0.1, window=context.window)
		
		progress.http.setup()
		
		wm.modal_handler_add(self)
		return {'RUNNING_MODAL'}

	def cancel(self, context):
		wm = context.window_manager
		wm.event_timer_remove(self._timer)
		
# terminal output on screen
def phaenotyp_terminal(self, context):
	for i, text in enumerate(basics.terminal):
		blf.position(0, 10, 130-i*12, 0)
		blf.size(0, 10)
		blf.color(0, 1,1,1,1)
		blf.draw(0, text)
		
# variables
class phaenotyp_properties(PropertyGroup):
	'''
	Is holding all variables for the panel.
	'''
	if "from_hull":
		fh_methode: EnumProperty(
			name = "fh_methode",
			description = "Work with grid or spline",
			items = [
					("-", "-", ""),
					("grid", "Grid", ""),
					("path", "Path", "")
					],
			default = "-",
			update = geometry.fh_update
			)

		fh_input_type: EnumProperty(
			name = "fh_input_type",
			description = "Work with grid or spline",
			items = [
					("-", "-", ""),
					("even", "Even", ""),
					("individual", "Individual", "")
					],
			default = "-",
			update = geometry.fh_update
			)
		
		fh_w: FloatProperty(
			name = "fh_w",
			description = "Width of structure",
			default = 7.0,
			min = 1.0,
			max = 100.0,
			update = geometry.fh_update
			)
		
		fh_d: FloatProperty(
			name = "fh_d",
			description = "Depth of structure",
			default = 7.0,
			min = 1.0,
			max = 100.0,
			update = geometry.fh_update
			)
		
		fh_h: FloatProperty(
			name = "fh_h",
			description = "Height of structure",
			default = 3.0,
			min = 1.0,
			max = 100.0,
			update = geometry.fh_update
			)
		
		fh_o_x: FloatProperty(
			name = "fh_o_x",
			description = "Offset in x-direction",
			default = 0.0,
			min = -10.0,
			max = 10.0,
			update = geometry.fh_update
			)
		
		fh_o_y: FloatProperty(
			name = "fh_o_y",
			description = "Offset in y-direction",
			default = 0.0,
			min = -10.0,
			max = 10.0,
			update = geometry.fh_update
			)
		
		fh_o_z: FloatProperty(
			name = "fh_o_z",
			description = "Offset in z-direction",
			default = 0.0,
			min = -10.0,
			max = 10.0,
			update = geometry.fh_update
			)

		fh_rot: FloatProperty(
			name = "fh_rot",
			description = "Rotation in z-direction",
			default = 0.0,
			min = 0.0,
			max = 360.0,
			update = geometry.fh_update
			)

		fh_amount: IntProperty(
			name = "fh_amount",
			description = "Amount of segments",
			default = 3,
			min = 1,
			max = 12,
			update = geometry.fh_update
			)

		fh_o_c: FloatProperty(
			name = "fh_o_c",
			description = "Offset along path",
			default = 0.0,
			min = 0.0,
			max = 10.0,
			update = geometry.fh_update
			)
		
	if "setup":
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

	if "supports":
		loc_x: BoolProperty(name = 'loc_x', default = True)
		loc_y: BoolProperty(name = 'loc_y', default = True)
		loc_z: BoolProperty(name = 'loc_z', default = True)
		rot_x: BoolProperty(name = 'rot_x', default = False)
		rot_y: BoolProperty(name = 'rot_y', default = False)
		rot_z: BoolProperty(name = 'rot_z', default = False)

	if "members":
		profile_type: EnumProperty(
			name = "Profile Type",
			description = "Type of structural profile",
			items = [
				("round_hollow", "Round Hollow", "Hollow circular profile, like a tube or pipe"),
				("round_solid", "Round Solid", "Solid circular profile, like a rod"),
				("rect_hollow", "Rectangular Hollow", "Hollow rectangular profile, like RHS"),
				("rect_solid", "Rectangular Solid", "Solid rectangular profile, like a flat bar"),
				("standard_profile", "Standard Profile", "Standard profile like IPE"),
				("large_steel_hollow", "Large Steel Hollow", "Large Steel Hollow if standard profile is not available")
			]
		)

		height: FloatProperty(
			name = "height",
			description = "Height or diameter of the profile in cm",
			default = 10.0,
			min = 0.1,
			max = 100.0
			)

		width: FloatProperty(
			name = "width",
			description = "Width of profile in cm",
			default = 6.0,
			min = 0.1,
			max = 100.0
			)
		
		wall_thickness: FloatProperty(
			name = "wall_thickness",
			description = "Wallthickness of the profile",
			default = 1.0,
			min = 0.1,
			max = 50.0
			)

		member_orientation: EnumProperty(
			name = "member_orientation",
			description = "Orientation of Member",
			items = [
					("z_up", "Z-up", ""),
					("normal", "Normal", ""),
					("optimize", "Optimize", "")
				   ]
			)
		
		member_angle: FloatProperty(
			name = "member_angle",
			description = "Angle added to oriention",
			default = 0.0,
			min = 0.0,
			max = 360.0
			)
		
		buckling_resolution: IntProperty(
			name = "buckling_resolution",
			description = "Amount of connected members that form an entity for buckling (choose 1 if unsure).",
			default = 1,
			min = 1,
			max = 12
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
			description = "Will be applied to all defined members",
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
		
		acceptable_sigma_quads: FloatProperty(
			name = "acceptable_sigma_quads",
			description = "Acceptable sigma kN/cm²",
			default = 16.0,
			min = 0.01,
			max = 30.0
			)

		acceptable_shear_quads: FloatProperty(
			name = "acceptable_shear_quads",
			description = "Acceptable shear kN/cm²",
			default = 9.5,
			min = 0.01,
			max = 30.0
			)

		acceptable_sigmav_quads: FloatProperty(
			name = "acceptable_sigmav kN/cm²",
			description = "Acceptable sigmav",
			default = 10.5,
			min = 23.5,
			max = 30.0
			)

		kn_custom_quads: StringProperty(
			name = "kn_custom_quads",
			description = "kn of custom material",
			default = "16.5, 15.8, 15.3, 14.8, 14.2, 13.5, 12.7, 11.8, 10.7, 9.5, 8.2, 6.9, 5.9, 5.1, 4.4, 3.9, 3.4, 3.1, 2.7, 2.5, 2.2, 2.0, 1.9, 1.7, 1.6"
			)
		
	if "quads":
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
			description = "Will be applied to all defined quads",
			default = 1.35,
			min = 0.8,
			max = 1.5
			)
			
	if "loads":
		load_type: EnumProperty(
			name = "load_type",
			description = "Load types",
			items = [
					("vertices", "Vertices", ""),
					("edges", "Edges", ""),
					("faces", "Faces", "")
				   ],
			update = basics.set_selection_for_load
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
			description = "Will be applied to all defined loads",
			default = 1.5,
			min = 0.8,
			max = 4
			)

	if "transformation":
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

	if "mode":
		items = [
			("transformation", "Transformation", ""),
			("single_frame", "Single frame", ""),
			("animation", "Animation", ""),
			("bruteforce", "Bruteforce", ""),
			("gradient_descent", "Gradient descent", ""),
			("genetic_algorithm", "Genetic algorithm", "")
		]

		if basics.lab_usage:
			items.append(("bayesian_modeling", "Bayesian modeling", ""))
	
		mode: EnumProperty(
			name = "mode",
			description = "Select mode to start",
			items = items,
			default = "single_frame"
			)
	
	if "progress":
		jobs_percentage: IntProperty(
			name = "jobs_percentage",
			description = "Jobs done",
			subtype = "PERCENTAGE",
			default = 50,
			min = 0,
			max = 100
			)
	
	if "ga":
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

		mate_type: EnumProperty(
			name = "mate_type",
			description = "Type of mating",
			items = [
					("direct", "direct", ""),
					("morph", "morph", "")
				   ]
			)

	if "gd":
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
			min = 0.0,
			max = 0.1
			)

		gd_max_iteration: IntProperty(
			name = "gd_max_iteration",
			description="Max number of iteration to avoid endless loop",
			default = 100,
			min = 10,
			max = 1000
			)

	if "bm":
		bm_iterations: IntProperty(
			name = "iterations",
			description="Iterations of baysian modelling",
			default = 5,
			min = 1,
			max = 50
			)
						
		bm_acq: EnumProperty(
			name = "acq",
			description = "Acquisition",
			items = [
					("UpperConfidenceBound", "Upper Confidence Bound", ""),
					("ProbabilityOfImprovement", "Probability Of Improvement", ""),
					("ExpectedImprovement", "Expected Improvement", ""),
					("ConstantLiar", "Constant Liar", "")
				   ]
			)

		bm_factor: IntProperty(
			name = "factor",
			description="Factor for kappa and xi",
			subtype = "PERCENTAGE",
			default = 50,
			min = 0,
			max = 100
			)
			
	if "fitness":
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

		fitness_average_sigma_members: FloatProperty(
			name = "average sigma",
			description = "Average sigma of all members",
			default = 0.0,
			min = 0.0,
			max = 1.0
			)
			
		fitness_average_sigmav_quads: FloatProperty(
			name = "average sigma",
			description = "Average sigmav of all quads",
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

		fitness_deflection_members: FloatProperty(
			name = "deflection",
			description = "Average deflection of the elements",
			default = 0.0,
			min = 0.0,
			max = 1.0
			)

		fitness_deflection_members_invert: BoolProperty(
			name = 'deflection invert',
			description = "Activate to maximize the deflection",
			default = False
		)
		
		fitness_deflection_quads: FloatProperty(
			name = "deflection",
			description = "Average deflection of the elements",
			default = 0.0,
			min = 0.0,
			max = 1.0
			)
		
		fitness_deflection_quads_invert: BoolProperty(
			name = 'deflection invert',
			description = "Activate to maximize the deflection",
			default = False
		)

	if "viz":
		ranking: IntProperty(
			name = "ranking",
			description="Show results from best to worth fitness",
			default = 0,
			min = 0,
			max = 250
			)
		
		viz_show_structure: BoolProperty(name = 'viz_show_structure', default = False, update = geometry.hide_reveal)
		viz_show_supports: BoolProperty(name = 'viz_show_supports', default = False, update = geometry.hide_reveal)
		viz_show_loads: BoolProperty(name = 'viz_show_loads', default = False, update = geometry.hide_reveal)
		viz_show_members: BoolProperty(name = 'viz_show_members', default = True, update = geometry.hide_reveal)
		viz_show_quads: BoolProperty(name = 'viz_show_quads', default = True, update = geometry.hide_reveal)
		viz_show_stresslines: BoolProperty(name = 'viz_show_stresslines', default = True, update = geometry.hide_reveal)

		forces_fd: EnumProperty(
			name = "forces_fd",
			description = "Force types",
			items = [
						("sigma", "Sigma", ""),
						("axial", "Axial", ""),
						("utilization", "Utilization", "")
					],
			update = geometry.viz_update
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
						("shear_z", "Shear Z", ""),
						("torque", "Torque", ""),
						("lever_arm", "Lever arm", ""),
						("utilization", "Utilization", ""),
						("normal_energy", "Normal energy", ""),
						("moment_energy", "Moment energy", ""),
						("strain_energy", "Strain energy", "")
					],
			update = geometry.viz_update
			)
				
		forces_quads: EnumProperty(
			name = "forces_quads",
			description = "Force types",
			items = [
						("s_x", "S X", ""),
						("s_y", "S Y", ""),
						("T_xy", "T XY", ""),
						("s_1", "S 1", ""),
						("s_2", "S 2", "")
					],
			update = geometry.viz_update,
			default = "s_1"
			)

		viz_boundaries_members: FloatProperty(
			name = "viz_boundaries_members",
			description = "Max / min value of selected force in all frames",
			update = geometry.viz_update,
			default = 50
			)

		viz_boundaries_quads: FloatProperty(
			name = "viz_boundaries_quads",
			description = "Max / min value of selected force in all frames",
			update = geometry.viz_update,
			default = 50
			)
		
		viz_scale: FloatProperty(
			name = "viz_scale",
			description = "scale",
			update = geometry.viz_update,
			subtype = "PERCENTAGE",
			default = 50,
			min = 0.001,
			max = 100
			)
		
		viz_deflection: FloatProperty(
			name = "viz_scale",
			description = "deflected / original",
			update = geometry.viz_update,
			subtype = "PERCENTAGE",
			default = 50,
			min = 0.001,
			max = 100
			)

		viz_stressline_scale: FloatProperty(
			name = "viz_stressline_scale",
			description = "scale",
			update = geometry.viz_update,
			subtype = "PERCENTAGE",
			default = 50,
			min = 0.001,
			max = 200
			)

		viz_stressline_length: FloatProperty(
			name = "viz_stressline_length",
			description = "length",
			update = geometry.viz_update,
			subtype = "PERCENTAGE",
			default = 50,
			min = 0.001,
			max = 200
			)

	if "profiles":
		profiles: EnumProperty(
			name = "profiles",
			description = "Profiles",
			items = material.dropdown_profiles
			)
	
	if "optimization":
		optimization_fd: EnumProperty(
			name = "optimization",
			description = "Enables sectional optimization after each frame",
			items = [
						("none", "Members none", ""),
						("approximate", "Members approximate", "")
					]
			)

		optimization_pn: EnumProperty(
			name = "optimization",
			description = "Enables sectional optimization after each frame",
			items = [
						("none", "Members none (rotation only)", ""),
						("pipes", "Members utilization pipes", ""),
						("rect", "Members utilization rect", ""),
						("profiles", "Members utilization profiles", ""),
						("lsh", "Members utilization large steel hollow", "")
					]
			)

		optimization_quads: EnumProperty(
			name = "optimization",
			description = "Enables sectional optimization after each frame",
			items = [
						("none", "Quads none", ""),
						("approximate", "Quads approximate", ""),
						("utilization", "Quads utilization", "")
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
	
	if "selection":
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
						("height", "Height", ""),
						("wall_thickness", "Wall thickness", ""),
						("weight", "weight", ""),
						("length", "length", ""),
						("sigma", "Sigma", ""),
						("axial", "Axial", ""),
						("utilization", "Utilization", "")
					],
			default = "height"
			)

		selection_key_pn: EnumProperty(
			name = "selection_key_pn",
			description = "Key for selection",
			items = [
						("id", "Id", ""),
						("height", "Height", ""),
						("width", "Width", ""),
						("weight", "Weight", ""),
						("length", "Length", ""),
						("max_long_stress", "Max long stress", ""),
						("max_tau_shear_y", "Max tau shear y", ""),
						("max_tau_shear_z", "Max tau shear z", ""),
						("max_tau_torsion", "Max tau torsion", ""),
						("max_sum_tau", "Max sum tau", ""),
						("max_sigma", "Max sigma", ""),
						("max_lever_arm", "Max lever arm", ""),
						("utilization", "Utilization", "")
					],
			default = "height"
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
						("shear_y", "Shear_Y", ""),
						("s_x", "S X", ""),
						("s_y", "S Y", ""),
						("T_xy", "T XY", ""),
						("s_1", "S 1", ""),
						("s_2", "S 2", "")
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
	
	if "nn":
		nn_learning_rate: FloatProperty(
			name = "nn_learning_rate",
			description="Learning Rate",
			default = 0.1,
			min = 0.001,
			max = 1.0
			)

		nn_epochs: IntProperty(
			name = "nn_epochs",
			description="Number of iterations",
			default = 5000,
			min = 1000,
			max = 50000
			)
	
	if "diagrams":
		diagram_fitness: EnumProperty(
			name = "diagram_fitness",
			description = "Fitness to work with",
			items = [
					("weighted", "Weighted", ""),
					("volume", "Volume", ""),
					("area", "Area", ""),
					("weight", "Weight", ""),
					("rise", "Rise", ""),
					("span", "Span", ""),
					("cantilever", "Cantilever", ""),
					("deflection_members", "Deflection Members", ""),
					("average_sigma_members", "Average sigma members", ""),
					("deflection_quads", "Deflection quads", ""),
					("average_sigmav_quads", "Average sigmav quads", ""),
					("average_strain_energy", "Average strain energy", "")
					],
			default = "weighted",
			update = geometry.create_diagram
			)

		diagram_key_0: IntProperty(
			name = "diagram_key_0",
			description="First key",
			default = 0,
			update = geometry.create_diagram,
			min = 0
			)

		diagram_key_1: IntProperty(
			name = "diagram_key_1",
			description="Second key",
			default = 1,
			update = geometry.create_diagram,
			min = 0
			)
		
		diagram_scale: FloatProperty(
			name = "diagram_scale",
			description = "Factor to scale diagramm",
			update = geometry.create_diagram,
			default = 1,
			min = 0
			)
			
# handle lists in panel
# based on code by sinestesia and support by Gorgious
# check out this pages for explanation:
# https://sinestesia.co/blog/tutorials/using-uilists-in-blender/
# https://blenderartists.org/t/create-and-handle-multiple-uilists
class PHAENOTYP_list_item(PropertyGroup):
	item_name: StringProperty(name="item_name", default="Name", update = geometry.fh_update)
	item_value: FloatProperty(name="item_value", default=3.0, update = geometry.fh_update)

class PHAENOTYP_UL_List(UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		layout.label(text=item.item_name)
		layout.label(text=str(item.item_value))

class LIST_OT_new_item(Operator):
	bl_idname = "phaenotyp_lists.new_item"
	bl_label = "Add a new item"

	phaenotyp_lists: bpy.props.StringProperty()
	current_index: bpy.props.StringProperty()
	
	def execute(self, context):
		phaenotyp_lists = getattr(context.scene, self.phaenotyp_lists)
		phaenotyp_lists.add()
		
		geometry.fh_update(self, context)
		return{'FINISHED'}

class LIST_OT_delete_item(Operator):
	bl_idname = "phaenotyp_lists.delete_item"
	bl_label = "Deletes an item"

	phaenotyp_lists: bpy.props.StringProperty()
	current_index: bpy.props.StringProperty()

	def execute(self, context):
		phaenotyp_lists = getattr(context.scene, self.phaenotyp_lists)
		index = getattr(context.scene, self.current_index)
		
		phaenotyp_lists.remove(index)
		
		new_index = min(max(0, index - 1), len(phaenotyp_lists) - 1)
		bpy.context.scene[self.current_index] = new_index
		
		geometry.fh_update(self, context)
		return{'FINISHED'}

class LIST_OT_move_item(Operator):
	bl_idname = "phaenotyp_lists.move_item"
	bl_label = "Move an item in the list"
	
	direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))
	phaenotyp_lists: bpy.props.StringProperty()
	current_index: bpy.props.StringProperty()
	
	def move_index(self, phaenotyp_lists, index):
		list_length = len(phaenotyp_lists) - 1
		new_index = index + (-1 if self.direction == 'UP' else 1)
		new_index = max(0, min(new_index, list_length))
		bpy.context.scene[self.current_index] = new_index
		
	def execute(self, context):
		phaenotyp_lists = getattr(context.scene, self.phaenotyp_lists) 
		index = getattr(context.scene, self.current_index) 
		neighbor = index + (-1 if self.direction == 'UP' else 1)
		phaenotyp_lists.move(neighbor, index)
		self.move_index(phaenotyp_lists, index)
		
		geometry.fh_update(self, context)
		return{'FINISHED'}
		
class WM_OT_set_hull(Operator):
	'''
	Is calling set_hull from the module called operators.
	Check out further info in there.
	'''
	bl_label = "set_hull"
	bl_idname = "wm.set_hull"
	bl_description = "Set hull to work with"

	def execute(self, context):
		operators.set_hull()
		return {"FINISHED"}

class WM_OT_set_path(Operator):
	'''
	Is calling set_path from the module called operators.
	Check out further info in there.
	'''
	bl_label = "set_path"
	bl_idname = "wm.set_path"
	bl_description = "Set path to work with"

	def execute(self, context):
		operators.set_path()
		return {"FINISHED"}
		
class WM_OT_from_hull(Operator):
	'''
	Is calling from_hull from the module called operators.
	Check out further info in there.
	'''
	bl_label = "from_hull"
	bl_idname = "wm.from_hull"
	bl_description = "Is creating a structure from the given hull"

	def execute(self, context):
		operators.from_hull()
		return {"FINISHED"}
					
class WM_OT_curve_to_mesh_straight(Operator):
	'''
	Is calling curve_to_mesh_straight from the module called operators.
	Check out further info in there.
	'''
	bl_label = "curve_to_mesh_straight"
	bl_idname = "wm.curve_to_mesh_straight"
	bl_description = "Is converting straight curves to work with phaenotyp"

	def execute(self, context):
		operators.curve_to_mesh_straight()
		return {"FINISHED"}

class WM_OT_curve_to_mesh_curved(Operator):
	'''
	Is calling curve_to_mesh_curved from the module called operators.
	Check out further info in there.
	'''
	bl_label = "curve_to_mesh_curved"
	bl_idname = "wm.curve_to_mesh_curved"
	bl_description = "Is converting curved curves to work with phaenotyp"

	def execute(self, context):
		operators.curve_to_mesh_curved()
		return {"FINISHED"}

class WM_OT_meta_to_mesh(Operator):
	'''
	Is calling meta_to_mesh from the module called operators.
	Check out further info in there.
	'''
	bl_label = "meta_to_mesh"
	bl_idname = "wm.meta_to_mesh"
	bl_description = "Is converting metaballss to work with phaenotyp"

	def execute(self, context):
		operators.meta_to_mesh()
		return {"FINISHED"}
		
class WM_OT_mesh_to_quads_simple(Operator):
	'''
	Is calling mesh_to_quads_simple from the module called operators.
	Check out further info in there.
	'''
	bl_label = "mesh_to_quads_simple"
	bl_idname = "wm.mesh_to_quads_simple"
	bl_description = "Is converting triangels to quads by calling buildin operator to work with phaenotyp quads"

	def execute(self, context):
		operators.mesh_to_quads_simple()
		return {"FINISHED"}

class WM_OT_mesh_to_quads_complex(Operator):
	'''
	Is calling mesh_to_quads_complex from the module called operators.
	Check out further info in there.
	'''
	bl_label = "mesh_to_quads_complex"
	bl_idname = "wm.mesh_to_quads_complex"
	bl_description = "Is subdividing the mesh to create quad meshes to work with phaenotyp quads"

	def execute(self, context):
		operators.mesh_to_quads_complex()
		return {"FINISHED"}

class WM_OT_union(Operator):
	'''
	Is calling union from the module called operators.
	Check out further info in there.
	'''
	bl_label = "union"
	bl_idname = "wm.union"
	bl_description = "Is creating intersections of faces with boolean operator"

	def execute(self, context):
		operators.union()
		return {"FINISHED"}

class WM_OT_automerge(Operator):
	'''
	Is calling automerge from the module called operators.
	Check out further info in there.
	'''
	bl_label = "automerge"
	bl_idname = "wm.automerge"
	bl_description = "Is creating vertices on intersections by calling automerge"

	def execute(self, context):
		operators.automerge()
		return {"FINISHED"}

class WM_OT_simplify_edges(Operator):
	'''
	Is calling simplify_edges from the module called operators.
	Check out further info in there.
	'''
	bl_label = "simplify_edges"
	bl_idname = "wm.simplify_edges"
	bl_description = "Is combining edges to work as single columns in phanotyp"

	def execute(self, context):
		operators.simplify_edges()
		return {"FINISHED"}

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

class WM_OT_optimize_members(Operator):
	'''
	Is calling the selected optimization from the module called operators.
	Check out further info in there.
	'''
	bl_label = "optimize_members"
	bl_idname = "wm.optimize_members"
	bl_description = "Sectional performance of members"

	def execute(self, context):
		operators.optimize_members()
		return {"FINISHED"}

class WM_OT_optimize_approximate(Operator):
	'''
	Is calling optimize_approximate from the module called operators.
	'''
	bl_label = "optimize_approximate"
	bl_idname = "wm.optimize_approximate"
	bl_description = "Approximate sectional performance (force distribution)"
	
	def execute(self, context):
		operators.optimize_approximate()
		return {"FINISHED"}

class WM_OT_optimize_quads_approximate(Operator):
	'''
	Is calling optimize_quads_sectional from the module called operators.
	Check out further info in there.
	'''
	bl_label = "optimize_quads_approximate"
	bl_idname = "wm.optimize_quads_approximate"
	bl_description = "Quad approximate sectional performance"

	def execute(self, context):
		operators.quads_approximate_sectional()
		return {"FINISHED"}

class WM_OT_optimize_quads_utilization(Operator):
	'''
	Is calling optimize_quads_utilization_sectional from the module called operators.
	Check out further info in there.
	'''
	bl_label = "optimize_quads_utilization"
	bl_idname = "wm.optimize_quads_utilization"
	bl_description = "Quad utilization sectional performance"

	def execute(self, context):
		operators.quads_utilization_sectional()
		return {"FINISHED"}
		
class WM_OT_decimate(Operator):
	'''
	Is calling topolgy_decimate from the module called operators.
	Check out further info in there.
	'''
	bl_label = "topolgy_decimate"
	bl_idname = "wm.topolgy_decimate"
	bl_description = "Decimate topological performance"

	def execute(self, context):
		operators.topolgy_decimate()
		return {"FINISHED"}

class WM_OT_decimate_apply(Operator):
	'''
	Is calling topolgy_decimate_apply from the module called operators.
	Check out further info in there.
	'''
	bl_label = "topolgy_decimate_apply"
	bl_idname = "wm.topolgy_decimate_apply"
	bl_description = "Apply topological performance"

	def execute(self, context):
		operators.topolgy_decimate_apply()
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

class WM_OT_bm_install(Operator):
	'''
	Is calling bm_install from the module called operators.
	Check out further info in there.
	'''
	bl_label = "bm_install"
	bl_idname = "wm.bm_install"
	bl_description = "Install external libs (can take a few minutes)"

	def execute(self, context):
		operators.bm_install()
		return {"FINISHED"}
		
class WM_OT_bm_start(Operator):
	'''
	Is calling bm_start from the module called operators.
	Check out further info in there.
	'''
	bl_label = "bm_start"
	bl_idname = "wm.bm_start"
	bl_description = "Start bayesian modelling over selected shape keys."

	def execute(self, context):
		operators.bm_start()
		return {"FINISHED"}
		
class WM_OT_run_web(Operator):
	'''
	Is running the webserver.
	'''
	bl_label = "run_web"
	bl_idname = "wm.run_web"
	bl_description = "Is running the webinterface to show current progres."

	def execute(self, context):
		progress.run()
		return {"FINISHED"}
		
class WM_OT_stop_jobs(Operator):
	'''
	Stop all jobs by deleteing the joblist.
	'''
	bl_label = "stop_jobs"
	bl_idname = "wm.stop_jobs"
	bl_description = "Is stopping all jobs."

	def execute(self, context):
		basics.jobs = []
		
		# stop webserver
		if progress.http.active == True:
			progress.http.active = False
		
		if len(basics.jobs) == 0:
			basics.is_running_jobs = False
			
		return {"FINISHED"}
		
class WM_OT_get_boundaries(Operator):
	'''
	Is calling get_boundaries from the module called operators.
	Check out further info in there.
	'''
	bl_label = "get_boundaries"
	bl_idname = "wm.get_boundaries"
	bl_description = "Get the lowest and highest value of all frames"

	def execute(self, context):
		operators.get_boundaries()
		return {"FINISHED"}

class WM_OT_get_boundary_diagram(Operator):
	'''
	Is calling get_boundary_diagram from the module called operators.
	Check out further info in there.
	'''
	bl_label = "get_boundary_diagram"
	bl_idname = "wm.get_boundary_diagram"
	bl_description = "Get the lowest and highest value of all frames"

	def execute(self, context):
		operators.get_boundary_diagram()
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

class WM_OT_precast(Operator):
	'''
	Is calling precast from the module called operators.
	Check out further info in there.
	'''
	bl_label = "precast"
	bl_idname = "wm.precast"
	bl_description = "Precast result with given shape-keys"

	def execute(self, context):
		operators.precast()
		return {"FINISHED"}

class WM_OT_diagram(Operator):
	'''
	Is centering the view to fit the created diagram.
	Check out further info in there.
	'''
	bl_label = "diagram"
	bl_idname = "wm.diagram"
	bl_description = "Center view to fit diagram"

	def execute(self, context):
		geometry.create_diagram(self, context)
		data = bpy.context.scene['<Phaenotyp>']
		scene_id = data["scene_id"]
		obj = bpy.data.objects["<Phaenotyp>diagram_" + str(scene_id)]
		obj.select_set(True)
		bpy.context.view_layer.objects.active = obj
		bpy.ops.view3d.view_selected()
		obj.select_set(False)
			
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

class OBJECT_PT_Phaenotyp_pre(Panel):
	'''
	Panel for Phaenotyp.
	'''
	bl_label = "Prepare"
	bl_idname = "OBJECT_PT_Phaenotyp_pre"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_options = {"DEFAULT_CLOSED"}
	bl_category = basics.phaenotyp_name

	@classmethod
	def poll(self,context):
		'''
		To hide the panel if no object is available.
		'''
		if context.object is not None:
			if basics.is_running_jobs == False:
				return True

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
			# from hull and prepare
			panel.pre(layout)
					
		except Exception as error:
			# run error panel
			print(error)
			traceback.print_exc()
			panel.error(layout, basics.phaenotyp_version)

class OBJECT_PT_Phaenotyp_setup(Panel):
	'''
	Panel for Phaenotyp.
	'''
	bl_label = "Setup"
	bl_idname = "OBJECT_PT_Phaenotyp_setup"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_options = {"DEFAULT_CLOSED"}
	bl_category = basics.phaenotyp_name

	@classmethod
	def poll(self,context):
		'''
		To hide the panel if no object is available.
		'''
		if context.object is not None:
			if len(basics.jobs) == 0:
				if basics.is_running_jobs == False:
					return True

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
			# setup and start
			panel.structure(layout)
			panel.scipy(layout)
			panel.calculation_type(layout)
			panel.supports(layout)
			panel.members(layout)
			panel.quads(layout)
			panel.loads(layout)
			panel.file(layout)
				
		except Exception as error:
			# run error panel
			print(error)
			traceback.print_exc()
			panel.error(layout, basics.phaenotyp_version)

class OBJECT_PT_Phaenotyp_run(Panel):
	'''
	Panel for Phaenotyp.
	'''
	bl_label = "Run"
	bl_idname = "OBJECT_PT_Phaenotyp_run"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = basics.phaenotyp_name

	@classmethod
	def poll(self,context):
		'''
		To hide the panel if no object is available.
		'''
		scene = context.scene
		data = scene.get("<Phaenotyp>")
		if data:
			if data["panel_state"]["file"]:
				if data["panel_state"]["members"] or data["panel_state"]["quads"]:
					if basics.is_running_jobs == False:
						return True

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
			# setup and start
			panel.mode(layout)

			# select and run mode
			selected_mode = eval("panel." + phaenotyp.mode)
			selected_mode(layout)
					
		except Exception as error:
			# run error panel
			print(error)
			traceback.print_exc()
			panel.error(layout, basics.phaenotyp_version)

class OBJECT_PT_Phaenotyp_progress(Panel):
	'''
	Panel for Phaenotyp.
	'''
	bl_label = "Progress"
	bl_idname = "OBJECT_PT_Phaenotyp_progress"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = basics.phaenotyp_name
	
	@classmethod
	def poll(self,context):
		'''
		To hide the panel if no object is available.
		'''
		if basics.is_running_jobs == True:
			return True

	def draw(self, context):
		'''
		Is running all functions from the module called panel.
		'''
		layout = self.layout
		panel.show_progress(layout)
				
class OBJECT_PT_Phaenotyp_post(Panel):
	'''
	Panel for Phaenotyp.
	'''
	bl_label = "Post"
	bl_idname = "OBJECT_PT_Phaenotyp_post"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = basics.phaenotyp_name
	
	@classmethod
	def poll(self,context):
		'''
		To hide the panel if no object is available.
		'''
		scene = context.scene
		data = scene.get("<Phaenotyp>")
		frame = scene.frame_current
		
		# only show if result is available
		if data:
			result = data["done"].get(str(frame))
			if result:
				if basics.is_running_jobs == False:
					return True

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
			# get data and result
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
					data["panel_grayed"]["quads"] = True
					data["panel_grayed"]["loads"] = True

					panel.visualization(layout)
					#panel.i_profiles(layout) -> Altes Modul
					panel.text(layout)
					panel.info(layout)
					panel.selection(layout)
					panel.precast(layout)
					panel.report(layout)
					panel.diagram(layout)
					
		except Exception as error:
			# run error panel
			print(error)
			traceback.print_exc()
			panel.error(layout, basics.phaenotyp_version)

class OBJECT_PT_Phaenotyp_reset(Panel):
	'''
	Panel for Phaenotyp.
	'''
	bl_label = "Reset"
	bl_idname = "OBJECT_PT_Phaenotyp_reset"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_options = {"DEFAULT_CLOSED"}
	bl_category = basics.phaenotyp_name
	
	@classmethod
	def poll(self,context):
		'''
		To hide the panel if no object is available.
		'''
		#return context.object is not None
		if basics.is_running_jobs == False:
			return True

	def draw(self, context):
		'''
		Is running all functions from the module called panel.
		'''
		layout = self.layout
		panel.reset(layout)
	
classes = (
	phaenotyp_properties,

	WM_OT_curve_to_mesh_straight,
	WM_OT_curve_to_mesh_curved,
	WM_OT_mesh_to_quads_simple,
	WM_OT_mesh_to_quads_complex,
	WM_OT_meta_to_mesh,
	
	WM_OT_set_hull,
	WM_OT_set_path,
	WM_OT_from_hull,
	
	WM_OT_automerge,
	WM_OT_union,
	WM_OT_simplify_edges,

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

	WM_OT_optimize_members,
	WM_OT_optimize_approximate,
	WM_OT_optimize_quads_approximate,
	WM_OT_optimize_quads_utilization,
	WM_OT_decimate,
	WM_OT_decimate_apply,

	WM_OT_bf_start,
	WM_OT_ga_start,
	WM_OT_gd_start,
	WM_OT_bm_install,
	WM_OT_bm_start,
	
	WM_OT_run_web,
	WM_OT_stop_jobs,
	
	WM_OT_get_boundaries,
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
	
	WM_OT_precast,
	
	WM_OT_get_boundary_diagram,
	WM_OT_diagram,
	
	WM_OT_reset,
	
	OBJECT_PT_Phaenotyp_pre,
	OBJECT_PT_Phaenotyp_setup,
	OBJECT_PT_Phaenotyp_run,
	OBJECT_PT_Phaenotyp_progress,
	OBJECT_PT_Phaenotyp_post,
	OBJECT_PT_Phaenotyp_reset
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

		# only run if quad is available
		quads_available = data.get("quads")
		if quads_available:
			quads = data["quads"]
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
	
	# handle lists in panel
	# based on code by sinestesia and support by Gorgious
	# check out this pages for explanation:
	# https://sinestesia.co/blog/tutorials/using-uilists-in-blender/
	# https://blenderartists.org/t/create-and-handle-multiple-uilists-pass-argument/1508288/7

	bpy.utils.register_class(PHAENOTYP_list_item)
	bpy.utils.register_class(PHAENOTYP_UL_List)
	bpy.utils.register_class(LIST_OT_new_item)
	bpy.utils.register_class(LIST_OT_delete_item)
	bpy.utils.register_class(LIST_OT_move_item)
	
	# multiple lists
	bpy.types.Scene.phaenotyp_fh_w = CollectionProperty(type = PHAENOTYP_list_item)
	bpy.types.Scene.phaenotyp_fh_d = CollectionProperty(type = PHAENOTYP_list_item)
	bpy.types.Scene.phaenotyp_fh_h = CollectionProperty(type = PHAENOTYP_list_item)
	
	# multiple indices
	bpy.types.Scene.phaenotyp_fh_w_index = IntProperty(name = "Index for phaenotyp_lists", default = 0)
	bpy.types.Scene.phaenotyp_fh_d_index = IntProperty(name = "Index for phaenotyp_lists", default = 0)
	bpy.types.Scene.phaenotyp_fh_h_index = IntProperty(name = "Index for phaenotyp_lists", default = 0)
	
	# for jobs
	bpy.utils.register_class(phaenotyp_jobs)
	
	# for webinterface
	bpy.utils.register_class(phaenotyp_webinterface)

	# terminal
	bpy.types.SpaceView3D.draw_handler_add(phaenotyp_terminal, (None, None), 'WINDOW', 'POST_PIXEL')
	
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
	
	# handle lists in panel
	# based on code by sinestesia and support by Gorgious
	# check out this pages for explanation:
	# https://sinestesia.co/blog/tutorials/using-uilists-in-blender/
	# https://blenderartists.org/t/create-and-handle-multiple-uilists-pass-argument/1508288/7
	
	del bpy.types.Scene.phaenotyp_fh_w
	del bpy.types.Scene.phaenotyp_fh_d
	del bpy.types.Scene.phaenotyp_fh_h
	
	del bpy.types.Scene.phaenotyp_fh_w_index
	del bpy.types.Scene.phaenotyp_fh_d_index
	del bpy.types.Scene.phaenotyp_fh_h_index
	
	bpy.utils.unregister_class(PHAENOTYP_list_item)
	bpy.utils.unregister_class(PHAENOTYP_UL_List)
	bpy.utils.unregister_class(LIST_OT_new_item)
	bpy.utils.unregister_class(LIST_OT_delete_item)
	bpy.utils.unregister_class(LIST_OT_move_item)
	
	# for jobs
	bpy.utils.unregister_class(phaenotyp_jobs)
	
	# for webinterface
	bpy.utils.unregister_class(phaenotyp_webinterface)
	
if __name__ == "__main__":
	'''
	Run mainloop and register all blender specific stuff.
	'''
	register()
