import bpy
from phaenotyp import material

class state:
	'''
	Shows if a topic is defined allready
	'''
	structure = False
	calculation_type = False
	supports = False
	members = False
	file = False

class grayed_out:
	'''
	Used to gray out boxes, that should not be modified
	and can not be hidden from within the function
	'''
	scipy = False
	supports = False
	members = False
	laods = False

def structure(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	# create box
	box_structure = layout.box()

	# check if phaenotyp created data allready
	state_temp = True

	if not data:
		state_temp = False

	else:
		structure = data.get("structure")

		# is the obj state? Maybe someone deleted the structure after calc ...
		if not structure:
			state_temp = False

		else:
			# Phaenotyp started, but no structure state by user
			if structure == None:
				state_temp = False

	# user needs to define a structure
	if not state_temp:
		box_structure.label(text="Structure:")
		box_structure.operator("wm.set_structure", text="Set")

	# user state a structure
	else:
		obj = data["structure"]
		box_structure.label(text = obj.name_full + " is state as structure.")

		state.structure = True
		grayed_out.structure = True

		# disable box
		box_structure.enabled = False

def scipy(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.structure:
		# check or uncheck scipy if available
		if data["scipy_available"]:
			box_scipy = layout.box()
			box_scipy.label(text = "Sparse matrix:")
			box_scipy.prop(phaenotyp, "use_scipy", text="Use scipy")

		# disable box
		if grayed_out.scipy:
			box_scipy.enabled = False

def calculation_type(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.structure:
		box_calculation_type = layout.box()
		box_calculation_type.label(text = "Calculation type:")
		box_calculation_type.prop(phaenotyp, "calculation_type", text="")

		calculation_type = phaenotyp.calculation_type

		if state.calculation_type == False:
			box_calculation_type.enabled = False

def supports(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.structure:
		# define support
		box_supports = layout.box()
		box_supports.label(text="Support:")

		# show all types if pynite is used
		if calculation_type not in ["geometrical", "force_distribution"]:
			col = box_supports.column()
			split = col.split()
			split.prop(phaenotyp, "loc_x", text="loc x")
			split.prop(phaenotyp, "rot_x", text="rot x")

			col = box_supports.column()
			split = col.split()
			split.prop(phaenotyp, "loc_y", text="loc y")
			split.prop(phaenotyp, "rot_y", text="rot y")

			col = box_supports.column()
			split = col.split()
			split.prop(phaenotyp, "loc_z", text="loc z")
			split.prop(phaenotyp, "rot_z", text="rot z")

		box_supports.operator("wm.set_support", text="Set")

		if len(data["supports"]) > 0:
			box_supports.label(text = str(len(data["supports"])) + " vertices state as support.")
			state.supports = True

		# disable box
		if grayed_out.supports:
			box_supports.enabled = False

def members(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.supports:
		# define material and geometry
		box_members = layout.box()
		box_members.label(text="Members:")

		box_members.prop(phaenotyp, "Do", text="Diameter outside")
		box_members.prop(phaenotyp, "Di", text="Diameter inside")

		# current setting passed from gui
		# (because a property can not be set in gui)
		material.current["Do"] = phaenotyp.Do * 0.1
		material.current["Di"] = phaenotyp.Di * 0.1

		box_members.prop(phaenotyp, "material", text="")
		if phaenotyp.material == "custom":
			box_members.prop(phaenotyp, "E", text="Modulus of elasticity")
			box_members.prop(phaenotyp, "G", text="Shear modulus")
			box_members.prop(phaenotyp, "d", text="Density")

			box_members.prop(phaenotyp, "acceptable_sigma", text="Acceptable sigma")
			box_members.prop(phaenotyp, "acceptable_shear", text="Acceptable shear")
			box_members.prop(phaenotyp, "acceptable_torsion", text="Acceptable torsion")
			box_members.prop(phaenotyp, "acceptable_sigmav", text="Acceptable sigmav")
			box_members.prop(phaenotyp, "ir", text="Ir")

			material.current["E"] = phaenotyp.E
			material.current["G"] = phaenotyp.G
			material.current["d"] = phaenotyp.d

			material.current["acceptable_sigma"] = phaenotyp.acceptable_sigma
			material.current["acceptable_shear"] = phaenotyp.acceptable_shear
			material.current["acceptable_torsion"] = phaenotyp.acceptable_torsion
			material.current["acceptable_sigmav"] = phaenotyp.acceptable_sigmav

		else:
			# pass input form library to data
			for mat in material.library:
				if phaenotyp.material == mat[0]: # select correct material
					# current setting passed from gui
					# (because a property can not be set in gui)
					material.current["E"] = mat[2]
					material.current["G"] = mat[3]
					material.current["d"] = mat[4]

					material.current["acceptable_sigma"] = mat[5]
					material.current["acceptable_shear"] = mat[6]
					material.current["acceptable_torsion"] = mat[7]
					material.current["acceptable_sigmav"] = mat[8]
					material.current["knick_model"] = mat[9]

			if calculation_type != "geometrical":
				box_members.label(text="E = " + str(material.current["E"]) + " kN/cm²")

			if calculation_type not in ["geometrical", "force_distribution"]:
				box_members.label(text="G = " + str(material.current["G"]) + " kN/cm²")

			box_members.label(text="d = " + str(material.current["d"]) + " g/cm3")

			if calculation_type != "geometrical":
				box_members.label(text="Acceptable sigma = " + str(material.current["acceptable_sigma"]))

			if calculation_type not in ["geometrical", "force_distribution"]:
				box_members.label(text="Acceptable shear = " + str(material.current["acceptable_shear"]))
				box_members.label(text="Acceptable torsion = " + str(material.current["acceptable_torsion"]))
				box_members.label(text="Acceptable sigmav = " + str(material.current["acceptable_sigmav"]))

		material.update() # calculate Iy, Iz, J, A, kg
		if calculation_type != "geometrical":
			box_members.label(text="Iy = " + str(round(material.current["Iy"], 4)) + " cm⁴")
			box_members.label(text="Iz = " + str(round(material.current["Iz"], 4)) + " cm⁴")

		if calculation_type not in ["geometrical", "force_distribution"]:
			box_members.label(text="J = " + str(round(material.current["J"], 4)) + " cm⁴")

		box_members.label(text="A = " + str(round(material.current["A"], 4)) + " cm²")
		box_members.label(text="kg = " + str(round(material.current["kg_A"], 4)) + " kg/m")

		box_members.operator("wm.set_member", text="Set")

		# if not all edges are state as member
		len_structure_edges = len(data["structure"].data.edges)
		len_members = len(data["members"])
		if len_members == 0:
			pass

		elif len_structure_edges != len_members:
			text = str(len_members) + " edges of " + str(len_structure_edges) + " set as members."
			box_members.label(text=text)

			# disable box for calculation_type when first edge is set
			# to avoid key error if user is changing the type
			state.calculation_type = False

		else:
			state.calculation_type = False

			text = str(len_members) + " edges set as members."
			box_members.label(text=text)

			state.members = True

		# disable box
		if grayed_out.members:
			box_members.enabled = False

def loads(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.members:
		box_loads = layout.box()
		box_loads.label(text="Loads:")
		if phaenotyp.calculation_type != "force_distribution":
			box_loads.prop(phaenotyp, "load_type", text="")
			if phaenotyp.load_type == "faces": # if faces
				box_loads.prop(phaenotyp, "load_normal", text="normal (like wind)")
				box_loads.prop(phaenotyp, "load_projected", text="projected (like snow)")
				box_loads.prop(phaenotyp, "load_area_z", text="area z (like weight of facade)")

			# if vertices or edges
			else:
				box_loads.prop(phaenotyp, "load_x", text="x")
				box_loads.prop(phaenotyp, "load_y", text="y")
				box_loads.prop(phaenotyp, "load_z", text="z")

		# with fd
		else:
			box_loads.prop(phaenotyp, "load_x", text="x")
			box_loads.prop(phaenotyp, "load_y", text="y")
			box_loads.prop(phaenotyp, "load_z", text="z")

		box_loads.operator("wm.set_load", text="Set")

		len_loads = len(data["loads_v"]) + len(data["loads_e"]) + len(data["loads_f"])
		if len_loads > 0:
			text = str(len_loads) + " loads defined."
			box_loads.label(text=text)

		# disable box
		if grayed_out.laods:
			box_loads.enabled = False

def file(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.members:
		if not bpy.data.is_saved:
			box_file = layout.box()
			box_file.label(text="Please save Blender-File first.")

		else:
			state.file = True

def mode(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.file and state.members:
		box_start = layout.box()
		box_start.label(text="Mode:")
		box_start.prop(phaenotyp, "mode", text="")

def transformation(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.file and state.members:
		box_assimilation = layout.box()
		box_assimilation.label(text="Assimilation:")
		box_assimilation.prop(phaenotyp, "assimilate_length", text="")
		box_assimilation.operator("wm.assimilate", text="Start")

		box_actuator = layout.box()
		box_actuator.label(text="Actuator:")
		box_actuator.prop(phaenotyp, "actuator_length", text="")
		box_actuator.operator("wm.actuator", text="Start")

		box_goal = layout.box()
		box_goal.label(text="Reach goal:")
		box_goal.operator("wm.reach_goal", text="Start")

def single_frame(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.file and state.members:
		if calculation_type != "geometrical":
			# analysis
			box_analysis = layout.box()
			box_analysis.label(text="Analysis:")
			box_analysis.operator("wm.calculate_single_frame", text="Start")

			# Optimization
			box_opt = layout.box()
			box_opt.label(text="Optimization:")

			result = data["done"].get(str(frame))
			if result:
				if calculation_type == "force_distribution":
					box_opt.operator("wm.optimize_approximate", text="Approximate")
				else:
					box_opt.operator("wm.optimize_simple", text="Simple")
					box_opt.operator("wm.optimize_utilization", text="Utilization")
					box_opt.operator("wm.optimize_complex", text="Complex")
			else:
				box_opt.label(text="Run single analysis first.")

			# Topology
			box_opt = layout.box()
			box_opt.label(text="Topology:")

			result = data["done"].get(str(frame))
			if result:
				box_opt.operator("wm.topolgy_decimate", text="Decimate")
			else:
				box_opt.label(text="Run single analysis first.")

		else:
			box_analysis = layout.box()
			box_analysis.label(text="Only genetic algorithm is available for geometrical mode.")

def animation(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.file and state.members:
		if calculation_type != "geometrical":
			box_optimization = layout.box()
			box_optimization.label(text="Optimization:")
			if phaenotyp.calculation_type != "geometrical":
				if calculation_type == "force_distribution":
					box_optimization.prop(phaenotyp, "optimization_fd", text="")
				else:
					box_optimization.prop(phaenotyp, "optimization_pn", text="")
				if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none":
					box_optimization.prop(phaenotyp, "animation_optimization_type", text="")
					box_optimization.prop(phaenotyp, "optimization_amount", text="Amount of sectional optimization")

			box_animation = layout.box()
			box_animation.label(text="Animation:")
			box_animation.operator("wm.calculate_animation", text="Start")

		else:
			box_optimization = layout.box()
			box_optimization.label(text="Only genetic algorithm is available for geometrical mode.")

def bruteforce(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.file and state.members:
		shape_key = data["structure"].data.shape_keys
		if not shape_key:
			box_ga = layout.box()
			box_ga.label(text="Bruteforce:")
			box_ga.label(text="Please set shape keys first.")
		else:
			if phaenotyp.calculation_type != "geometrical":
				box_optimization = layout.box()
				box_optimization.label(text="Optimization:")
				if calculation_type == "force_distribution":
					box_optimization.prop(phaenotyp, "optimization_fd", text="")
				else:
					box_optimization.prop(phaenotyp, "optimization_pn", text="")
				if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none":
					box_optimization.prop(phaenotyp, "optimization_amount", text="Amount of sectional optimization")

			# fitness headline
			box_fitness = layout.box()
			box_fitness.label(text="Fitness function:")

			# architectural fitness
			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_volume", text="Volume")
			split.prop(phaenotyp, "fitness_volume_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_area", text="Area")
			split.prop(phaenotyp, "fitness_area_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_kg", text="Kg")
			split.prop(phaenotyp, "fitness_kg_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_rise", text="Rise")
			split.prop(phaenotyp, "fitness_rise_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_span", text="Span")
			split.prop(phaenotyp, "fitness_span_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_cantilever", text="Cantilever")
			split.prop(phaenotyp, "fitness_cantilever_invert", text="Invert")

			# structural fitness
			if phaenotyp.calculation_type != "geometrical":
				box_fitness.prop(phaenotyp, "fitness_average_sigma", text="Sigma")
				if phaenotyp.calculation_type != "force_distribution":
					box_fitness.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy")

			box_shape_keys = layout.box()
			box_shape_keys.label(text="Shape keys:")
			for keyblock in shape_key.key_blocks:
				name = keyblock.name
				box_shape_keys.label(text=name)

			# check generation_size and elitism
			box_start = layout.box()
			box_start.label(text="Bruteforce:")
			box_start.operator("wm.bf_start", text="Start")

			if len(data["individuals"]) > 0 and not bpy.context.screen.is_animation_playing:
				box_select = layout.box()
				box_select.label(text="Select individual by fitness:")
				box_select.prop(phaenotyp, "ranking", text="Result sorted by fitness.")
				if phaenotyp.ranking >= len(data["individuals"]):
					text = "Only " + str(len(data["individuals"])) + " available."
					box_select.label(text=text)
				else:
					# show
					box_select.operator("wm.ranking", text="Generate")

				box_rendering = layout.box()
				box_rendering.label(text="Render sorted indiviuals:")
				box_rendering.operator("wm.render_animation", text="Generate")

def genetic_algorithm(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.file and state.members:
		shape_key = data["structure"].data.shape_keys
		if not shape_key:
			box_ga = layout.box()
			box_ga.label(text="Genetic algorithm:")
			box_ga.label(text="Please set shape keys first.")
		else:
			# Genetic Mutation:
			box_ga = layout.box()
			box_ga.label(text="Mutation:")
			box_ga.prop(phaenotyp, "mate_type", text="Type of mating")
			box_ga.prop(phaenotyp, "generation_size", text="Size of generation for GA")
			box_ga.prop(phaenotyp, "elitism", text="Size of elitism for GA")
			box_ga.prop(phaenotyp, "generation_amount", text="Amount of generations")

			if phaenotyp.calculation_type != "geometrical":
				box_optimization = layout.box()
				box_optimization.label(text="Optimization:")
				if calculation_type == "force_distribution":
					box_optimization.prop(phaenotyp, "optimization_fd", text="")
				else:
					box_optimization.prop(phaenotyp, "optimization_pn", text="")
				if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none":
					box_optimization.prop(phaenotyp, "optimization_amount", text="Amount of sectional optimization")

			# fitness headline
			box_fitness = layout.box()
			box_fitness.label(text="Fitness function:")

			# architectural fitness
			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_volume", text="Volume")
			split.prop(phaenotyp, "fitness_volume_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_area", text="Area")
			split.prop(phaenotyp, "fitness_area_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_kg", text="Kg")
			split.prop(phaenotyp, "fitness_kg_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_rise", text="Rise")
			split.prop(phaenotyp, "fitness_rise_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_span", text="Span")
			split.prop(phaenotyp, "fitness_span_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_cantilever", text="Cantilever")
			split.prop(phaenotyp, "fitness_cantilever_invert", text="Invert")

			# structural fitness
			if phaenotyp.calculation_type != "geometrical":
				box_fitness.prop(phaenotyp, "fitness_average_sigma", text="Sigma")
				if phaenotyp.calculation_type != "force_distribution":
					box_fitness.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy")

			box_shape_keys = layout.box()
			box_shape_keys.label(text="Shape keys:")
			for keyblock in shape_key.key_blocks:
				name = keyblock.name
				box_shape_keys.label(text=name)

			# check generation_size and elitism
			box_start = layout.box()
			box_start.label(text="Genetic algorithm:")
			if phaenotyp.generation_size*0.5 > phaenotyp.elitism:
				box_start.operator("wm.ga_start", text="Start")
			else:
				box_start.label(text="Elitism should be smaller than 50% of generation size.")

			if len(data["individuals"]) > 0 and not bpy.context.screen.is_animation_playing:
				box_select = layout.box()
				box_select.label(text="Select individual by fitness:")
				box_select.prop(phaenotyp, "ranking", text="Result sorted by fitness.")
				if phaenotyp.ranking >= len(data["individuals"]):
					text = "Only " + str(len(data["individuals"])) + " available."
					box_select.label(text=text)
				else:
					# show
					box_select.operator("wm.ranking", text="Generate")

				box_rendering = layout.box()
				box_rendering.label(text="Render sorted indiviuals:")
				box_rendering.operator("wm.render_animation", text="Generate")

def gradient_descent(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if state.file and state.members:
		shape_key = data["structure"].data.shape_keys
		if not shape_key:
			box_gd = layout.box()
			box_gd.label(text="Gradient descent:")
			box_gd.label(text="Please set shape keys first.")
		else:
			# Genetic Mutation:
			box_gd = layout.box()
			box_gd.label(text="Learing:")
			box_gd.prop(phaenotyp, "gd_delta", text="Delta")
			box_gd.prop(phaenotyp, "gd_learning_rate", text="Learning rate")
			box_gd.prop(phaenotyp, "gd_abort", text="Abort")
			box_gd.prop(phaenotyp, "gd_max_iteration", text="Max iteration")
			box_gd.operator("wm.gd_start", text="Start")

			if phaenotyp.calculation_type != "geometrical":
				box_optimization = layout.box()
				box_optimization.label(text="Optimization:")
				if calculation_type == "force_distribution":
					box_optimization.prop(phaenotyp, "optimization_fd", text="")
				else:
					box_optimization.prop(phaenotyp, "optimization_pn", text="")
				if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none":
					box_optimization.prop(phaenotyp, "optimization_amount", text="Amount of sectional optimization")

			# fitness headline
			box_fitness = layout.box()
			box_fitness.label(text="Fitness function:")

			# architectural fitness
			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_volume", text="Volume")
			split.prop(phaenotyp, "fitness_volume_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_area", text="Area")
			split.prop(phaenotyp, "fitness_area_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_kg", text="Kg")
			split.prop(phaenotyp, "fitness_kg_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_rise", text="Rise")
			split.prop(phaenotyp, "fitness_rise_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_span", text="Span")
			split.prop(phaenotyp, "fitness_span_invert", text="Invert")

			col = box_fitness.column()
			split = col.split()
			split.prop(phaenotyp, "fitness_cantilever", text="Cantilever")
			split.prop(phaenotyp, "fitness_cantilever_invert", text="Invert")

			# structural fitness
			if phaenotyp.calculation_type != "geometrical":
				box_fitness.prop(phaenotyp, "fitness_average_sigma", text="Sigma")
				if phaenotyp.calculation_type != "force_distribution":
					box_fitness.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy")

			box_shape_keys = layout.box()
			box_shape_keys.label(text="Shape keys:")
			for keyblock in shape_key.key_blocks:
				name = keyblock.name
				box_shape_keys.label(text=name)

def visualization(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	try:
		box_scipy.enabled = False
	except:
		pass

	if phaenotyp.calculation_type != "geometrical":
		box_viz = layout.box()
		box_viz.label(text="Vizualisation:")
		if calculation_type == "force_distribution":
			box_viz.prop(phaenotyp, "forces_fd", text="Force")
		else:
			box_viz.prop(phaenotyp, "forces_pn", text="Force")

		# sliders to scale forces and deflection
		box_viz.prop(phaenotyp, "viz_scale", text="scale", slider=True)
		if phaenotyp.calculation_type != "force_distribution":
			box_viz.prop(phaenotyp, "viz_deflection", text="deflected / original", slider=True)

def text(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	box_text = layout.box()
	box_text.label(text="Result:")
	box_text.label(text="Volume: "+str(round(data["frames"][str(frame)]["volume"],3)) + " m³")
	box_text.label(text="Area: "+str(round(data["frames"][str(frame)]["area"],3)) + " m²")
	box_text.label(text="Length: "+str(round(data["frames"][str(frame)]["length"],3)) + " m")
	box_text.label(text="Kg: "+str(round(data["frames"][str(frame)]["kg"],3)) + " kg")
	box_text.label(text="Rise: "+str(round(data["frames"][str(frame)]["rise"],3)) + " m")
	box_text.label(text="Span: "+str(round(data["frames"][str(frame)]["span"],3)) + " m")
	box_text.label(text="Cantilever: "+str(round(data["frames"][str(frame)]["cantilever"],3)) + " m")

def info(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if phaenotyp.calculation_type != "geometrical":
		box_info = layout.box()
		box_info.label(text="Info:")
		selected_objects = bpy.context.selected_objects
		if len(selected_objects) > 1:
			box_info.label(text="Please select the vizualisation object only - too many objects")

		elif len(selected_objects) == 0:
			box_info.label(text="Please select the vizualisation object - no object selected")

		elif selected_objects[0].name_full != "<Phaenotyp>member":
			box_info.label(text="Please select the vizualisation object - wrong object selected")

		else:
			if context.active_object.mode == 'EDIT':
				vert_sel = bpy.context.active_object.data.total_vert_sel
				if vert_sel != 1:
					box_info.label(text="Select one vertex only")

				else:
					box_info.operator("wm.text", text="Generate")
					if len(data["texts"]) > 0:
						for text in data["texts"]:
							box_info.label(text=text)
			else:
				box_info.label(text="Switch to edit-mode")

def selection(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if phaenotyp.calculation_type != "geometrical":
		box_selection = layout.box()
		box_selection.label(text="Selection:")
		if phaenotyp.calculation_type == "force_distribution":
			box_selection.prop(phaenotyp, "selection_key_fd", text="")
		else:
			box_selection.prop(phaenotyp, "selection_key_pn", text="Key:")
		box_selection.prop(phaenotyp, "selection_compare", text="Compare:")
		box_selection.prop(phaenotyp, "selection_value", text="Value:")
		box_selection.prop(phaenotyp, "selection_threshold", text="Threshold:")
		box_selection.operator("wm.selection", text="Start")

def report(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	box_report = layout.box()
	box_report.label(text="Report:")

	if phaenotyp.calculation_type != "geometrical":
		if phaenotyp.calculation_type != "force_distribution":
			box_report.operator("wm.report_members", text="members")
			box_report.operator("wm.report_frames", text="frames")
		else:
			box_report.operator("wm.report_combined", text="combined")
	else:
		box_report.label(text="No report for members, frames or combined available in geometrical mode.")

	# if ga
	environment = data.get("environment")
	if environment:
		ga_available = environment.get("generations")
		if ga_available:
			box_report.operator("wm.report_chromosomes", text="chromosomes")
			box_report.operator("wm.report_tree", text="tree")

def reset(layout):
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	# reset data
	box_reset = layout.box()
	box_reset.operator("wm.reset", text="Reset")
