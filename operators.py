import bpy

import os
import webbrowser

from phaenotyp import basics, material, geometry, calculation, bf, ga, gd, panel, report, progress
import itertools

def print_data(text):
	"""
	Print data for debugging
	:param text: Needs a text as string (Do not pass as list)
	"""
	print("Phaenotyp |", text)

def set_structure():
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp

	selected_objects = context.selected_objects
	obj = context.active_object

	print_data("set structure")

	# check for modifiers
	basics.check_modifiers()

	# more than two objects
	if len(selected_objects) > 1:
		if obj.type == 'CURVE':
			text = ["The selection is of type curve.",
				"Should Phaenotyp try to convert the selection to mesh?"]
			basics.popup_operator(lines=text, operator="wm.fix_structure", text="Convert curves to mesh")
			geometry.to_be_fixed = "curve_to_mesh"

		# uncommented to work with crown shyness
		'''
		else:
			text = ["Select multiple curves or a mesh only."]
			basics.popup(lines = text)
		'''
	
	# convert if meta
	elif obj.type == 'META':
		text = ["The selection is of type meta.",
			"Should Phaenotyp try to convert the selection to mesh?"]
		basics.popup_operator(lines=text, operator="wm.fix_structure", text="Meta to mesh")
		geometry.to_be_fixed = "meta_to_mesh"

	# convert if curve
	elif obj.type == 'CURVE':
		text = ["The selection is of typ curve.",
			"Should Phaenotyp try to convert the selection to mesh?"]
		basics.popup_operator(lines=text, operator="wm.fix_structure", text="Convert curve to mesh")
		geometry.to_be_fixed = "curve_to_mesh"
		
	# continue
	else:
		# if not mesh (camera, lamp, ...)
		if obj.type != 'MESH':
			text = ["Select multiple curves, metaball or a mesh only."]
			basics.popup(lines = text)

		else:
			bpy.ops.object.mode_set(mode="EDIT")

			amount_of_loose_parts = geometry.amount_of_loose_parts()
			amount_of_doubles = geometry.amount_of_doubles()
			
			if amount_of_loose_parts > 0:
				text = [
					"The mesh contains loose elements: " + str(amount_of_loose_parts),
					"Should Phaenotyp try to fix this?"]
				basics.popup_operator(lines=text, operator="wm.fix_structure", text="Delete loose parts")
				geometry.to_be_fixed = "delete_loose"
			
			elif amount_of_doubles > 0:
				text = [
					"The mesh contains vertices sharing the same position: " + str(amount_of_doubles),
					"Should Phaenotyp try to fix this?"]
				basics.popup_operator(lines=text, operator="wm.fix_structure", text="Remove doubles")
				geometry.to_be_fixed = "remove_doubles"
				
			# everything looks ok
			else:
				# crete / recreate collection
				basics.delete_col_if_existing("<Phaenotyp>")
				collection = bpy.data.collections.new("<Phaenotyp>")
				bpy.context.scene.collection.children.link(collection)

				basics.create_data()

				geometry.to_be_fixed = None
				data = scene["<Phaenotyp>"]
				data["structure"] = obj

				# check for scipy
				calculation.check_scipy()
				
				# change to face selection for force_distribution
				if phaenotyp.calculation_type == "force_distribution":
					bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')

def fix_structure():
	if geometry.to_be_fixed == "seperate_by_loose":
		print_data("Seperate by loose parts")
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.mesh.separate(type='LOOSE')
		bpy.ops.object.mode_set(mode='OBJECT')

	elif geometry.to_be_fixed == "curve_to_mesh":
		print_data("Try to convert the curves to mesh")
		bpy.ops.object.mode_set(mode="OBJECT")
		bpy.ops.object.join()
		bpy.ops.object.convert(target='MESH')
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.object.mode_set(mode='OBJECT')

	elif geometry.to_be_fixed == "meta_to_mesh":
		print_data("Try to convert meta to mesh")
		bpy.ops.object.mode_set(mode="OBJECT")
		bpy.ops.object.convert(target='MESH')

	elif geometry.to_be_fixed == "delete_loose":
		print_data("Delete loose parts")
		bpy.ops.object.mode_set(mode="EDIT")
		bpy.ops.mesh.delete_loose()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.object.mode_set(mode='OBJECT')

	elif geometry.to_be_fixed == "triangulate":
		print_data("triangulate")
		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
		bpy.ops.mesh.select_all(action='DESELECT')

	elif geometry.to_be_fixed == "remove_doubles":
		print_data("Remove doubles")
		bpy.ops.object.mode_set(mode="EDIT")
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.object.mode_set(mode='OBJECT')

	else:
		text = ["No idea how to fix this"]
		basics.popup(lines = text)
	
	set_structure()
				
def set_support():
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]

	if context.active_object.mode == "EDIT":
		# for force disbribution
		if phaenotyp.calculation_type == "force_distribution":
			if geometry.amount_of_selected_faces() != 1:
				text = ["Select one face as support for force distribution only."]
				basics.popup(lines = text)

			# apply supports
			else:
				# get selected vertices
				bpy.ops.object.mode_set(mode="OBJECT")
				bpy.ops.object.mode_set(mode="EDIT")

				for vertex in obj.data.vertices:
					if vertex.select:
						id = vertex.index

						support = [
							phaenotyp.loc_x,
							phaenotyp.loc_y,
							phaenotyp.loc_z,
							phaenotyp.rot_x,
							phaenotyp.rot_y,
							phaenotyp.rot_z
							]

						data["supports"][str(id)] = support

						# delete support if user is deleting the support
						# (set all conditions to False and apply)
						fixed = False
						for i in range(6):
							if support[i] == True:
								fixed = True

						if not fixed:
							data["supports"].pop(str(id))

				# delete face and edges to work with force distribution
				geometry.delete_selected_faces()

				# delete obj if existing
				basics.delete_obj_if_existing("<Phaenotyp>support")
				basics.delete_mesh_if_existing("<Phaenotyp>support")

				# create one mesh for all
				geometry.create_supports(data["structure"], data["supports"])

			# leave signs of support, structure and go to edit-mode
			# (in order to let the user define more supports)
			bpy.ops.object.mode_set(mode="OBJECT")
			bpy.ops.object.select_all(action='DESELECT')
			obj.select_set(True)
			bpy.context.view_layer.objects.active = obj
			bpy.ops.object.mode_set(mode="EDIT")
			bpy.context.space_data.shading.type = 'WIREFRAME'

		# for PyNite
		else:
			# get selected vertices
			bpy.ops.object.mode_set(mode="OBJECT")
			bpy.ops.object.mode_set(mode="EDIT")

			for vertex in obj.data.vertices:
				if vertex.select:
					id = vertex.index

					support = [
						phaenotyp.loc_x,
						phaenotyp.loc_y,
						phaenotyp.loc_z,
						phaenotyp.rot_x,
						phaenotyp.rot_y,
						phaenotyp.rot_z
						]

					data["supports"][str(id)] = support

					# delete support if user is deleting the support
					# (set all conditions to False and apply)
					fixed = False
					for i in range(6):
						if support[i] == True:
							fixed = True

					if not fixed:
						data["supports"].pop(str(id))

			# delete obj if existing
			basics.delete_obj_if_existing("<Phaenotyp>support")
			basics.delete_mesh_if_existing("<Phaenotyp>support")

			# create one mesh for all
			geometry.create_supports(data["structure"], data["supports"])

		# leave signs of support, structure and go to edit-mode
		# (in order to let the user define more supports)
		bpy.ops.object.mode_set(mode="OBJECT")
		bpy.ops.object.select_all(action='DESELECT')
		obj.select_set(True)
		bpy.context.view_layer.objects.active = obj
		bpy.ops.object.mode_set(mode="EDIT")

def set_member():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	frame = bpy.context.scene.frame_current

	bpy.ops.object.mode_set(mode="OBJECT")

	# create new member for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		for edge in obj.data.edges:
			vertex_0_id = edge.vertices[0]
			vertex_1_id = edge.vertices[1]

			if edge.select:
				id = edge.index

				member = {}

				# this variables are always fix
				member["name"] = "member_" + str(id) # equals edge-id
				member["vertex_0_id"] = vertex_0_id # equals id of vertex
				member["vertex_1_id"] = vertex_1_id # equals id of vertex

				member["acceptable_sigma"] = material.current["acceptable_sigma"] # from gui
				member["acceptable_shear"] = material.current["acceptable_shear"] # from gui
				member["acceptable_torsion"] = material.current["acceptable_torsion"] # from gui
				member["acceptable_sigmav"] = material.current["acceptable_sigmav"] # from gui
				member["knick_model"] = material.current["knick_model"] # from gui
				
				member["material_name"] = material.current["material_name"]
				member["E"] = material.current["E"] # from gui
				member["G"] = material.current["G"] # from gui
				member["d"] = material.current["d"] # from gui

				# this variables can change per frame
				# the key "first" is used to store the user-input of each member
				# this is importand, if a user is chaning the frame during the
				# input for some reason
				member["Do"] = {}
				member["Di"] = {}

				member["Do_first"] = material.current["Do"] # from gui
				member["Di_first"] = material.current["Di"] # from fui

				member["type"] = phaenotyp.member_type # from gui
				
				member["Iy"] = {}
				member["Iz"] = {}
				member["J"] = {}
				member["A"] = {}
				member["kg_A"] = {}
				member["ir"] = {}

				member["Iy_first"] = material.current["Iy"] # from gui
				member["Iz_first"] = material.current["Iz"] # from gui
				member["J_first"] = material.current["J"] # from gui
				member["A_first"] = material.current["A"] # from gui
				member["kg_first"] = material.current["kg_A"] # from gui
				member["ir_first"] = material.current["ir"] # from gui

				# results
				member["axial"] = {}
				member["moment_y"] = {}
				member["moment_z"] = {}
				member["moment_h"] = {}
				member["shear_y"] = {}
				member["shear_z"] = {}
				member["shear_h"] = {}
				member["torque"] = {}
				member["sigma"] = {}

				member["Wy"] = {}
				member["WJ"] = {}

				member["long_stress"] = {}
				member["tau_shear"] = {}
				member["tau_torsion"] = {}
				member["sum_tau"] = {}
				member["sigmav"] = {}
				member["sigma"] = {}
				member["max_long_stress"] = {}
				member["max_tau_shear"] = {}
				member["max_tau_torsion"] = {}
				member["max_sum_tau"] = {}
				member["max_sigmav"] = {}
				member["max_sigma"] = {}
				member["acceptable_sigma_buckling"] = {}
				member["lamda"] = {}
				member["lever_arm"] = {}
				member["max_lever_arm"] = {}
				member["initial_positions"] = {}
				member["deflection"] = {}
				member["overstress"] = {}
				member["utilization"] = {}

				member["normal_energy"] = {}
				member["moment_energy"] = {}
				member["strain_energy"] = {}

				member["kg"] = {}
				member["length"] = {}

				data["members"][str(id)] = member

	# create new member for PyNite
	else:
		for edge in obj.data.edges:
			vertex_0_id = edge.vertices[0]
			vertex_1_id = edge.vertices[1]

			if edge.select:
				id = edge.index

				member = {}

				# this variables are always fix
				member["name"] = "member_" + str(id) # equals edge-id
				member["vertex_0_id"] = vertex_0_id # equals id of vertex
				member["vertex_1_id"] = vertex_1_id # equals id of vertex

				member["acceptable_sigma"] = material.current["acceptable_sigma"] # from gui

				member["E"] = material.current["E"] # from gui
				member["G"] = material.current["G"] # from gui
				member["d"] = material.current["d"] # from gui

				# this variables can change per frame
				# the key "first" is used to store the user-input of each member
				# this is importand, if a user is chaning the frame during the
				# input for some reason
				member["Do"] = {}
				member["Di"] = {}

				member["Do_first"] = material.current["Do"] # from gui
				member["Di_first"] = material.current["Di"] # from fui

				member["Iy"] = {}
				member["Iz"] = {}
				member["J"] = {}
				member["A"] = {}
				member["kg_A"] = {}
				member["ir"] = {}

				member["Iy_first"] = material.current["Iy"] # from gui
				member["Iz_first"] = material.current["Iz"] # from gui
				member["J_first"] = material.current["J"] # from gui
				member["A_first"] = material.current["A"] # from gui
				member["kg_first"] = material.current["kg_A"] # from gui
				member["ir_first"] = material.current["ir"] # from gui

				# results
				member["axial"] = {}
				member["sigma"] = {}

				member["initial_positions"] = {}
				member["deflection"] = {}
				member["overstress"] = {}
				member["utilization"] = {}

				member["kg"] = {}
				member["length"] = {}

				data["members"][str(id)] = member

	# delete obj if existing
	basics.delete_obj_if_existing("<Phaenotyp>member")
	basics.delete_mesh_if_existing("<Phaenotyp>member")

	# create one mesh for all
	geometry.create_members(data["structure"], data["members"])

	# leave membersand go to edit-mode
	# (in order to let the user define more supports)
	bpy.ops.object.mode_set(mode="OBJECT")
	bpy.ops.object.select_all(action='DESELECT')
	obj.select_set(True)
	bpy.context.view_layer.objects.active = data["structure"]
	bpy.ops.object.mode_set(mode="EDIT")

	# switch to wireframe
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			for space in area.spaces:
				if space.type == 'VIEW_3D':
					space.shading.type = 'WIREFRAME'

	# to avoid key-error in optimization
	data["done"][str(frame)] = False

def set_quad():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	frame = bpy.context.scene.frame_current

	bpy.ops.object.mode_set(mode="OBJECT")

	# this operator is only working for PyNite
	# it is only called in this calculation_type
	for face in obj.data.polygons:		
		if face.select:
			id = face.index
			vertices_ids = face.vertices
			
			quad = {}

			# this variables are always fix
			quad["name"] = "quad_" + str(id)
			quad["vertices_ids_structure"] = vertices_ids # structure obj
			quad["vertices_ids_viz"] = {} # obj for visualization
			
			quad["thickness"] = phaenotyp.thickness # from gui
			quad["E"] = phaenotyp.E_quads # from gui
			quad["G"] = phaenotyp.G_quads # from gui
			quad["nu"] = phaenotyp.nu_quads # from gui
			quad["rho"] = phaenotyp.rho_quads # from gui

			# results
			quad["shear_x"] = {}
			quad["shear_y"] = {}
			
			quad["moment_x"] = {}
			quad["moment_y"] = {}
			quad["moment_xy"] = {}
			
			quad["membrane_x"] = {}
			quad["membrane_y"] = {}
			quad["membrane_xy"] = {}

			quad["initial_positions"] = {}
			quad["deflection"] = {}
			quad["overstress"] = {}
			quad["utilization"] = {}

			quad["kg"] = {}
			quad["area"] = {}

			data["quads"][str(id)] = quad

	# delete obj if existing
	basics.delete_obj_if_existing("<Phaenotyp>quads")
	basics.delete_mesh_if_existing("<Phaenotyp>quads")

	# create one mesh for all
	geometry.create_quads(data["structure"], data["quads"])

	# leave membersand go to edit-mode
	# (in order to let the user define more supports)
	bpy.ops.object.mode_set(mode="OBJECT")
	bpy.ops.object.select_all(action='DESELECT')
	obj.select_set(True)
	bpy.context.view_layer.objects.active = data["structure"]
	bpy.ops.object.mode_set(mode="EDIT")

	# switch to wireframe
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			for space in area.spaces:
				if space.type == 'VIEW_3D':
					space.shading.type = 'WIREFRAME'

	# to avoid key-error in optimization
	data["done"][str(frame)] = False

def set_load():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	
	calculation_type = phaenotyp.calculation_type
	
	# create load
	#bpy.ops.object.mode_set(mode="OBJECT") # <---- to avoid "out-of-range-error" on windows
	bpy.ops.object.mode_set(mode="EDIT") # <---- to avoid "out-of-range-error" on windows
	bpy.ops.object.mode_set(mode="OBJECT") # <---- to avoid "out-of-range-error" on windows

	# pass user input to data

	if phaenotyp.load_type == "vertices":
		for vertex in obj.data.vertices:
			if vertex.select:
				id = vertex.index
				
				if calculation_type not in ["geometrical", "force_distribution"]:
					load = [
						phaenotyp.load_FX,
						phaenotyp.load_FY,
						phaenotyp.load_FZ,
						phaenotyp.load_MX,
						phaenotyp.load_MY,
						phaenotyp.load_MZ
						]
				else:
					load = [
						phaenotyp.load_FX,
						phaenotyp.load_FY,
						phaenotyp.load_FZ
						]

				data["loads_v"][str(id)] = load

				# delete load if user is deleting the load
				# (set all conditions to False and apply)
				force = False
				if calculation_type not in ["geometrical", "force_distribution"]:
					for i in range(6):
						if load[i] != 0:
							force = True
				else:
					for i in range(3):
						if load[i] != 0:
							force = True
							
				if not force:
					data["loads_v"].pop(str(id))

	if phaenotyp.load_type == "edges":
		for edge in obj.data.edges:
			vertex_0_id = edge.vertices[0]
			vertex_1_id = edge.vertices[1]

			if edge.select:
				id = edge.index
				
				if calculation_type not in ["geometrical", "force_distribution"]:
					load = [
						phaenotyp.load_FX,
						phaenotyp.load_FY,
						phaenotyp.load_FZ,
						phaenotyp.load_Fx,
						phaenotyp.load_Fy,
						phaenotyp.load_Fz
						]
				else:
					load = [
						phaenotyp.load_FX,
						phaenotyp.load_FY,
						phaenotyp.load_FZ
						]

				data["loads_e"][str(id)] = load

				# delete load if user is deleting the load
				# (set all conditions to False and apply)
				force = False
				if calculation_type not in ["geometrical", "force_distribution"]:
					for i in range(6):
						if load[i] != 0:
							force = True
				else:
					for i in range(3):
						if load[i] != 0:
							force = True
							
				if not force:
					data["loads_e"].pop(str(id))

	if phaenotyp.load_type == "faces":
		for polygon in obj.data.polygons:
			if polygon.select:
				id = polygon.index
				load = [
					phaenotyp.load_normal,
					phaenotyp.load_projected,
					phaenotyp.load_area_z,
					]

				data["loads_f"][str(id)] = load

				# delete load if user is deleting the load
				# (set all conditions to False and apply)
				force = False
				for i in range(3):
					if load[i] != 0:
						force = True

				if not force:
					data["loads_f"].pop(str(id))

	# delete text of loads
	basics.delete_obj_if_name_contains("<Phaenotyp>load")

	# run one function for all loads
	geometry.create_loads(obj, data["loads_v"], data["loads_e"], data["loads_f"])

	bpy.ops.object.mode_set(mode="EDIT")

def assimilate():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	supports = scene["<Phaenotyp>"]["supports"]
	frame = bpy.context.scene.frame_current

	obj = data["structure"]
	vertices = obj.data.vertices
	edges = obj.data.edges

	bpy.ops.object.mode_set(mode="OBJECT")

	# get ids of supports
	support_ids = []
	for id, support in supports.items():
		support_id = int(id)
		support_ids.append(support_id)

	target = phaenotyp.assimilate_length
	strength = phaenotyp.assimilate_strength * 0.01
	iterations = phaenotyp.assimilate_iterations
	
	# assimilate all edges
	for i in range(iterations):
		for edge in edges:
			v_0_id = edge.vertices[0]
			v_1_id = edge.vertices[1]

			v_0 = vertices[v_0_id].co
			v_1 = vertices[v_1_id].co

			dist_v = v_1 - v_0
			dist = dist_v.length

			if dist > target:
				if v_0_id not in support_ids:
					vertices[v_0_id].co = v_0 + dist_v*strength
				if v_1_id not in support_ids:
					vertices[v_1_id].co = v_1 - dist_v*strength

			else:
				if v_0_id not in support_ids:
					vertices[v_0_id].co = v_0 - dist_v*strength
				if v_1_id not in support_ids:
					vertices[v_1_id].co = v_1 + dist_v*strength

def actuator():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	supports = scene["<Phaenotyp>"]["supports"]
	frame = bpy.context.scene.frame_current

	obj = data["structure"]
	vertices = obj.data.vertices
	edges = obj.data.edges

	bpy.ops.object.mode_set(mode="OBJECT")

	# target lenght from gui
	length = phaenotyp.actuator_length
	strength = phaenotyp.actuator_strength * 0.01
	iterations = phaenotyp.actuator_iterations
	
	# get current length of each edge
	lengthes = {}
	
	for edge in edges:
		v_0_id = edge.vertices[0]
		v_1_id = edge.vertices[1]

		v_0 = vertices[v_0_id].co
		v_1 = vertices[v_1_id].co

		dist_v = v_1 - v_0
		dist = dist_v.length

		lengthes[str(edge.index)] = dist

	# get id of supports
	support_ids = []
	for id, support in supports.items():
		support_id = int(id)
		support_ids.append(support_id)

	# set target length to all selected edges
	for edge in edges:
		if edge.select == True:
			id = edge.index
			lengthes[str(id)] = length

	# change lengthes
	for i in range(iterations):
		for edge in edges:
			v_0_id = edge.vertices[0]
			v_1_id = edge.vertices[1]

			v_0 = vertices[v_0_id].co
			v_1 = vertices[v_1_id].co

			dist_v = v_1 - v_0
			dist = dist_v.length

			if dist > lengthes[str(edge.index)]:
				# move only if no support
				# allow to move if only fixed in other direction?
				if v_0_id not in support_ids:
					vertices[v_0_id].co = v_0 + dist_v*strength
				if v_1_id not in support_ids:
					vertices[v_1_id].co = v_1 - dist_v*strength

			else:
				if v_0_id not in support_ids:
					vertices[v_0_id].co = v_0 - dist_v*strength
				if v_1_id not in support_ids:
					vertices[v_1_id].co = v_1 + dist_v*strength

def reach_goal():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	supports = scene["<Phaenotyp>"]["supports"]
	frame = bpy.context.scene.frame_current

	obj = data["structure"]
	vertices = obj.data.vertices
	edges = obj.data.edges

	bpy.ops.object.mode_set(mode="OBJECT")

	strength = phaenotyp.goal_strength * 0.01
	iterations = phaenotyp.goal_iterations
	
	# get empties
	empties = []
	for selected_obj in bpy.context.selected_objects:
		if selected_obj.type == "EMPTY":
			empties.append(selected_obj)

	# check conditions
	if len(empties) != 1:
		# stop animation if it is playing
		if bpy.context.screen.is_animation_playing:
			bpy.ops.screen.animation_play()
		
		# drop message for user
		text = ["Select one empty only."]
		basics.popup(lines = text)

	else:
		empty = empties[0]

		# target lenght from gui
		length = phaenotyp.actuator_length

		# get current length of each edge
		lengthes = {}

		for edge in edges:
			v_0_id = edge.vertices[0]
			v_1_id = edge.vertices[1]

			v_0 = vertices[v_0_id].co
			v_1 = vertices[v_1_id].co

			dist_v = v_1 - v_0
			dist = dist_v.length

			lengthes[str(edge.index)] = dist

		# get id of supports
		support_ids = []
		for id, support in supports.items():
			support_id = int(id)
			support_ids.append(support_id)

		# towards empty
		for i in range(iterations):
			for vertex in vertices:
				vertex_co = vertex.co
				empty_loc = empty.location

				dist_v = vertex_co - empty_loc
				dist = dist_v.length

				if dist > 1:
					if vertex.index not in support_ids:
						vertex.co = vertex_co - dist_v*strength


			# keep lenghtes
			for edge in edges:
				v_0_id = edge.vertices[0]
				v_1_id = edge.vertices[1]

				v_0 = vertices[v_0_id].co
				v_1 = vertices[v_1_id].co

				dist_v = v_1 - v_0
				dist = dist_v.length

				if dist > lengthes[str(edge.index)]:
					# move only if no support
					# allow to move if only fixed in other direction?
					if v_0_id not in support_ids:
						vertices[v_0_id].co = v_0 + dist_v*strength
					if v_1_id not in support_ids:
						vertices[v_1_id].co = v_1 - dist_v*strength

				else:
					if v_0_id not in support_ids:
						vertices[v_0_id].co = v_0 - dist_v*strength
					if v_1_id not in support_ids:
						vertices[v_1_id].co = v_1 + dist_v*strength
			
def wool_threads():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	supports = scene["<Phaenotyp>"]["supports"]
	frame = bpy.context.scene.frame_current

	obj = data["structure"]
	vertices = obj.data.vertices
	edges = obj.data.edges
	edge_keys = obj.data.edge_keys
	members = data["members"]

	bpy.ops.object.mode_set(mode="OBJECT")

	# get ids of supports
	support_ids = []
	for id, support in supports.items():
		support_id = int(id)
		support_ids.append(support_id)
	
	# get list of distances at start
	length = members[list(members)[0]]["length"].get("0")
	if length:
		# only create distances if not available
		pass
	
	else:
		# create lengthes at first frame
		# this is necessary because the wool is
		# using the link length of the beginning
		for id, member in members.items():
			edge = edges[int(id)]
			v_0 = vertices[edge.vertices[0]].co
			v_1 = vertices[edge.vertices[1]].co
			v = v_1 - v_0
			dist = v.length
			member["length"]["0"] = dist
	
	# parameters
	gravity_strength = phaenotyp.gravity_strength * 0.01 # to make readable slider
	link_strength = phaenotyp.link_strength
	bonding_threshold = phaenotyp.bonding_threshold
	bonding_strength = phaenotyp.bonding_strength * 0.0001 # to make readable slider
	iterations = phaenotyp.wool_iterations	# 10.0
	
	# get parts as list of ids of vertices
	parts = geometry.parts()
	
	# get pairs inside of threshold
	inside = data["process"].get("inside_bonding")
	if inside:
		pass
	else:
		combinations = [(a,b) for a in parts for b in parts if a != b]
		inside = []
		for a,b in combinations:
			for vertex_id in parts[a]:
				for other_id in parts[b]:
					vertex = vertices[vertex_id]
					other = vertices[other_id]
					
					v_0 = vertex.co
					v_1 = other.co
					v = v_1 - v_0
					dist = v.length
					
					if dist < bonding_threshold:
						pair = [vertex_id, other_id]
						sorted_pair = sorted(pair)
						inside.append(sorted_pair)
		
		inside = list(inside for inside,_ in itertools.groupby(inside))
		data["process"]["inside_bonding"] = inside
		inside = data["process"]["inside_bonding"]
		
	for i in range(iterations):
		# links
		for id, key in enumerate(edge_keys):
			# get current distance
			v_0_id = key[0]
			v_1_id = key[1]
			
			v_0 = vertices[v_0_id].co
			v_1 = vertices[v_1_id].co
			v = v_1 - v_0
			dist = v.length

			# shrink and exapand
			length = members[str(id)]["length"]["0"]
			strength = length - dist
			if v_0_id not in support_ids:
				# gravity
				v_0[2] -= length * gravity_strength
				# shrink and exapand
				v_0 -= v * strength * link_strength
				
			if v_1_id not in support_ids:
				# gravity
				v_1[2] -= length * gravity_strength
				# shrink and exapand
				v_1 += v * strength * link_strength
		
		# run trought pairs of closest vertices
		for a,b in inside:			
			v_0 = vertices[a].co
			v_1 = vertices[b].co
			v = v_1 - v_0
			dist = v.length
			
			# move points towards each other
			if a not in support_ids:
				v_0 += v * bonding_strength
			if b not in support_ids:
				v_1 -= v * bonding_strength
	
	# recreate combination and closest
	if frame % 25 == 0:
		del data["process"]["inside_bonding"]

def crown_shyness():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	supports = scene["<Phaenotyp>"]["supports"]
	frame = bpy.context.scene.frame_current

	obj = data["structure"]
	vertices = obj.data.vertices
	edges = obj.data.edges

	bpy.ops.object.mode_set(mode="OBJECT")
	
	# get ids of supports
	support_ids = []
	for id, support in supports.items():
		support_id = int(id)
		support_ids.append(support_id)
	
	# parameters
	shyness_threshold = phaenotyp.shyness_threshold
	shyness_strength = phaenotyp.shyness_strength * (-0.001)
	growth_strength = phaenotyp.growth_strength * 0.001
	iterations = phaenotyp.crown_iterations
	
	# get parts as list of ids of vertices
	parts = geometry.parts()

	# get pairs inside of threshold
	inside = data["process"].get("inside_shyness")
	outside = data["process"].get("outside_shyness")
	if inside:
		pass
	else:
		combinations = [(a,b) for a in parts for b in parts if a != b]
		inside = []
		outside = [i for i in range(len(vertices))]
		for a,b in combinations:
			for vertex_id in parts[a]:
				for other_id in parts[b]:
					vertex = vertices[vertex_id]
					other = vertices[other_id]
					
					v_0 = vertex.co
					v_1 = other.co
					v = v_1 - v_0
					dist = v.length
					
					if dist < shyness_threshold:
						pair = [vertex_id, other_id]
						sorted_pair = sorted(pair)
						inside.append(sorted_pair)
						
						if vertex_id in outside:
							outside.remove(vertex_id)
						
						if other_id in outside:
							outside.remove(other_id)
		
		inside = list(inside for inside,_ in itertools.groupby(inside))
		data["process"]["inside_shyness"] = inside
		inside = data["process"]["inside_shyness"]
		
		data["process"]["outside_shyness"] = outside
		outside = data["process"]["outside_shyness"]
	
	# run trought pairs of closest vertices
	for a,b in inside:			
		v_0 = vertices[a].co
		v_1 = vertices[b].co
		v = v_1 - v_0
		
		# avoid
		if a not in support_ids:
			v_0 += v * shyness_strength

		if b not in support_ids:
			v_1 -= v * shyness_strength
				
	# grow
	for vertex_id in outside:
		if vertex_id not in support_ids:
			vertex = vertices[vertex_id]
			normal = vertex.normal
			vertex.co += normal * growth_strength

	# recreate combination and closest
	if frame % 25 == 0:
		del data["process"]["inside_shyness"]
		del data["process"]["outside_shyness"]
		
def store_co():
	'''
	Is storing the position of all vertices at the current state to be restored after translation.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	vertices = obj.data.vertices
	
	data["process"]["stored"] = {}
	stored = data["process"]["stored"]
	
	for vertex in vertices:
		id = vertex.index
		co = vertex.co
		stored[str(id)] = co
	
def restore_co():
	'''
	Is restoring the position of all vertices prevously stored.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	vertices = obj.data.vertices
	
	stored = data["process"]["stored"]
	
	for vertex in vertices:
		id = vertex.index
		vertex.co = stored[str(id)]
		
def calculate_single_frame():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		interweave_results = calculation.interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		interweave_results = calculation.interweave_results_fd

	# calculate new properties for each member
	geometry.update_geometry_pre()

	# created a model object
	models = {}
	models[str(frame)] = prepare_fea()

	# run singlethread and get results
	feas = calculation.run_mp(models)

	# wait for it and interweave results to data
	interweave_results(feas)

	# calculate new visualization-mesh
	geometry.update_geometry_post()

	basics.view_vertex_colors()

def calculate_animation():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		interweave_results = calculation.interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		interweave_results = calculation.interweave_results_fd

	# if optimization
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none":
		if phaenotyp.animation_optimization_type == "each_frame":
			start = bpy.context.scene.frame_start
			end = bpy.context.scene.frame_end + 1 # to render also last frame

			amount = end-start

			# start progress
			progress.run()
			progress.http.reset_pci(amount)

			# create list of models
			models = {}

			# run analysis for each frame first
			for frame in range(start, end):
				# update scene
				bpy.context.scene.frame_current = frame
				bpy.context.view_layer.update()

				# calculate new properties for each member
				geometry.update_geometry_pre()

				# created a model object of PyNite and add to dict
				model = prepare_fea()
				models[frame] = model

			# run mp and get results
			feas = calculation.run_mp(models)

			# wait for it and interweave results to data
			interweave_results(feas)

			# calculate new visualization-mesh
			geometry.update_geometry_post()

			progress.http.reset_o(phaenotyp.optimization_amount)
			
			# run optimization and analysis
			for i in range(phaenotyp.optimization_amount):
				progress.http.reset_pci(amount)
				
				for frame in range(start, end):
					# update scene
					bpy.context.scene.frame_current = frame
					bpy.context.view_layer.update()

					# run optimization and get new properties
					if phaenotyp.calculation_type == "force_distribution":
						if phaenotyp.optimization_fd == "approximate":
							calculation.approximate_sectional()

					else:
						if phaenotyp.optimization_pn == "simple":
							calculation.simple_sectional()

						if phaenotyp.optimization_pn == "utilization":
							calculation.utilization_sectional()

						if phaenotyp.optimization_pn == "complex":
							calculation.complex_sectional()

					# calculate new properties for each member
					geometry.update_geometry_pre()

					# created a model object of PyNite and add to dict
					model = prepare_fea()
					models[frame] = model
				
				# run mp and get results
				feas = calculation.run_mp(models)

				# wait for it and interweave results to data
				interweave_results(feas)

				# calculate new visualization-mesh
				geometry.update_geometry_post()
				
				progress.http.update_o()

			# update view
			basics.view_vertex_colors()

		if phaenotyp.animation_optimization_type == "gradient":
			start = bpy.context.scene.frame_start
			end = start + phaenotyp.optimization_amount
			
			amount = end - start

			# start progress
			progress.run()
			progress.http.reset_pci(amount*2)

			# update scene
			bpy.context.scene.frame_current = start
			bpy.context.view_layer.update()

			# mp is not working, because the previous frame is needed
			# run in single frame
			calculate_single_frame()

			# run analysis first
			for frame in range(start+1, end):
				# update scene
				bpy.context.scene.frame_current = frame
				bpy.context.view_layer.update()

				# copy previous frame to current
				for id, member in members.items():
					member["Do"][str(frame)] = member["Do"][str(frame-1)]
					member["Di"][str(frame)] = member["Di"][str(frame-1)]

				calculate_single_frame()

				# run optimization and get new properties
				if phaenotyp.calculation_type == "force_distribution":
					if phaenotyp.optimization_fd == "approximate":
						optimize_approximate()

				else:
					if phaenotyp.optimization_pn == "simple":
						optimize_simple()

					if phaenotyp.optimization_pn == "utilization":
						optimize_utilization()

					if phaenotyp.optimization_pn == "complex":
						optimize_complex()
		
			bpy.context.scene.frame_end = frame

	# without optimization
	else:
		start = bpy.context.scene.frame_start
		end = bpy.context.scene.frame_end + 1 # to render also last frame

		# start progress
		progress.run()
		progress.http.reset_pci(end-start)

		# create list of models
		models = {}

		# run analysis for each frame first
		for frame in range(start, end):
			# update scene
			bpy.context.scene.frame_current = frame
			bpy.context.view_layer.update()

			# calculate new properties for each member
			geometry.update_geometry_pre()

			# created a model object of PyNite and add to dict
			model = prepare_fea()
			models[frame] = model

		# run mp and get results
		feas = calculation.run_mp(models)

		# wait for it and interweave results to data
		interweave_results(feas)

		# calculate new visualization-mesh
		geometry.update_geometry_post()

		# update view
		basics.view_vertex_colors()

	# join progress
	progress.http.active = False
	progress.http.Thread_hosting.join()

def optimize_approximate():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	print_data("approximate sectional performance")

	calculation.approximate_sectional()

	# calculate new properties for each member
	geometry.update_geometry_pre()

	# created a model object
	models = {}
	models[str(frame)] = calculation.prepare_fea_fd()

	# run singlethread and get results
	feas = calculation.run_mp(models)

	# wait for it and interweave results to data
	calculation.interweave_results_fd(feas)

	# calculate new visualization-mesh
	geometry.update_geometry_post()

	basics.view_vertex_colors()

def optimize_simple():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	print_data("simple sectional performance")
	
	calculation.simple_sectional()

	# calculate new properties for each member
	geometry.update_geometry_pre()

	# created a model object
	models = {}
	models[str(frame)] = calculation.prepare_fea_pn()

	# run singlethread and get results
	feas = calculation.run_mp(models)

	# wait for it and interweave results to data
	calculation.interweave_results_pn(feas)

	# calculate new visualization-mesh
	geometry.update_geometry_post()

	basics.view_vertex_colors()

def optimize_utilization():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	print_data("utilization sectional performance")

	calculation.utilization_sectional()

	# calculate new properties for each member
	geometry.update_geometry_pre()

	# created a model object
	models = {}
	models[str(frame)] = calculation.prepare_fea_pn()

	# run singlethread and get results
	feas = calculation.run_mp(models)

	# wait for it and interweave results to data
	calculation.interweave_results_pn(feas)

	# calculate new visualization-mesh
	geometry.update_geometry_post()

	basics.view_vertex_colors()

def optimize_complex():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	print_data("complex sectional performance")

	calculation.complex_sectional()

	# calculate new properties for each member
	geometry.update_geometry_pre()

	# created a model object
	models = {}
	models[str(frame)] = calculation.prepare_fea_pn()

	# run singlethread and get results
	feas = calculation.run_mp(models)

	# wait for it and interweave results to data
	calculation.interweave_results_pn(feas)

	# calculate new visualization-mesh
	geometry.update_geometry_post()

	basics.view_vertex_colors()

def topolgy_decimate():
	print_data("Decimate topological performance")
	calculation.decimate_topology()

def bf_start():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]

	print_data("Start bruteforce over selected shape keys")

	data["environment"]["genes"] = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
	data["individuals"] = {}
	individuals = data["individuals"]

	if phaenotyp.calculation_type == "force_distribution":
		if phaenotyp.optimization_fd == "approximate":
			optimization_amount = phaenotyp.optimization_amount
		else:
			optimization_amount = 0

	else:
		if phaenotyp.optimization_pn in ["simple", "utilization", "complex"]:
			optimization_amount = phaenotyp.optimization_amount
		else:
			optimization_amount = 0

	# skip optimization if geometrical only
	if phaenotyp.calculation_type == "geometrical":
		optimization_amount = 0

	# start progress
	progress.run()
	progress.http.reset_pci(1)
	progress.http.reset_o(optimization_amount)

	# set frame_start
	bpy.context.scene.frame_start = 0

	# generate an individual as basis at frame 0
	# this individual has choromosome with all genes equals 0
	# the fitness of this chromosome is the basis for all others
	bf.generate_basis()

	for i in range(optimization_amount):
		progress.http.reset_pci(1)
		calculation.sectional_optimization(0, 1)
		progress.http.update_o()

	progress.http.reset_pci(1)
	calculation.calculate_fitness(0, 1)
	individuals["0"]["fitness"]["weighted"] = 1

	data = scene["<Phaenotyp>"]
	shape_keys = obj.data.shape_keys.key_blocks

	# create matrix of possible combinations
	matrix = []
	for key in range(len(shape_keys)-1): # to exclude basis
		genes = data["environment"]["genes"]
		matrix.append(genes)

	chromosomes = list(itertools.product(*matrix))
	chromosomes.pop(0) # delete the basis individual, is allready calculated

	# create start and end of calculation and create individuals
	start = 1 # basis indiviual is allready created and optimized
	end = len(chromosomes)+1

	# set frame_end to first size of inital generation
	bpy.context.scene.frame_end = end-1

	# progress
	progress.http.reset_pci(end-start)
	progress.http.reset_o(optimization_amount)

	# pair with bruteforce
	bf.bruteforce(chromosomes)
	for i in range(optimization_amount):
		progress.http.reset_pci(end-start)
		calculation.sectional_optimization(start, end)
		progress.http.update_o()

	calculation.calculate_fitness(start, end)

	if phaenotyp.calculation_type != "geometrical":
		basics.view_vertex_colors()

	# join progress
	progress.http.active = False
	progress.http.Thread_hosting.join()

def ga_start():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]

	print_data("Start genetic mutation over selected shape keys")

	# pass from gui
	data["environment"]["generation_size"] = phaenotyp.generation_size
	data["environment"]["elitism"] = phaenotyp.elitism
	data["environment"]["generation_amount"] = phaenotyp.generation_amount
	data["environment"]["new_generation_size"] = phaenotyp.generation_size - phaenotyp.elitism

	# clear to restart
	data["environment"]["generations"] = {}
	data["environment"]["generation_id"] = 0
	data["environment"]["genes"] = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
	data["individuals"] = {}

	# shorten
	generation_size = data["environment"]["generation_size"]
	elitism = data["environment"]["elitism"]
	generation_amount = data["environment"]["generation_amount"]
	new_generation_size = data["environment"]["new_generation_size"]
	generation_id = data["environment"]["generation_id"]
	individuals = data["individuals"]

	if phaenotyp.calculation_type == "force_distribution":
		if phaenotyp.optimization_fd == "approximate":
			optimization_amount = phaenotyp.optimization_amount
		else:
			optimization_amount = 0

	else:
		if phaenotyp.optimization_pn in ["simple", "utilization", "complex"]:
			optimization_amount = phaenotyp.optimization_amount
		else:
			optimization_amount = 0

	# skip optimization if geometrical only
	if phaenotyp.calculation_type == "geometrical":
		optimization_amount = 0

	# start progress
	progress.run()
	progress.http.reset_pci(1)
	progress.http.reset_o(optimization_amount)

	# set frame_start
	bpy.context.scene.frame_start = 0

	# generate an individual as basis at frame 0
	# this individual has choromosome with all genes equals 0
	# the fitness of this chromosome is the basis for all others
	ga.generate_basis()

	for i in range(optimization_amount):
		progress.http.reset_pci(1)
		calculation.sectional_optimization(0, 1)
		progress.http.update_o()

	progress.http.reset_pci(1)
	calculation.calculate_fitness(0, 1)
	individuals["0"]["fitness"]["weighted"] = 1

	# create start and end of calculation and create individuals
	start = 1
	end = generation_size

	# set frame_end to first size of inital generation
	bpy.context.scene.frame_end = end

	# progress
	progress.http.reset_pci(end-start)
	progress.http.g = [0, generation_amount]
	progress.http.reset_o(optimization_amount)

	# create initial generation
	# the first generation contains 20 individuals (standard value is 20)
	# the indiviuals are created with random genes
	# there is no elitism possible, because there is no previous group
	ga.create_initial_individuals(start, end)

	# optimize if sectional performance if activated
	for i in range(optimization_amount):
		progress.http.reset_pci(end-start)
		calculation.sectional_optimization(start, end)
		progress.http.update_o()

	progress.http.reset_pci(end-start)
	calculation.calculate_fitness(start, end)
	ga.populate_initial_generation()

	# create all other generations
	# 2 indiviuals are taken from previous group (standard value is 10)
	# 10 indiviuals are paired (standard ist 50 %)
	for i in range(generation_amount):
		start = end
		end = start + new_generation_size

		# expand frame
		bpy.context.scene.frame_end = end

		# create new generation and copy fittest percent
		ga.do_elitism()

		# create 18 new individuals (standard value of 20 - 10 % elitism)
		progress.http.reset_pci(end-start)
		progress.http.reset_o(optimization_amount)

		ga.create_new_individuals(start, end)

		for i in range(optimization_amount):
			progress.http.reset_pci(end-start)
			calculation.sectional_optimization(start, end)
			progress.http.update_o()

		calculation.calculate_fitness(start, end)
		ga.populate_new_generation(start, end)

		# update progress
		progress.http.update_g()

	if phaenotyp.calculation_type != "geometrical":
		basics.view_vertex_colors()

	# join progress
	progress.http.active = False
	progress.http.Thread_hosting.join()

def gd_start():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]

	print_data("Start gradient descent over selected shape keys")

	progress.run()

	gd.start()

	# join progress
	progress.http.active = False
	progress.http.Thread_hosting.join()

	if phaenotyp.calculation_type != "geometrical":
		basics.view_vertex_colors()

def ranking():
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]

	print_data("go to selected ranking")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	ranking_pos = phaenotyp.ranking

	data = scene["<Phaenotyp>"]
	# turns ga off, if user interrupted the process
	data["process"]["genetetic_mutation_update_post"] = False

	environment = data["environment"]
	individuals = data["individuals"]

	# sort by fitness
	list_result = []
	for name, individual in individuals.items():
		list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

	sorted_list = sorted(list_result, key = lambda x: x[2])
	ranked_indiviual = sorted_list[ranking_pos]

	text = str(ranking_pos) + ". ranked with fitness: " + str(ranked_indiviual[2])
	print_data(text)

	frame_to_switch_to = int(ranked_indiviual[0])

	bpy.context.scene.frame_current = frame_to_switch_to

def render_animation():
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]

	environment = data["environment"]
	individuals = data["individuals"]

	print_data("render animation")

	# change engine, shading
	bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
	bpy.context.scene.display.shading.light = 'FLAT'
	bpy.context.scene.display.shading.color_type = 'VERTEX'

	# set background to transparent
	bpy.context.scene.render.film_transparent = True

	# use stamp
	bpy.context.scene.render.use_stamp = True
	bpy.context.scene.render.use_stamp_note = True
	bpy.context.scene.render.stamp_note_text = ""
	bpy.context.scene.render.stamp_background[3] = 1
	bpy.context.scene.render.stamp_background = (0, 0, 0, 1)

	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	# render all indiviuals
	image_id = 0 # to sort images by fitness in filemanager
	amount_of_digts = len(str(len(individuals))) # write in format 01, 001 or 0001 ...

	# sort by fitness
	list_result = []
	for name, individual in individuals.items():
		list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

	sorted_list = sorted(list_result, key = lambda x: x[2])

	for frame, chromosome, fitness in sorted_list:
		str_image_id = str(image_id).zfill(amount_of_digts)
		filename = directory + "/Phaenotyp-ga_animation/image_id_" + str_image_id + "-individual_" + str(frame)

		# get text from chromosome
		str_chromosome = "["
		for gene in chromosome:
			str_chromosome += str(round(gene, 3))
			str_chromosome += ", "
		str_chromosome[-1]
		str_chromosome += "]"

		# set note
		text = filename + " -> " + str_chromosome + " fitness " + str(fitness)
		bpy.context.scene.render.stamp_note_text = text

		# set path and render
		bpy.context.scene.render.filepath = filename
		bpy.context.scene.render.image_settings.file_format='PNG'
		bpy.context.scene.render.filepath=filename
		bpy.ops.render.render(write_still=1)

		# update scene
		bpy.context.scene.frame_current = int(frame)
		bpy.context.view_layer.update()

		image_id += 1

	print_data("render animation - done")

def text():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	print_data("Generate output at the selected point")
	data["texts"] = []
	selected_objects = bpy.context.selected_objects

	# get selected vertex
	bpy.ops.object.mode_set(mode="OBJECT")
	for vertex in bpy.context.active_object.data.vertices:
		if vertex.select == True:
			# continue with this vertex:
			# (only one is selected)
			vertex_id = vertex.index
			bpy.ops.object.mode_set(mode="EDIT")

			# get member
			for id, member in members.items():
				if phaenotyp.calculation_type != "force_distribution":
					for position in range(11):
						if member["mesh_vertex_ids"][position] == vertex_id:
							data_temp = []
							# get member id
							text = "Member: " + id
							data_temp.append(text)

							# get Position
							text = "Position: " + str(position)
							data_temp.append(text)

							# get frame
							frame = bpy.context.scene.frame_current

							# get Do and Di
							text = "Do: " + str(round(member["Do"][str(frame)], 3))
							data_temp.append(text)
							text = "Di: " + str(round(member["Di"][str(frame)], 3))
							data_temp.append(text)

							# results
							text = "axial: " + str(round(member["axial"][str(frame)][position], 3))
							data_temp.append(text)
							text = "moment_y: " + str(round(member["moment_y"][str(frame)][position], 3))
							data_temp.append(text)
							text = "moment_z: " + str(round(member["moment_z"][str(frame)][position], 3))
							data_temp.append(text)
							text = "shear_y: " + str(round(member["shear_y"][str(frame)][position], 3))
							data_temp.append(text)
							text = "shear_z: " + str(round(member["shear_z"][str(frame)][position], 3))
							data_temp.append(text)
							text = "torque: " + str(round(member["torque"][str(frame)][position], 3))
							data_temp.append(text)

							text = "long_stress: " + str(round(member["long_stress"][str(frame)][position], 3))
							data_temp.append(text)
							text = "tau_shear: " + str(round(member["tau_shear"][str(frame)][position], 3))
							data_temp.append(text)
							text = "tau_torsion: " + str(round(member["tau_torsion"][str(frame)][position], 3))
							data_temp.append(text)
							text = "sum_tau: " + str(round(member["sum_tau"][str(frame)][position], 3))
							data_temp.append(text)
							text = "sigmav: " + str(round(member["sigmav"][str(frame)][position], 3))
							data_temp.append(text)
							text = "sigma: " + str(round(member["sigma"][str(frame)][position], 3))
							data_temp.append(text)

							# leverarm
							text = "leverarm: " + str(round(member["lever_arm"][str(frame)][position], 3))
							data_temp.append(text)

							# overstress
							text = "overstress: " + str(round(member["overstress"][str(frame)], 3))
							data_temp.append(text)

							data["texts"] = data_temp

				else:
					for position in range(2):
						if member["mesh_vertex_ids"][position] == vertex_id:
							data_temp = []
							# get member id
							text = "Member: " + id
							data_temp.append(text)

							# get frame
							frame = bpy.context.scene.frame_current

							# get Do and Di
							text = "Do: " + str(round(member["Do"][str(frame)], 3))
							data_temp.append(text)
							text = "Di: " + str(round(member["Di"][str(frame)], 3))
							data_temp.append(text)

							# results
							text = "axial: " + str(round(member["axial"][str(frame)], 3))
							data_temp.append(text)

							text = "sigma: " + str(round(member["sigma"][str(frame)], 3))
							data_temp.append(text)

							# leverarm
							text = "utilization: " + str(round(member["utilization"][str(frame)], 3))
							data_temp.append(text)

							# overstress
							text = "overstress: " + str(round(member["overstress"][str(frame)], 3))
							data_temp.append(text)

							data["texts"] = data_temp

def selection():
	print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	print_data("Select edges by given key and value.")

	# get data from gui
	if phaenotyp.calculation_type == "force_distribution":
		key = phaenotyp.selection_key_fd
	else:
		key = phaenotyp.selection_key_pn

	compare = phaenotyp.selection_compare
	value = int(phaenotyp.selection_value)
	threshold = abs(int(phaenotyp.selection_threshold))
	value_min = value - threshold
	value_max = value + threshold

	# set obj active and switch mode
	obj.hide_set(False)
	bpy.context.view_layer.objects.active = obj
	
	# set edge for selection type and deselect
	bpy.ops.object.mode_set(mode="EDIT")
	bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
	bpy.ops.mesh.select_all(action='DESELECT')
	bpy.ops.object.mode_set(mode="OBJECT")

	# iterate edges
	edges = obj.data.edges

	if key == "id":
		for edge in edges:
			id = edge.index
			
			# is this edge a member?
			member = members.get(str(id))
			if member:
				if compare == "Equal":
					if value_min <= id <= value_max:
						edge.select = True
					else:
						edge.select = False

				if compare == "Greater":
					if id > value_min:
						edge.select = True
					else:
						edge.select = False

				if compare == "Less":
					if id < value_max:
						edge.select = True
					else:
						edge.select = False

	else:
		for edge in edges:
			id = edge.index
			# is this edge a member?
			member = members.get(str(id))
			if member:
				value = member[key][str(frame)]

				if compare == "Equal":
					if value_min <= value <= value_max:
						edge.select = True
					else:
						edge.select = False

				if compare == "Greater":
					if value > value_min:
						edge.select = True
					else:
						edge.select = False

				if compare == "Less":
					if value < value_max:
						edge.select = True
					else:
						edge.select = False

	# go into edit-mode and switch to wireframe
	bpy.ops.object.mode_set(mode="EDIT")
	bpy.context.space_data.shading.type = 'WIREFRAME'

def report_members():
	print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	try:
		os.mkdir(os.path.join(directory, "Phaenotyp-members"))
	except:
		pass

	directory += "/Phaenotyp-members/"

	report.copy_sorttable(directory)

	sorted_frames = basics.sorted_keys(members[list(members)[0]]["axial"])
	start = sorted_frames[0] # first frame (if user is changing start frame)
	end = sorted_frames[len(sorted_frames)-1]

	report.report_members(directory, frame)

	# open file
	file_to_open = directory + "/axial.html"
	webbrowser.open(file_to_open)

def report_frames():
	print_data("Generate report overview in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	try:
		os.mkdir(os.path.join(directory, "Phaenotyp-frames"))
	except:
		pass

	directory += "/Phaenotyp-frames/"

	report.copy_sorttable(directory)

	sorted_frames = basics.sorted_keys(members[list(members)[0]]["axial"])
	start = sorted_frames[0] # first frame (if user is changing start frame)
	end = sorted_frames[len(sorted_frames)-1]

	report.report_frames(directory, start, end)

	# open file
	file_to_open = directory + "/max_sigma.html"
	webbrowser.open(file_to_open)

def report_combined():
	print_data("Generate report overview in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	try:
		os.mkdir(os.path.join(directory, "Phaenotyp-combined"))
	except:
		pass

	directory += "/Phaenotyp-combined/"

	report.copy_sorttable(directory)

	sorted_frames = basics.sorted_keys(members[list(members)[0]]["axial"])
	start = sorted_frames[0] # first frame (if user is changing start frame)
	end = sorted_frames[len(sorted_frames)-1]

	report.report_combined(directory, start, end)

	# open file
	file_to_open = directory + "/sigma.html"
	webbrowser.open(file_to_open)

def report_chromosomes():
	print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	try:
		os.mkdir(os.path.join(directory, "Phaenotyp-chromosomes"))
	except:
		pass

	directory += "/Phaenotyp-chromosomes/"

	report.copy_sorttable(directory)
	report.report_chromosomes(directory)

	# open file
	file_to_open = directory + "/index.html"
	webbrowser.open(file_to_open)

def report_tree():
	print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	try:
		os.mkdir(os.path.join(directory, "Phaenotyp-tree"))
	except:
		pass

	directory += "/Phaenotyp-tree/"

	report.report_tree(directory)

	# open file
	file_to_open = directory + "/index.html"
	webbrowser.open(file_to_open)

def reset():
	print_data("reset phaenotyp")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	
	# make structure visible
	# try only because the object is maybe allready deleted
	try:
		data = scene["<Phaenotyp>"]
		obj = scene["<Phaenotyp>"]["structure"]
		obj.hide_set(False)
		
		# set active again to avoid missing panel
		bpy.context.view_layer.objects.active = obj
	except:
		pass
	
	# create / recreate data
	basics.create_data()

	# delete obj and meshes
	basics.delete_obj_if_existing("<Phaenotyp>support")
	basics.delete_mesh_if_existing("<Phaenotyp>support")

	basics.delete_obj_if_existing("<Phaenotyp>member")
	basics.delete_mesh_if_existing("<Phaenotyp>member")

	# delete collection
	basics.delete_col_if_existing("<Phaenotyp>")

	# change view back to solid ...
	basics.revert_vertex_colors()

	# change props
	phaenotyp.calculation_type = "-"
