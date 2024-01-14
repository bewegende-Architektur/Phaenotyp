import bpy
from phaenotyp import material

def pre(layout):
	'''
	Panel for creating and preparing structure.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	# create box
	box_pre = layout.box()
	
	# convert
	box_pre.label(text="Convert:")
	box_pre.operator("wm.curve_to_mesh_straight", text="Curves to mesh straight")
	box_pre.operator("wm.curve_to_mesh_curved", text="Curves to mesh curved")
	box_pre.operator("wm.meta_to_mesh", text="Meta to mesh")

	# from hull
	#box_pre.label(text="From hull:")
	'''
	grid or spline
	Set
	w = 3
	d = 7
	h = 3
	o_x = 3
	o_y = 7
	o_z = 3
	Start
	'''
		
	# prepare
	box_pre.label(text="Prepare:")
	box_pre.operator("wm.mesh_to_quads_simple", text="Mesh to quads simple")
	box_pre.operator("wm.mesh_to_quads_complex", text="Mesh to quads complex")
	box_pre.operator("wm.automerge", text="Automerge")
	box_pre.operator("wm.union", text="Union")
	box_pre.operator("wm.simplify_edges", text="Simplify edges")
	
	# gray out, if a structure is set allready
	if data:
		structure = data.get("structure")
		if structure:
			box_pre.enabled = False
		
def structure(layout):
	'''
	Panel for structure.
	:param layout: Passed layout of phaenotyp panel.
	'''
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

		data["panel_state"]["structure"] = True
		data["panel_grayed"]["structure"] = True

		# disable box
		box_structure.enabled = False

def scipy(layout):
	'''
	Panel for scipy.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	
	if data:
		if data["panel_state"]["structure"]:
			# check or uncheck scipy if available
			if data["scipy_available"]:
				box_scipy = layout.box()
				box_scipy.label(text = "Sparse matrix:")
				box_scipy.prop(phaenotyp, "use_scipy", text="Use scipy")

				# disable box
				if data["panel_grayed"]["scipy"]:
					box_scipy.enabled = False

def calculation_type(layout):
	'''
	Panel for calculation type.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if data:
		if data["panel_state"]["structure"]:
			box_calculation_type = layout.box()
			box_calculation_type.label(text = "Calculation type:")
			box_calculation_type.prop(phaenotyp, "calculation_type", text="")

			calculation_type = phaenotyp.calculation_type
			type_of_joints = phaenotyp.type_of_joints
			
			# for pynite
			if calculation_type not in ["geometrical", "force_distribution", "-"]:
				box_calculation_type.prop(phaenotyp, "type_of_joints", text="")
			
				# gray out panel if defined
				if calculation_type != "-" and type_of_joints != "-":
					data["panel_state"]["calculation_type"] = True
					data["panel_grayed"]["calculation_type"] = True
					box_calculation_type.enabled = False
			
			# for others
			else:
				# gray out panel if defined
				if calculation_type != "-":
					data["panel_state"]["calculation_type"] = True
					data["panel_grayed"]["calculation_type"] = True
					box_calculation_type.enabled = False


def supports(layout):
	'''
	Panel for supports.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["structure"] and data["panel_state"]["calculation_type"]:
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
				data["panel_state"]["supports"] = True

			# disable box
			if data["panel_grayed"]["supports"]:
				box_supports.enabled = False

def members(layout):
	'''
	Panel for members.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["supports"]:
			# define material and geometry
			box_members = layout.box()
			box_members.label(text="Members:")

			box_members.prop(phaenotyp, "Do", text="Diameter outside")
			box_members.prop(phaenotyp, "Di", text="Diameter inside")
			if calculation_type != "force_distribution":
				box_members.prop(phaenotyp, "buckling_resolution", text="Buckling resolution")

			# current setting passed from gui
			# (because a property can not be set in gui)
			material.current["Do"] = phaenotyp.Do
			material.current["Di"] = phaenotyp.Di
			
			if calculation_type != "force_distribution":
				box_members.prop(phaenotyp, "member_type", text="")

			box_members.prop(phaenotyp, "material", text="")
			if phaenotyp.material == "custom":
				box_members.prop(phaenotyp, "E", text="Modulus of elasticity kN/cm²")
				box_members.prop(phaenotyp, "G", text="Shear modulus kN/cm²")
				box_members.prop(phaenotyp, "rho", text="Density g/cm3")

				box_members.prop(phaenotyp, "acceptable_sigma", text="Acceptable sigma kN/cm²")
				box_members.prop(phaenotyp, "acceptable_shear", text="Acceptable shear kN/cm²")
				box_members.prop(phaenotyp, "acceptable_torsion", text="Acceptable torsion kN/cm²")
				box_members.prop(phaenotyp, "acceptable_sigmav", text="Acceptable sigmav kN/cm²")
				box_members.prop(phaenotyp, "kn_custom", text="kn")
				
				material.current["material_name"] = "custom"
				material.current["E"] = phaenotyp.E
				material.current["G"] = phaenotyp.G
				material.current["rho"] = phaenotyp.rho

				material.current["acceptable_sigma"] = phaenotyp.acceptable_sigma
				material.current["acceptable_shear"] = phaenotyp.acceptable_shear
				material.current["acceptable_torsion"] = phaenotyp.acceptable_torsion
				material.current["acceptable_sigmav"] = phaenotyp.acceptable_sigmav
					
				# convert custom kn from string to int
				kn_custom = []
				kn = phaenotyp.kn_custom
				kn = kn.split(",")
				
				for entry in kn:
					kn_custom.append(float(entry))
				
				material.current["knick_model"] = kn_custom

			else:
				# pass input form library to data
				for mat in material.library:
					if phaenotyp.material == mat[0]: # select correct material
						# current setting passed from gui
						# (because a property can not be set in gui)
						
						material.current["material_name"] = mat[0]					
						material.current["E"] = mat[2]
						material.current["G"] = mat[3]
						material.current["rho"] = mat[4]

						material.current["acceptable_sigma"] = mat[5]
						material.current["acceptable_shear"] = mat[6]
						material.current["acceptable_torsion"] = mat[7]
						material.current["acceptable_sigmav"] = mat[8]
						material.current["knick_model"] = mat[9]

				if calculation_type != "geometrical":
					box_members.label(text="E = " + str(material.current["E"]) + " kN/cm²")

				if calculation_type not in ["geometrical", "force_distribution"]:
					box_members.label(text="G = " + str(material.current["G"]) + " kN/cm²")

				box_members.label(text="rho = " + str(material.current["rho"]) + " g/cm3")

				if calculation_type != "geometrical":
					box_members.label(text="Acceptable sigma = " + str(material.current["acceptable_sigma"]) + " kN/cm²")

				if calculation_type not in ["geometrical", "force_distribution"]:
					box_members.label(text="Acceptable shear = " + str(material.current["acceptable_shear"]) + " kN/cm²")
					box_members.label(text="Acceptable torsion = " + str(material.current["acceptable_torsion"]) + " kN/cm²")
					box_members.label(text="Acceptable sigmav = " + str(material.current["acceptable_sigmav"]) + " kN/cm²")

			material.update() # calculate Iy, Iz, J, A, weight
			if calculation_type != "geometrical":
				box_members.label(text="Iy = " + str(round(material.current["Iy"], 4)) + " cm⁴")
				box_members.label(text="Iz = " + str(round(material.current["Iz"], 4)) + " cm⁴")

			if calculation_type not in ["geometrical", "force_distribution"]:
				box_members.label(text="J = " + str(round(material.current["J"], 4)) + " cm⁴")

			box_members.label(text="A = " + str(round(material.current["A"], 4)) + " cm²")
			box_members.label(text="Weight = " + str(round(material.current["weight_A"], 4)) + " kg/m")
			
			if calculation_type != "force_distribution":
				box_members.prop(phaenotyp, "psf_members", text="Partial safety factor")
				
			box_members.operator("wm.set_member", text="Set")

			# display amount of defined edges
			amount = len(data["members"])
			if amount > 0:
				text = str(amount) + " edges set as members."
				box_members.label(text=text)
			
				data["panel_state"]["members"] = True

			# disable box
			if data["panel_grayed"]["members"]:
				box_members.enabled = False

def quads(layout):
	'''
	Panel for quads.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["supports"]:
			# define material and geometry
			if calculation_type != "force_distribution":
				box_quads = layout.box()
				box_quads.label(text="Quads:")
				
				box_quads.prop(phaenotyp, "thickness", text="Thickness")
				
				box_quads.prop(phaenotyp, "material_quads", text="")
				
				if phaenotyp.material_quads == "custom":
					box_quads.prop(phaenotyp, "E_quads", text="Modulus of elasticity kN/cm²")
					box_quads.prop(phaenotyp, "G_quads", text="Modulus of elasticity kN/cm²")
					box_quads.prop(phaenotyp, "nu_quads", text="Poisson's ratio")
					box_quads.prop(phaenotyp, "rho_quads", text="Density g/cm3")
					
					material.current_quads["E"] = phaenotyp.E_quads
					material.current_quads["G"] = phaenotyp.G_quads
					material.current_quads["nu"] = phaenotyp.nu_quads
					material.current_quads["rho"] = phaenotyp.rho_quads
					
					quad["acceptable_sigma"] = phaenotyp.acceptable_sigma_quads
					quad["acceptable_shear"] = phaenotyp.acceptable_shear_quads
					quad["acceptable_sigmav"] = phaenotyp.acceptable_sigmav_quads
					quad["knick_model"] = phaenotyp.knick_model_quads
					
					box_quads.label(text="Weight = " + str(round(phaenotyp.rho_quads*phaenotyp.thickness*10, 4)) + " kg/m²")

				else:
					# pass input form library to data
					for mat in material.library_quads:
						if phaenotyp.material_quads == mat[0]: # select correct material
							# current setting passed from gui
							# (because a property can not be set in gui)
							
							E = mat[2]
							G = mat[3]
							nu = mat[4]
							rho = mat[5]
							
							acceptable_sigma = mat[6]
							acceptable_shear = mat[7]
							acceptable_sigmav = mat[8]
							knick_model = mat[9]
							
							material.current_quads["E"] = E
							material.current_quads["G"] = G
							material.current_quads["nu"] = nu
							material.current_quads["rho"] = rho
							
							material.current_quads["acceptable_sigma"] = acceptable_sigma
							material.current_quads["acceptable_shear"] = acceptable_shear
							material.current_quads["acceptable_sigmav"] = acceptable_sigmav
							material.current_quads["knick_model"] = knick_model
							
							box_quads.label(text="E = " + str(E) + " kN/cm²")
							box_quads.label(text="G = " + str(G) + " kN/cm²")
							box_quads.label(text="nu = " + str(nu))
							box_quads.label(text="rho = " + str(rho) + " g/cm³")
							
							box_quads.label(text="acceptable_sigma = " + str(acceptable_sigma) + " kN/cm³")
							box_quads.label(text="acceptable_shear = " + str(acceptable_shear) + " kN/cm³")
							box_quads.label(text="acceptable_sigmav = " + str(acceptable_sigmav) + " kN/cm³")
							box_quads.label(text="knick_model = " + str(knick_model))
					
					box_quads.label(text="Weight = " + str(round(rho*phaenotyp.thickness*10, 4)) + " kg/m²")
				
				box_quads.prop(phaenotyp, "psf_quads", text="Partial safety factor")
				box_quads.operator("wm.set_quad", text="Set")

				# display amount of defined faces
				amount = len(data["quads"])
				if amount > 0:
					text = str(amount) + " faces set as quads."
					box_quads.label(text=text)
				
					data["panel_state"]["quads"] = True

				# disable box
				if data["panel_grayed"]["quads"]:
					box_quads.enabled = False

def loads(layout):
	'''
	Panel for loads.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["members"] or data["panel_state"]["quads"]:
			box_loads = layout.box()
			box_loads.label(text="Loads:")
			box_loads.prop(phaenotyp, "load_type", text="")

			if phaenotyp.load_type == "vertices":
				box_loads.prop(phaenotyp, "load_FX", text="Axial x")
				box_loads.prop(phaenotyp, "load_FY", text="Axial y")
				box_loads.prop(phaenotyp, "load_FZ", text="Axial z")
			
				if calculation_type not in ["geometrical", "force_distribution"]:
					box_loads.prop(phaenotyp, "load_MX", text="Moment x")
					box_loads.prop(phaenotyp, "load_MY", text="Moment y")
					box_loads.prop(phaenotyp, "load_MZ", text="Moment z")
			
			if phaenotyp.load_type == "edges":
				box_loads.prop(phaenotyp, "load_FX", text="Axial x")
				box_loads.prop(phaenotyp, "load_FY", text="Axial y")
				box_loads.prop(phaenotyp, "load_FZ", text="Axial z")

				if calculation_type not in ["geometrical", "force_distribution"]:
					box_loads.prop(phaenotyp, "load_Fx", text="Axial x local")
					box_loads.prop(phaenotyp, "load_Fy", text="Axial y local")
					box_loads.prop(phaenotyp, "load_Fz", text="Axial z local")
					
			if phaenotyp.load_type == "faces":
				box_loads.prop(phaenotyp, "load_normal", text="Normal (Like wind)")
				box_loads.prop(phaenotyp, "load_projected", text="Projected (Like snow)")
				box_loads.prop(phaenotyp, "load_area_z", text="Area z (Like weight of facade)")
			
			if calculation_type != "force_distribution":
				box_loads.prop(phaenotyp, "psf_loads", text="Partial safety factor")
			
			box_loads.operator("wm.set_load", text="Set")

			len_loads = len(data["loads_v"]) + len(data["loads_e"]) + len(data["loads_f"])
			if len_loads > 0:
				text = str(len_loads) + " loads defined."
				box_loads.label(text=text)

			# disable box
			if data["panel_grayed"]["loads"]:
				box_loads.enabled = False

def file(layout):
	'''
	Panel for file.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if data:
		if data["panel_state"]["members"] or data["panel_state"]["quads"]:
			if not bpy.data.is_saved:
				box_file = layout.box()
				box_file.label(text="Please save Blender-File first.")

			else:
				data["panel_state"]["file"] = True

def mode(layout):
	'''
	Panel for mode.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if data:
		if data["panel_state"]["file"]:
			if data["panel_state"]["members"] or data["panel_state"]["quads"]:
				box_start = layout.box()
				box_start.label(text="Mode:")
				box_start.prop(phaenotyp, "mode", text="")

def transformation(layout):
	'''
	Panel for transformation.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	if data:
		if data["panel_state"]["file"]:
			if data["panel_state"]["members"] or data["panel_state"]["quads"]:
				box_assimilation = layout.box()
				box_assimilation.label(text="Assimilation:")
				box_assimilation.prop(phaenotyp, "assimilate_length", text="Length")
				box_assimilation.prop(phaenotyp, "assimilate_strength", text="Strength")
				box_assimilation.prop(phaenotyp, "assimilate_iterations", text="Iterations")
				box_assimilation.operator("wm.assimilate", text="Start")

				box_actuator = layout.box()
				box_actuator.label(text="Actuator:")
				box_actuator.prop(phaenotyp, "actuator_length", text="Length")
				box_actuator.prop(phaenotyp, "actuator_strength", text="Strength")
				box_actuator.prop(phaenotyp, "actuator_iterations", text="Iterations")
				box_actuator.operator("wm.actuator", text="Start")

				box_goal = layout.box()
				box_goal.label(text="Reach goal:")
				box_goal.prop(phaenotyp, "goal_strength", text="Strength")
				box_goal.prop(phaenotyp, "goal_iterations", text="Iterations")
				box_goal.operator("wm.reach_goal", text="Start")
				
				box_wool = layout.box()
				box_wool.label(text="Wool threads:")
				box_wool.prop(phaenotyp, "gravity_strength", text="Gravity strength")
				box_wool.prop(phaenotyp, "link_strength", text="Link strength")
				box_wool.prop(phaenotyp, "bonding_threshold", text="Bonding threshold")
				box_wool.prop(phaenotyp, "bonding_strength", text="Bonding strength")
				box_wool.prop(phaenotyp, "wool_iterations", text="Iterations")		
				box_wool.operator("wm.wool_threads", text="Start")

				box_crown = layout.box()
				box_crown.label(text="Crown shyness:")
				box_crown.prop(phaenotyp, "shyness_threshold", text="Shyness threshold")
				box_crown.prop(phaenotyp, "shyness_strength", text="Shyness strength")
				box_crown.prop(phaenotyp, "growth_strength", text="Growth strength")
				box_crown.prop(phaenotyp, "crown_iterations", text="Iterations")		
				box_crown.operator("wm.crown_shyness", text="Start")
				
				box_animation = layout.box()
				box_animation.label(text="Animation:")
				box_animation.prop(phaenotyp, "assimilate_update", text="Assimilate")
				box_animation.prop(phaenotyp, "actuator_update", text="Actuator")
				box_animation.prop(phaenotyp, "goal_update", text="Goal")
				box_animation.prop(phaenotyp, "wool_update", text="Wool threads")
				box_animation.prop(phaenotyp, "crown_update", text="Crown shyness")
				if bpy.context.screen.is_animation_playing:
					box_animation.operator("screen.animation_play", text="Stop")
				else:
					box_animation.operator("screen.animation_play", text="Start")

				box_state = layout.box()
				box_state.label(text="State:")
				stored = data["process"].get("stored")
				if stored:
					box_state.operator("wm.store_co", text="Overwrite")
					box_state.operator("wm.restore_co", text="Restore")
				else:
					box_state.operator("wm.store_co", text="Store")
			
def single_frame(layout):
	'''
	Panel for single frame.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["file"]:
			if data["panel_state"]["members"] or data["panel_state"]["quads"]:
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
							box_opt.operator("wm.optimize_approximate", text="Members approximate")
						else:
							box_opt.operator("wm.optimize_simple", text="Members simple")
							box_opt.operator("wm.optimize_utilization", text="Members utilization")
							box_opt.operator("wm.optimize_complex", text="Members complex")
							box_opt.operator("wm.optimize_quads_approximate", text="Quads approximate")
							box_opt.operator("wm.optimize_quads_utilization", text="Quads utilization")
					else:
						box_opt.label(text="Run single analysis first.")

					# Topology
					box_top = layout.box()
					box_top.label(text="Topology:")
					
					if len(data["members"]) > 0:
						result = data["done"].get(str(frame))
						if result:
							box_top.operator("wm.topolgy_decimate", text="Decimate")
							decimate_group = data["structure"].vertex_groups.get("<Phaenotyp>decimate")
							if decimate_group:
								box_top.label(text="Ajust the ratio of decimate, apply modifier and reset Phänotyp aferwards to restart")
						else:
							box_top.label(text="Run single analysis first.")
					else:
						box_top.label(text="Decimate topology only works with members.")	
					

				else:
					box_analysis = layout.box()
					box_analysis.label(text="Only genetic algorithm is available for geometrical mode.")

def animation(layout):
	'''
	Panel for animation.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["file"]:
			if data["panel_state"]["members"] or data["panel_state"]["quads"]:
				if calculation_type != "geometrical":
					box_optimization = layout.box()
					box_optimization.label(text="Optimization:")
					if phaenotyp.calculation_type != "geometrical":
						if calculation_type == "force_distribution":
							box_optimization.prop(phaenotyp, "optimization_fd", text="")
						else:
							col = box_optimization.column()
							split = col.split()
							split.label(text="Members:")
							split.prop(phaenotyp, "optimization_pn", text="")
							col = box_optimization.column()
							split = col.split()
							split.label(text="Quads:")
							split.prop(phaenotyp, "optimization_quads", text="")
						if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
							box_optimization.prop(phaenotyp, "animation_optimization_type", text="")
							box_optimization.prop(phaenotyp, "optimization_amount", text="Amount of sectional optimization")

					box_animation = layout.box()
					box_animation.label(text="Animation:")
					box_animation.operator("wm.calculate_animation", text="Start")

				else:
					box_optimization = layout.box()
					box_optimization.label(text="Only genetic algorithm is available for geometrical mode.")

def bruteforce(layout):
	'''
	Panel for bruteforce.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["file"]:
			if data["panel_state"]["members"] or data["panel_state"]["quads"]:
				shape_key = data["structure"].data.shape_keys
				if not shape_key:
					box_ga = layout.box()
					box_ga.label(text="Bruteforce:")
					box_ga.label(text="Please set shape keys first.")
				else:
					if calculation_type != "geometrical":
						box_optimization = layout.box()
						box_optimization.label(text="Optimization:")
						if phaenotyp.calculation_type != "geometrical":
							if calculation_type == "force_distribution":
								box_optimization.prop(phaenotyp, "optimization_fd", text="")
							else:
								col = box_optimization.column()
								split = col.split()
								split.label(text="Members:")
								split.prop(phaenotyp, "optimization_pn", text="")
								col = box_optimization.column()
								split = col.split()
								split.label(text="Quads:")
								split.prop(phaenotyp, "optimization_quads", text="")
							if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
								box_optimization.prop(phaenotyp, "animation_optimization_type", text="")
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
					split.prop(phaenotyp, "fitness_weight", text="weight")
					split.prop(phaenotyp, "fitness_weight_invert", text="Invert")

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
						col = box_fitness.column()
						split = col.split()
						split.prop(phaenotyp, "fitness_deflection_members", text="Deflection members")
						split.prop(phaenotyp, "fitness_deflection_members_invert", text="Invert")
						
						if phaenotyp.calculation_type != "force_distribution":
							col = box_fitness.column()
							split = col.split()
							split.prop(phaenotyp, "fitness_deflection_quads", text="Deflection quads")
							split.prop(phaenotyp, "fitness_deflection_quads_invert", text="Invert")
												
						box_fitness.prop(phaenotyp, "fitness_average_sigma_members", text="Sigma members")
						
						if phaenotyp.calculation_type != "force_distribution":
							box_fitness.prop(phaenotyp, "fitness_average_sigmav_quads", text="Sigmav quads")
						
						if phaenotyp.calculation_type != "force_distribution":
							box_fitness.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy (members only)")

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
	'''
	Panel for genetic algorithm.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["file"]:
			if data["panel_state"]["members"] or data["panel_state"]["quads"]:
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

					if calculation_type != "geometrical":
						box_optimization = layout.box()
						box_optimization.label(text="Optimization:")
						if phaenotyp.calculation_type != "geometrical":
							if calculation_type == "force_distribution":
								box_optimization.prop(phaenotyp, "optimization_fd", text="")
							else:
								col = box_optimization.column()
								split = col.split()
								split.label(text="Members:")
								split.prop(phaenotyp, "optimization_pn", text="")
								col = box_optimization.column()
								split = col.split()
								split.label(text="Quads:")
								split.prop(phaenotyp, "optimization_quads", text="")
							if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
								box_optimization.prop(phaenotyp, "animation_optimization_type", text="")
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
					split.prop(phaenotyp, "fitness_weight", text="weight")
					split.prop(phaenotyp, "fitness_weight_invert", text="Invert")

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
						col = box_fitness.column()
						split = col.split()
						split.prop(phaenotyp, "fitness_deflection_members", text="Deflection members")
						split.prop(phaenotyp, "fitness_deflection_members_invert", text="Invert")
						
						if phaenotyp.calculation_type != "force_distribution":
							col = box_fitness.column()
							split = col.split()
							split.prop(phaenotyp, "fitness_deflection_quads", text="Deflection quads")
							split.prop(phaenotyp, "fitness_deflection_quads_invert", text="Invert")
												
						box_fitness.prop(phaenotyp, "fitness_average_sigma_members", text="Sigma members")
						
						if phaenotyp.calculation_type != "force_distribution":
							box_fitness.prop(phaenotyp, "fitness_average_sigmav_quads", text="Sigmav quads")
						
						if phaenotyp.calculation_type != "force_distribution":
							box_fitness.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy (members only)")

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
	'''
	Panel for gradient descent.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	calculation_type = phaenotyp.calculation_type

	if data:
		if data["panel_state"]["file"]:
			if data["panel_state"]["members"] or data["panel_state"]["quads"]:
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

					if calculation_type != "geometrical":
						box_optimization = layout.box()
						box_optimization.label(text="Optimization:")
						if phaenotyp.calculation_type != "geometrical":
							if calculation_type == "force_distribution":
								box_optimization.prop(phaenotyp, "optimization_fd", text="")
							else:
								col = box_optimization.column()
								split = col.split()
								split.label(text="Members:")
								split.prop(phaenotyp, "optimization_pn", text="")
								col = box_optimization.column()
								split = col.split()
								split.label(text="Quads:")
								split.prop(phaenotyp, "optimization_quads", text="")
							if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
								box_optimization.prop(phaenotyp, "animation_optimization_type", text="")
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
					split.prop(phaenotyp, "fitness_weight", text="weight")
					split.prop(phaenotyp, "fitness_weight_invert", text="Invert")

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
						col = box_fitness.column()
						split = col.split()
						split.prop(phaenotyp, "fitness_deflection_members", text="Deflection members")
						split.prop(phaenotyp, "fitness_deflection_members_invert", text="Invert")
						
						if phaenotyp.calculation_type != "force_distribution":
							col = box_fitness.column()
							split = col.split()
							split.prop(phaenotyp, "fitness_deflection_quads", text="Deflection quads")
							split.prop(phaenotyp, "fitness_deflection_quads_invert", text="Invert")
												
						box_fitness.prop(phaenotyp, "fitness_average_sigma_members", text="Sigma members")
						
						if phaenotyp.calculation_type != "force_distribution":
							box_fitness.prop(phaenotyp, "fitness_average_sigmav_quads", text="Sigmav quads")
						
						if phaenotyp.calculation_type != "force_distribution":
							box_fitness.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy (members only)")

					box_shape_keys = layout.box()
					box_shape_keys.label(text="Shape keys:")
					for keyblock in shape_key.key_blocks:
						name = keyblock.name
						box_shape_keys.label(text=name)
					
					box_gd_start = layout.box()
					box_gd_start.label(text="Genetic descent:")
					box_gd_start.operator("wm.gd_start", text="Start")

def visualization(layout):
	'''
	Panel for visualization.
	:param layout: Passed layout of phaenotyp panel.
	'''
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
		if phaenotyp.calculation_type == "force_distribution":
			box_viz.prop(phaenotyp, "forces_fd", text="Members")
		else:
			box_viz.prop(phaenotyp, "forces_pn", text="Members")
			box_viz.prop(phaenotyp, "forces_quads", text="Quads")

		# sliders to scale forces and deflection
		box_viz.prop(phaenotyp, "viz_scale", text="Scale force", slider=True)
		if phaenotyp.calculation_type != "force_distribution":
			box_viz.prop(phaenotyp, "viz_deflection", text="Deflected / original", slider=True)
		
		# stresslines
		quads = data.get("quads")
		if quads:
			box_viz.prop(phaenotyp, "viz_stressline_scale", text="Scale of stresslines", slider=True)

def text(layout):
	'''
	Panel for text.
	:param layout: Passed layout of phaenotyp panel.
	'''
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
	box_text.label(text="Weight: "+str(round(data["frames"][str(frame)]["weight"],3)) + " kg")
	box_text.label(text="Rise: "+str(round(data["frames"][str(frame)]["rise"],3)) + " m")
	box_text.label(text="Span: "+str(round(data["frames"][str(frame)]["span"],3)) + " m")
	box_text.label(text="Cantilever: "+str(round(data["frames"][str(frame)]["cantilever"],3)) + " m")

def info(layout):
	'''
	Panel for info.
	:param layout: Passed layout of phaenotyp panel.
	'''
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
			box_info.label(text="Please select one vizualisation object only - too many objects")

		elif len(selected_objects) == 0:
			box_info.label(text="Please select a vizualisation object - no object selected")

		elif selected_objects[0].name_full !=  "<Phaenotyp>members" and selected_objects[0].name_full !=  "<Phaenotyp>quads":
			box_info.label(text="Please select a vizualisation object - wrong object selected")
			
		else:
			if context.active_object.mode == 'EDIT':
				# selection for members
				if selected_objects[0].name_full ==  "<Phaenotyp>members":
					vert_sel = bpy.context.active_object.data.total_vert_sel
					if vert_sel != 1:
						box_info.label(text="Select one vertex only")

					else:
						box_info.operator("wm.text", text="Generate")
						if len(data["texts"]) > 0:
							for text in data["texts"]:
								box_info.label(text=text)
				
				# seleciton for quads
				if selected_objects[0].name_full !=  "<Phaenotyp>members":
					face_sel = bpy.context.active_object.data.total_face_sel
					if face_sel != 1:
						box_info.label(text="Select one face only")

					else:
						box_info.operator("wm.text", text="Generate")
						if len(data["texts"]) > 0:
							for text in data["texts"]:
								box_info.label(text=text)
								
			else:
				box_info.label(text="Switch to edit-mode")
				data["texts"] = []

def selection(layout):
	'''
	Panel for selection.
	:param layout: Passed layout of phaenotyp panel.
	'''
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
			box_selection.prop(phaenotyp, "selection_type", text="Type:")
			if phaenotyp.selection_type == "member":
				box_selection.prop(phaenotyp, "selection_key_pn", text="Key:")
			else:
				box_selection.prop(phaenotyp, "selection_key_quads", text="Key:")
			
		box_selection.prop(phaenotyp, "selection_compare", text="Compare:")
		box_selection.prop(phaenotyp, "selection_value", text="Value:")
		box_selection.prop(phaenotyp, "selection_threshold", text="Threshold:")
		box_selection.operator("wm.selection", text="Start")

def precast(layout):
	'''
	Panel for neural network.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")
	results = data.get("results")

	shape_key = data["structure"].data.shape_keys
	if shape_key:
		box_precast = layout.box()
		box_precast.label(text="Precast:")			
		box_precast.prop(phaenotyp, "nn_epochs", text="Epochs:")
		box_precast.prop(phaenotyp, "nn_learning_rate", text="Learning Rate:")
		box_precast.operator("wm.precast", text="Start")
		if results:
			for name, result in results.items():
				text = name + ": " + str(round(result, 3))
				box_precast.label(text=text)

def report(layout):
	'''
	Panel for report.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	box_report = layout.box()
	box_report.label(text="Report:")

	if phaenotyp.calculation_type != "geometrical":
		if phaenotyp.calculation_type != "force_distribution":
			if len(data["members"]) > 0:
				box_report.operator("wm.report_members", text="members")
				box_report.operator("wm.report_frames", text="frames")
			if len(data["quads"]) > 0:
				box_report.operator("wm.report_quads", text="quads")
		else:
			box_report.operator("wm.report_combined", text="combined")
	else:
		box_report.label(text="No report for members, frames or combined available in geometrical mode.")

	# if ga or gd
	individuals = data.get("individuals")
	if individuals:
		box_report.operator("wm.report_chromosomes", text="chromosomes")
	
		# if ga
		environment = data.get("environment")
		ga_available = environment.get("generations")
		if ga_available:
			box_report.operator("wm.report_tree", text="tree")

def error(layout, phaenotyp_version):
	'''
	Panel for error.
	:param layout: Passed layout of phaenotyp panel.
	:param text: Passed error message as string.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	# handle error
	# all this is running because of an error in on of the  panels
	# most likly this is because of a file saved in a previous version
	if data:
		process = data.get("process")
		if process:
			phaenotyp_version_file = process.get("version")
			
			box_error = layout.box()
			if phaenotyp_version_file:
				version_file = (
					phaenotyp_version_file[0],
					phaenotyp_version_file[1],
					phaenotyp_version_file[2],
					)
				
				if phaenotyp_version_file != phaenotyp_version:
					# there is an entry for version, but the version
					# but the number is not matching the current version
					box_error.label(text=(
						"This file has been created in version: "
						+ str(phaenotyp_version_file[0]) + "."
						+ str(phaenotyp_version_file[1]) + "."
						+ str(phaenotyp_version_file[2]) + "."
						+ " Please reset.")
						)
				else:
					# this should not happen
					box_error.label(text="Some conflict in versions. Please reset.")
			else:
				# there is no entry for a version but there are entries of process and data
				# it looks like this file has been created before the version control
				box_error.label(text="This file has been created in an older version. Please reset.")
		
		else:
			box_error = layout.box()
			box_error.label(text="Unknown Error. Please reset")
		
	else:
		box_error = layout.box()
		box_error.label(text="Unknown Error. Please reset")
				
def reset(layout):
	'''
	Panel for reset.
	:param layout: Passed layout of phaenotyp panel.
	'''
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	data = bpy.context.scene.get("<Phaenotyp>")

	# reset data
	box_reset = layout.box()
	box_reset.operator("wm.reset", text="Reset")
