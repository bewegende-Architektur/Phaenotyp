import bpy
import bmesh
import numpy as np
from math import radians
import itertools

import os
import webbrowser

from phaenotyp import basics, material, geometry, calculation, bf, ga, gd, bm, panel, report, nn

def curve_to_mesh_straight():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'CURVE':
			valid_selection = False

	if not valid_selection:
		text = ["Select multiple curves only."]
		basics.popup(lines = text)
	else:
		# join curves
		bpy.ops.object.join()

		# set resolution
		bpy.context.object.data.resolution_u = 1
		bpy.context.scene.phaenotyp.buckling_resolution = 1
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.curve.select_all(action='SELECT')
		bpy.ops.curve.spline_type_set(type='POLY')

		# convert
		bpy.ops.object.mode_set(mode='OBJECT')
		geometry.to_be_fixed = "curve_to_mesh"
		fix_structure()
		basics.print_data("Convert curve to mesh straight")

def curve_to_mesh_curved():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'CURVE':
			valid_selection = False

	if not valid_selection:
		text = ["Select multiple curves only."]
		basics.popup(lines = text)
	else:
		# join curves
		bpy.ops.object.join()

		# set resolution for buckling
		res = bpy.context.object.data.resolution_u
		bpy.context.scene.phaenotyp.buckling_resolution = res

		# convert
		bpy.ops.object.mode_set(mode='OBJECT')
		geometry.to_be_fixed = "curve_to_mesh"
		fix_structure()
		basics.print_data("Convert curve to mesh curved")

def meta_to_mesh():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'META':
			valid_selection = False

	if not valid_selection:
		text = ["Select multiple metaballs only."]
		basics.popup(lines = text)
	else:
		bpy.ops.object.convert(target='MESH')
		basics.print_data("Convert metaballs to mesh")
		set_structure()

def mesh_to_quads_simple():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'MESH':
			valid_selection = False

	# check if one mesh only
	if len(selected) != 1:
		valid_selection = False

	if not valid_selection:
		text = ["Select one mesh only."]
		basics.popup(lines = text)
	else:
		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.tris_convert_to_quads()

		basics.print_data("Mesh to quads simple")

def mesh_to_quads_complex():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'MESH':
			valid_selection = False

	# check if one mesh only
	if len(selected) != 1:
		valid_selection = False

	if not valid_selection:
		text = ["Select one mesh only."]
		basics.popup(lines = text)
	else:
		# like explained from Blender Secrets here:
		# https://www.youtube.com/watch?app=desktop&v=oP2Bl97AVT0
		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.mesh.select_all(action='SELECT')

		# try simple approach first
		bpy.ops.mesh.tris_convert_to_quads()

		# add crease to keep all edges sharp
		bpy.ops.transform.edge_crease(value=1, snap=False)

		# add subsurf
		bpy.ops.object.mode_set(mode = 'OBJECT')
		bpy.ops.object.subdivision_set(level=2, relative=False)

		# convert to mesh
		bpy.ops.object.convert(target='MESH')

		# delete crease again
		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.transform.edge_crease(value=-1, snap=False)

		basics.print_data("Mesh to quads complex")

def set_hull():
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp

	bpy.ops.object.mode_set(mode='OBJECT')

	selected = context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'MESH':
			valid_selection = False

	# check if one mesh only
	if len(selected) != 1:
		valid_selection = False

	if not valid_selection:
		text = ["Select one mesh only."]
		basics.popup(lines = text)
	else:
		obj = selected[0]
		scene["<Phaenotyp>fh_hull"] = obj
		text = obj.name_full + " set as hull"
		basics.print_data(text)

def set_path():
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp

	bpy.ops.object.mode_set(mode='OBJECT')

	selected = context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'CURVE':
			valid_selection = False

	# check if one mesh only
	if len(selected) != 1:
		valid_selection = False

	if not valid_selection:
		text = ["Select one curve only."]
		basics.popup(lines = text)
	else:
		obj = selected[0]
		scene["<Phaenotyp>fh_path"] = obj
		text = obj.name_full + " set as path"
		basics.print_data(text)

def from_hull():
	context = bpy.context
	scene = context.scene
	phaenotyp = scene.phaenotyp

	# get parameters
	fh_methode = phaenotyp.fh_methode
	fh_input_type = phaenotyp.fh_input_type

	w = phaenotyp.fh_w
	d = phaenotyp.fh_d
	h = phaenotyp.fh_h

	if fh_methode == "grid":
		o_x = phaenotyp.fh_o_x
		o_y = phaenotyp.fh_o_y
		o_z = phaenotyp.fh_o_z

	if fh_methode == "path":
		o_x = 0
		o_y = 0
		o_z = 0

	rot_z = radians(phaenotyp.fh_rot)

	amount = phaenotyp.fh_amount
	o_c = phaenotyp.fh_o_c

	w_list = bpy.context.scene.phaenotyp_fh_w
	d_list = bpy.context.scene.phaenotyp_fh_d
	h_list = bpy.context.scene.phaenotyp_fh_h

	# get objects
	hull = scene["<Phaenotyp>fh_hull"]
	if fh_methode == "path":
		path = scene["<Phaenotyp>fh_path"]

	# delete hull and path if exisiting
	for obj in bpy.data.objects:
		if "_<Phaenotyp>fh" in obj.name_full:
			basics.delete_obj_if_existing(obj.name_full)

	# copy structure
	copy = hull.copy()
	copy.data = copy.data.copy()
	copy.name = hull.name + "_<Phaenotyp>fh"
	bpy.context.collection.objects.link(copy)

	# copy modifiers
	hull.select_set(True)
	bpy.context.view_layer.objects.active = hull
	copy.select_set(True)
	bpy.ops.object.make_links_data(type='MODIFIERS')
	bpy.ops.object.select_all(action='DESELECT')

	# hide structure
	hull.hide_set(True)

	# work with copy from now on
	structure = copy

	# set structure active
	bpy.context.view_layer.objects.active = structure

	# apply rotation and scale
	bpy.ops.object.select_all(action='DESELECT')
	structure.select_set(True)
	bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

	# convert to mesh
	bpy.ops.object.convert(target='MESH')

	# set origin of hull to centre of bounds
	bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

	if fh_input_type == "even":
		# create cube
		bpy.ops.mesh.primitive_cube_add(
			size = 1,
			calc_uvs = True,
			enter_editmode = False,
			align = 'WORLD',
			location = [0,0,h/2],
			rotation = [0,0,0],
			scale = [1,1,1]
			)

		grid = context.selected_objects[0]

		# set and apply scale
		grid.dimensions = [w,d,h]
		bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

	if fh_input_type == "individual":
		# create lists to work with
		x_list = [0]
		y_list = [0]
		z_list = [0]

		lists = [[x_list, w_list], [y_list, d_list], [z_list, h_list]]

		for target_list, input_list in lists:
			for i, v in enumerate(input_list):
				# first entry
				if i == 0:
					target_list.append(v.item_value)

				# other entries
				else:
					prev_v = target_list[i]
					target_list.append(prev_v+v.item_value)

		# empty lists to store geometry
		verts = []
		edges = []
		faces = []

		# create cubes
		for x_i in range(len(x_list)-1):
			for y_i in range(len(y_list)-1):
				for z_i in range(len(z_list)-1):
					x = x_list[x_i]
					y = y_list[y_i]
					z = z_list[z_i]

					w = x_list[x_i+1] - x_list[x_i]
					d = y_list[y_i+1] - y_list[y_i]
					h = z_list[z_i+1] - z_list[z_i]

					l = len(verts)

					v_0 = (x,y,z)
					v_1 = (x+w,y,z)
					v_2 = (x+w,y+d,z)
					v_3 = (x,y+d,z)
					v_4 = (x,y,z+h)
					v_5 = (x+w,y,z+h)
					v_6 = (x+w,y+d,z+h)
					v_7 = (x,y+d,z+h)

					verts.append(v_0)
					verts.append(v_1)
					verts.append(v_2)
					verts.append(v_3)
					verts.append(v_4)
					verts.append(v_5)
					verts.append(v_6)
					verts.append(v_7)

					faces.append([l+0, l+1, l+2, l+3]) # bottom
					faces.append([l+4, l+5, l+6, l+7]) # top
					faces.append([l+0, l+3, l+7, l+4]) # side left
					faces.append([l+1, l+2, l+6, l+5]) # side right
					faces.append([l+2, l+3, l+7, l+6]) # back
					faces.append([l+0, l+1, l+5, l+4]) # front


		new_mesh = bpy.data.meshes.new('new_mesh')
		new_mesh.from_pydata(verts, edges, faces)
		new_mesh.update()

		new_obj = bpy.data.objects.new('new_object', new_mesh)
		bpy.context.collection.objects.link(new_obj)

		bpy.context.view_layer.objects.active = new_obj

		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.object.mode_set(mode = 'OBJECT')

		grid = new_obj

		# set origin to center
		grid.select_set(True)
		bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
		bpy.context.view_layer.update()

	# move grid to bottom of structure in z
	loc = structure.location
	bottom_of_structure = loc[2] - structure.dimensions[2]*0.5
	z_position_grid = grid.location[2] + bottom_of_structure
	grid.location[2] = z_position_grid + o_z

	# create modifiere
	if fh_methode == "grid":
		# move grid to center of structure in x and y
		grid.location[0] = loc[0] + o_x
		grid.location[1] = loc[1] + o_y

		# get highest dim and offset for x and y
		# max of x and y because the object is rotated in z-direction
		max_dim = max(structure.dimensions[0], structure.dimensions[1])
		offset = max_dim + 20

		array_x = grid.modifiers.new(name="<Phaenotyp>_array-x", type='ARRAY')
		array_x.fit_type = 'FIT_LENGTH'
		array_x.relative_offset_displace = [1,0,0]
		array_x.fit_length = offset
		array_x.use_merge_vertices = True

		array_y = grid.modifiers.new(name="<Phaenotyp>_array-y", type='ARRAY')
		array_y.fit_type = 'FIT_LENGTH'
		array_y.relative_offset_displace = [0,1,0]
		array_y.fit_length = offset
		array_y.use_merge_vertices = True

		array_z = grid.modifiers.new(name="<Phaenotyp>_array-z", type='ARRAY')
		array_z.fit_type = 'FIT_LENGTH'
		array_z.relative_offset_displace = [0,0,1]
		array_z.fit_length = structure.dimensions[2]+10
		array_z.use_merge_vertices = True

		bpy.ops.object.convert(target='MESH')

		# set to center
		grid.location[0] -= grid.dimensions[0] * 0.5
		grid.location[1] -= grid.dimensions[1] * 0.5

		# set origin to centre of bounds
		bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

	if fh_methode == "path":
		array_x = grid.modifiers.new(name="<Phaenotyp>_array-x", type='ARRAY')
		array_x.fit_type = 'FIT_CURVE'
		array_x.curve = path
		array_x.relative_offset_displace = [1,0,0]
		array_x.use_merge_vertices = True

		array_y = grid.modifiers.new(name="<Phaenotyp>_array-x", type='ARRAY')
		array_y.fit_type = 'FIXED_COUNT'
		array_y.count = amount
		array_y.relative_offset_displace = [0,1,0]
		array_y.use_merge_vertices = True

		array_z = grid.modifiers.new(name="<Phaenotyp>_array-z", type='ARRAY')
		array_z.fit_type = 'FIT_LENGTH'
		array_z.fit_length = structure.dimensions[2]+10
		array_z.relative_offset_displace = [0,0,1]
		array_z.use_merge_vertices = True

		path.select_set(False)
		grid.select_set(True)
		bpy.context.view_layer.objects.active = grid
		bpy.ops.object.convert(target='MESH')

		# curve modifier
		curve = grid.modifiers.new(name="<Phaenotyp>_curve", type='CURVE')
		curve.object = path

	if fh_methode == "grid":
		# rotate grid z
		grid.rotation_euler[2] = rot_z

	if fh_methode == "path":
		# set origin of path to center
		bpy.context.scene.cursor.location = [0,0,0]
		path.select_set(True)
		bpy.context.view_layer.objects.active = path
		bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

		# set radius of all points to 1
		for pt in path.data.splines[0].points:
			pt.radius = 1

		# move to match path
		if fh_input_type == "even":
			grid.location[1] -= amount*d/2
		if fh_input_type == "individual":
			d = y_list[len(y_list)-1]
			grid.location[1] -= amount*d/2

		grid.location[1] += o_c

		# apply rotation
		bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

		# convert to mesh
		path.select_set(False)
		grid.select_set(True)
		bpy.context.view_layer.objects.active = grid
		bpy.ops.object.convert(target='MESH')

	# select all in structure edit-mode
	bpy.ops.object.select_all(action='DESELECT')
	grid.select_set(True)
	bpy.context.view_layer.objects.active = grid
	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_mode(type="VERT")
	bpy.ops.mesh.select_all(action = 'SELECT')
	bpy.ops.object.mode_set(mode = 'OBJECT')

	bpy.ops.object.select_all(action='DESELECT')
	structure.select_set(True)
	bpy.context.view_layer.objects.active = structure
	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_mode(type="VERT")
	bpy.ops.mesh.select_all(action = 'DESELECT')
	bpy.ops.object.mode_set(mode = 'OBJECT')

	# join cube and structure
	grid.select_set(True)
	structure.select_set(True)
	bpy.ops.object.join()

	# select array of cube only
	bpy.ops.object.mode_set(mode = 'EDIT')
	#bpy.ops.mesh.select_all(action='INVERT')

	# intersect array with structre
	bpy.ops.mesh.intersect_boolean()

	# keep columns and layers only
	faces = structure.data.polygons
	bpy.context.view_layer.objects.active = structure

	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_mode(type="FACE")
	bpy.ops.mesh.select_all(action='DESELECT')

	bpy.ops.object.mode_set(mode = 'OBJECT')

	for face in faces:
		if round(face.normal[0], 3) == 0: # round for threshold
			if round(face.normal[1], 3) == 0:
				if round(face.normal[2], 3) in [1,-1]:
					face.select = True

	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_all(action='INVERT')
	bpy.ops.mesh.delete(type='ONLY_FACE')
	bpy.ops.object.mode_set(mode = 'OBJECT')

	# get area
	area = geometry.area(faces)
	scene["<Phaenotyp>fh_area"] = area

	text = "Structure from hull created with area " + str(round(area,2)) + " m²"
	basics.print_data(text)

def automerge():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'MESH':
			valid_selection = False

	# check if one mesh only
	if len(selected) != 1:
		valid_selection = False

	if not valid_selection:
		text = ["Select one mesh only."]
		basics.popup(lines = text)
	else:
		scene = bpy.context.scene
		tool_settings = scene.tool_settings

		# get current settings
		bpy.ops.object.mode_set(mode = 'EDIT')
		current_automerge = tool_settings.use_mesh_automerge
		current_am_split = tool_settings.use_mesh_automerge_and_split
		current_double_threshold = tool_settings.double_threshold

		# toggle to automerge and split
		bpy.context.scene.tool_settings.use_mesh_automerge = True
		bpy.context.scene.tool_settings.use_mesh_automerge_and_split = True
		bpy.context.scene.tool_settings.double_threshold = 0.001

		# move to trigger automerge and split
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.transform.translate(
			value=(0, 0, 1), orient_type='GLOBAL',
			orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
			orient_matrix_type='GLOBAL',
			constraint_axis=(False, False, True),
			mirror=True, use_proportional_edit=False,
			proportional_edit_falloff='SMOOTH',
			proportional_size=1, use_proportional_connected=False,
			use_proportional_projected=False, snap=False,
			snap_elements={'INCREMENT'}, use_snap_project=False,
			snap_target='CLOSEST', use_snap_self=True,
			use_snap_edit=True, use_snap_nonedit=True,
			use_snap_selectable=False
			)

		#  alt_navigation=True excluded to work with blender 3 also

		# move to original position
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.transform.translate(
			value=(0, 0, -1), orient_type='GLOBAL',
			orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
			orient_matrix_type='GLOBAL',
			constraint_axis=(False, False, True),
			mirror=True, use_proportional_edit=False,
			proportional_edit_falloff='SMOOTH',
			proportional_size=1, use_proportional_connected=False,
			use_proportional_projected=False, snap=False,
			snap_elements={'INCREMENT'}, use_snap_project=False,
			snap_target='CLOSEST', use_snap_self=True,
			use_snap_edit=True, use_snap_nonedit=True,
			use_snap_selectable=False
			)

		#  alt_navigation=True excluded to work with blender 3 also

		# reset settings
		tool_settings.use_mesh_automerge = current_automerge
		tool_settings.use_mesh_automerge_and_split = current_am_split
		tool_settings.double_threshold = current_double_threshold

def union():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'MESH':
			valid_selection = False

	# check if one mesh only
	if len(selected) != 1:
		valid_selection = False

	if not valid_selection:
		text = ["Select one mesh only."]
		basics.popup(lines = text)
	else:
		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.intersect_boolean(
			operation = 'UNION',
			solver = 'EXACT',
			use_swap = False,
			use_self = True,
			threshold = 0.000001
			)

def simplify_edges():
	bpy.ops.object.mode_set(mode='OBJECT')

	selected = bpy.context.selected_objects

	# check if curves are selected
	valid_selection = True
	for obj in selected:
		if obj.type != 'MESH':
			valid_selection = False

	# check if one mesh only
	if len(selected) != 1:
		valid_selection = False

	if not valid_selection:
		text = ["Select one mesh only."]
		basics.popup(lines = text)
	else:
		obj = selected[0]
		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.mesh.select_all(action='DESELECT')

		me = bpy.context.object.data
		bm = bmesh.from_edit_mesh(me)

		linked_with_two_edges = lambda v: len(v.link_edges) == 2
		for vertex in bm.verts:
			vertex.select = linked_with_two_edges(vertex)
		bmesh.update_edit_mesh(me)

		bpy.ops.mesh.dissolve_verts()

def set_structure():
	context = bpy.context
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp

	bpy.ops.object.mode_set(mode='OBJECT')

	selected_objects = context.selected_objects
	obj = context.active_object

	basics.print_data("set structure")

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
				data = scene.get("<Phaenotyp>")
				if data:
					scene_id = data["scene_id"]
					basics.delete_col_if_existing("<Phaenotyp>" + str(scene_id))

				basics.create_data()
				data = scene["<Phaenotyp>"]
				scene_id = data["scene_id"]
				collection = bpy.data.collections.new("<Phaenotyp>" + str(scene_id))
				bpy.context.scene.collection.children.link(collection)
				geometry.to_be_fixed = None
				data["structure"] = obj

				# check for scipy
				calculation.check_scipy()

				# create meshes at this point allready
				# this is necessary to avoid a missing mesh if no members or no quads are created
				members = scene["<Phaenotyp>"]["members"]
				quads = scene["<Phaenotyp>"]["quads"]
				geometry.create_members(obj, members)
				geometry.create_quads(obj, quads)

				# set obj active
				bpy.context.view_layer.objects.active = obj

				# change to face selection for force_distribution
				if phaenotyp.calculation_type == "force_distribution":
					bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')

def fix_structure():
	if geometry.to_be_fixed == "seperate_by_loose":
		basics.print_data("Seperate by loose parts")
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.mesh.separate(type='LOOSE')
		bpy.ops.object.mode_set(mode='OBJECT')

	elif geometry.to_be_fixed == "curve_to_mesh":
		basics.print_data("Try to convert the curves to mesh")
		bpy.ops.object.mode_set(mode="OBJECT")
		bpy.ops.object.join()
		res = bpy.context.object.data.resolution_u
		bpy.context.scene.phaenotyp.buckling_resolution = res
		bpy.ops.object.convert(target='MESH')
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.object.mode_set(mode='OBJECT')

	elif geometry.to_be_fixed == "meta_to_mesh":
		basics.print_data("Try to convert meta to mesh")
		bpy.ops.object.mode_set(mode="OBJECT")
		bpy.ops.object.convert(target='MESH')

	elif geometry.to_be_fixed == "delete_loose":
		basics.print_data("Delete loose parts")
		bpy.ops.object.mode_set(mode="EDIT")
		bpy.ops.mesh.delete_loose()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.remove_doubles()
		bpy.ops.object.mode_set(mode='OBJECT')

	elif geometry.to_be_fixed == "triangulate":
		basics.print_data("triangulate")
		bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
		bpy.ops.mesh.select_all(action='DESELECT')

	elif geometry.to_be_fixed == "remove_doubles":
		basics.print_data("Remove doubles")
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
	scene_id = data["scene_id"]

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
				basics.delete_obj_if_existing("<Phaenotyp>support_" + str(scene_id))
				basics.delete_mesh_if_existing("<Phaenotyp>support_" + str(scene_id))

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
			basics.delete_obj_if_existing("<Phaenotyp>support_" + str(scene_id))
			basics.delete_mesh_if_existing("<Phaenotyp>support_" + str(scene_id))

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
	scene_id = data["scene_id"]
	obj = data["structure"]
	nodes = data["nodes"]
	frame = bpy.context.scene.frame_current

	bpy.ops.object.mode_set(mode="OBJECT")

	# create new member for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		for edge in obj.data.edges:
			vertex_0_id = edge.vertices[0]
			vertex_1_id = edge.vertices[1]

			if edge.select:
				id = edge.index

				# create empty node to track which nodes are used
				# infos like thickness and others can be stored too later
				for node_id in [vertex_0_id, vertex_1_id]:
					node = nodes.get(str(node_id))
					if not node:
						nodes[str(node_id)] = {}

				member = {}

				# this variables are always fix
				member["vertex_0_id"] = vertex_0_id # equals id of vertex
				member["vertex_1_id"] = vertex_1_id # equals id of vertex

				member["profile_type"] = "round_hollow"
				member["orientation"] = phaenotyp.member_orientation
				member["member_type"] = phaenotyp.member_type
				member["buckling_resolution"] = phaenotyp.buckling_resolution
				member["orientation"] = phaenotyp.member_orientation

				member["acceptable_sigma"] = material.current["acceptable_sigma"] # from gui
				member["acceptable_shear"] = material.current["acceptable_shear"] # from gui
				member["acceptable_torsion"] = material.current["acceptable_torsion"] # from gui
				member["knick_model"] = material.current["knick_model"] # from gui

				member["material_name"] = material.current["material_name"]
				member["E"] = material.current["E"] # from gui
				member["G"] = material.current["G"] # from gui
				member["rho"] = material.current["rho"] # from gui

				member["height"] = {}
				member["width"] = {}
				member["wall_thickness"] = {}

				member["height_first"] = material.current["height"] # from gui
				member["width_first"] = material.current["width"] # from gui
				member["wall_thickness_first"] = material.current["wall_thickness"] # from fui

				member["profile"] = {}
				member["profile_first"] = material.current["profile"] # from gui

				member["angle"] = {}
				member["angle_first"] = material.current["angle"] # from gui

				member["Iy"] = {}
				member["Iz"] = {}
				member["J"] = {}
				member["A"] = {}
				member["weight_A"] = {}
				member["ir_y"] = {}
				member["ir_z"] = {}

				member["Iy_first"] = material.current["Iy"] # from gui
				member["Iz_first"] = material.current["Iz"] # from gui
				member["J_first"] = material.current["J"] # from gui
				member["A_first"] = material.current["A"] # from gui
				member["weight_first"] = material.current["weight_A"] # from gui
				member["ir_y_first"] = material.current["ir_y"] # from gui
				member["ir_z_first"] = material.current["ir_z"] # from gui

				# results
				member["axial"] = {}
				member["moment_y"] = {}
				member["moment_z"] = {}
				member["moment_h"] = {}
				member["shear_y"] = {}
				member["shear_z"] = {}
				member["torque"] = {}
				member["sigma"] = {}

				member["Wy"] = {}
				member["Wz"] = {}

				member["long_stress"] = {}
				member["tau_shear_y"] = {}
				member["tau_shear_z"] = {}
				member["tau_torsion"] = {}
				member["sum_tau"] = {}
				member["sigma"] = {}
				member["max_long_stress"] = {}
				member["max_tau_shear_y"] = {}
				member["max_tau_shear_z"] = {}
				member["max_tau_torsion"] = {}
				member["max_sum_tau"] = {}
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

				member["weight"] = {}
				member["length"] = {}

				data["members"][str(id)] = member

	# create new member for fd
	else:
		for edge in obj.data.edges:
			vertex_0_id = edge.vertices[0]
			vertex_1_id = edge.vertices[1]

			if edge.select:
				id = edge.index

				# create empty node to track which nodes are used
				# infos like thickness and others can be stored too later
				for node_id in [vertex_0_id, vertex_1_id]:
					node = nodes.get(str(node_id))
					if not node:
						nodes[str(node_id)] = {}

				member = {}

				# this variables are always fix
				member["name"] = "member_" + str(id) # equals edge-id
				member["vertex_0_id"] = vertex_0_id # equals id of vertex
				member["vertex_1_id"] = vertex_1_id # equals id of vertex

				member["acceptable_sigma"] = material.current["acceptable_sigma"] # from gui

				member["E"] = material.current["E"] # from gui
				member["G"] = material.current["G"] # from gui
				member["rho"] = material.current["rho"] # from gui

				# this variables can change per frame
				# the key "first" is used to store the user-input of each member
				# this is importand, if a user is chaning the frame during the
				# input for some reason
				member["profile_type"] = phaenotyp.profile_type

				member["height"] = {}
				member["width"] = {}
				member["wall_thickness"] = {}

				member["height_first"] = material.current["height"] # from gui
				member["width_first"] = material.current["height"] # width == height for pipes
				member["wall_thickness_first"] = material.current["wall_thickness"] # from gui

				member["profile"] = {}
				member["profile_first"] = None

				member["angle"] = {}
				member["angle_first"] = phaenotyp.member_angle

				member["Iy"] = {}
				member["Iz"] = {}
				member["J"] = {}
				member["A"] = {}
				member["weight_A"] = {}
				member["ir"] = {} # ----> Überall berücksichtigen

				member["Iy_first"] = material.current["Iy"] # from gui
				member["Iz_first"] = material.current["Iz"] # from gui
				member["J_first"] = material.current["J"] # from gui
				member["A_first"] = material.current["A"] # from gui
				member["weight_first"] = material.current["weight_A"] # from gui
				member["ir_first"] = material.current["ir_y"] # from gui -> only ir_y for fd

				# results
				member["axial"] = {}
				member["sigma"] = {}

				member["initial_positions"] = {}
				member["deflection"] = {}
				member["overstress"] = {}
				member["utilization"] = {}

				member["weight"] = {}
				member["length"] = {}

				data["members"][str(id)] = member

	# delete obj if existing
	basics.delete_obj_if_existing( "<Phaenotyp>members_" + str(scene_id))
	basics.delete_mesh_if_existing( "<Phaenotyp>members_" + str(scene_id))

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
	scene_id = data["scene_id"]
	obj = data["structure"]
	nodes = data["nodes"]
	frame = bpy.context.scene.frame_current

	bpy.ops.object.mode_set(mode="OBJECT")

	# this operator is only working for PyNite
	# it is only called in this calculation_type
	for face in obj.data.polygons:
		if face.select:
			id = face.index
			vertices_ids = face.vertices

			# create empty node to track which nodes are used
			# infos like thickness and others can be stored too later
			for node_id in vertices_ids:
				node = nodes.get(str(node_id))
				if not node:
					nodes[str(node_id)] = {}

			quad = {}

			# this variables are always fix
			quad["vertices_ids_structure"] = vertices_ids # structure obj
			quad["vertices_ids_viz"] = {} # obj for visualization
			quad["face_id_viz"] = None
			quad["stresslines_viz"] = None

			quad["E"] = material.current_quads["E"] # from gui
			quad["G"] = material.current_quads["G"] # from gui
			quad["nu"] = material.current_quads["nu"] # from gui
			quad["rho"] = material.current_quads["rho"] # from gui

			quad["acceptable_sigma"] = material.current_quads["acceptable_sigma"] # from gui
			quad["acceptable_shear"] = material.current_quads["acceptable_shear"] # from gui
			quad["acceptable_sigmav"] = material.current_quads["acceptable_sigmav"] # from gui
			quad["knick_model"] = material.current_quads["knick_model"] # from gui

			quad["thickness"] = {}
			quad["thickness_first"] = phaenotyp.thickness # from gui

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

			quad["weight_A"] = {}
			quad["area"] = {}
			quad["weight"] = {}

			quad["length_x"] = {} # average length of quad in x-direction
			quad["length_y"] = {} # average length of quad in y-direction

			quad["ir"] = {}
			quad["A"] = {} # area of the section, not the face
			quad["J"] = {}
			quad["Wy"] = {}
			#quad["moment_h"] = {}
			#quad["long_stress"] = {}
			#quad["shear_h"] = {}
			#quad["tau_shear"] = {}
			quad["sigmav"] = {}
			#quad["sigma"] = {}
			quad["acceptable_sigma_buckling"] = {}
			quad["lamda"] = {}

			quad["s_x_1"] = {}
			quad["s_x_2"] = {}
			quad["s_y_1"] = {}
			quad["s_y_2"] = {}
			quad["T_xy_1"] = {}
			quad["T_xy_2"] = {}

			quad["s_1_1"] = {}
			quad["s_1_2"] = {}
			quad["s_2_1"] = {}
			quad["s_2_2"] = {}

			quad["alpha_1"] = {}
			quad["alpha_2"] = {}

			#quad["strain_energy"] = {}
			#quad["normal_energy"] = {}
			#quad["moment_energy"] = {}

			data["quads"][str(id)] = quad

	# delete obj if existing
	basics.delete_obj_if_existing("<Phaenotyp>quads_" + str(scene_id))
	basics.delete_mesh_if_existing("<Phaenotyp>quads_" + str(scene_id))

	basics.delete_obj_if_existing("<Phaenotyp>stresslines_" + str(scene_id))
	basics.delete_mesh_if_existing("<Phaenotyp>stresslines_" + str(scene_id))

	# create one mesh for all
	geometry.create_quads(data["structure"], data["quads"])
	geometry.create_stresslines(data["structure"], data["quads"])

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
	scene_id = data["scene_id"]
	nodes = data["nodes"]
	members = data["members"]
	quads = data["quads"]
	obj = data["structure"]

	calculation_type = phaenotyp.calculation_type

	# create load
	#bpy.ops.object.mode_set(mode="OBJECT") # <---- to avoid "out-of-range-error" on windows
	bpy.ops.object.mode_set(mode="EDIT") # <---- to avoid "out-of-range-error" on windows
	bpy.ops.object.mode_set(mode="OBJECT") # <---- to avoid "out-of-range-error" on windows

	# pass user input to data
	if phaenotyp.load_type == "vertices":
		# loads can only be applied to existing nodes, members and quads
		possible = True
		for vertex in obj.data.vertices:
			if vertex.select:
				id = vertex.index
				if str(id) not in nodes:
					possible = False
					break

		if possible == False:
			text = ["Loads can only be applied nodes that are part of members or quads."]
			basics.popup(lines = text)

		# apply loads
		else:
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
		# loads can only be applied to existing nodes, members and quads
		possible = True
		for edge in obj.data.edges:
			if edge.select:
				id = edge.index
				if str(id) not in members:
					possible = False
					break

		if possible == False:
			text = ["Loads of type edge can only be applied to Members of the structure."]
			basics.popup(lines = text)

		# apply loads
		else:
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
		# check if quad is available
		possible = True
		for face in obj.data.polygons:
			if face.select:
				id = face.index
				if str(id) not in quads:
					possible = False
					break

		# if not possible for quads
		if possible == False:
			# check if edges are available
			possible = True
			for face in obj.data.polygons:
				if face.select:
					edge_keys = face.edge_keys
					for key in edge_keys:
						for edge in obj.data.edges:
							v_0 = edge.vertices[0]
							v_1 = edge.vertices[1]
							if key[0] == v_0 and key[1] == v_1:
								id = edge.index
								if str(id) not in members:
									possible = False
									break

							if key[1] == v_0 and key[0] == v_1:
								id = edge.index
								if str(id) not in members:
									possible = False
									break


		# needs to be possible for fd
		if calculation_type == "force_distribution":
			possible = True

		if possible == False:
			text = ["Loads of type face can only be applied to Members or quads within the structure."]
			basics.popup(lines = text)

		# apply loads
		else:
			for face in obj.data.polygons:
				if face.select:
					id = face.index
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
	basics.delete_obj_if_name_contains("<Phaenotyp>load_" + str(scene_id))

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

	# create temp dictionaries
	basics.models = {}
	basics.feas = {}

	# calculate frames
	calculation.calculate_frames(frame, frame+1)

	# update view
	basics.jobs.append([basics.view_vertex_colors])

	# print done
	basics.jobs.append([basics.print_data, "done"])

	# calculate new visualization-mesh
	basics.jobs.append([geometry.update_geometry_post])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()

def calculate_animation():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	quads = scene["<Phaenotyp>"]["quads"]
	frame = bpy.context.scene.frame_current

	# create temp dictionaries
	basics.models = {}
	basics.feas = {}

	# show wireframe to see progress
	basics.view_wireframe()

	# get start and end of frames
	start = bpy.context.scene.frame_start
	end = bpy.context.scene.frame_end + 1 # to render also last frame

	# if optimizaiton
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
		# for each
		if phaenotyp.animation_optimization_type == "each_frame":
			# calculate frames
			calculation.calculate_frames(start, end)

			for i in range(phaenotyp.optimization_amount):
				# optimize each frame
				for frame in range(start, end):
					basics.jobs.append([calculation.sectional_optimization, frame])

				# calculate frames again
				calculation.calculate_frames(start, end)

		# gradient
		if phaenotyp.animation_optimization_type == "gradient":
			frame = start
			# calculate first frame
			calculation.calculate_frames(frame, frame+1)

			for i in range(phaenotyp.optimization_amount):
				frame += 1

				# copy previous settings
				basics.jobs.append([calculation.copy_d_t_from_prev, frame])

				# optimize
				basics.jobs.append([calculation.sectional_optimization, frame])

				# calculate frame again
				calculation.calculate_frames(frame, frame+1)

			bpy.context.scene.frame_start = start
			bpy.context.scene.frame_end = phaenotyp.optimization_amount+1


	# without optimization
	else:
		# calculate frames
		calculation.calculate_frames(start, end)

	# update view
	basics.jobs.append([basics.view_vertex_colors])

	# print done
	basics.jobs.append([basics.print_data, "done"])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()

def optimize_members():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	opt_type = phaenotyp.optimization_pn
	
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current
	
	text = "sectional performance " + str(opt_type)
	basics.print_data(text)

	# create temp dictionaries
	basics.models = {}
	basics.feas = {}

	# calculate new section
	if opt_type == "none": basics.jobs.append([calculation.optimize_members_rotation])
	if opt_type == "pipes": basics.jobs.append([calculation.utilization_members_pipes])
	if opt_type == "rect": basics.jobs.append([calculation.utilization_members_rect])
	if opt_type == "profiles": basics.jobs.append([calculation.utilization_members_profiles])
	if opt_type == "auto": basics.jobs.append([calculation.utilization_members_auto])

	# calculate frame
	calculation.calculate_frames(frame, frame+1)

	# calculate new visualization-mesh
	basics.jobs.append([geometry.update_geometry_post])

	# update view
	basics.jobs.append([basics.view_vertex_colors])

	# print done
	basics.jobs.append([basics.print_data, "done"])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()

def optimize_approximate():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	frame = bpy.context.scene.frame_current

	basics.print_data("sectional performance approximate")

	# reset temp dictionaries
	basics.models = {}
	basics.feas = {}

	# adjust sections and recalc current frame
	basics.jobs.append([calculation.approximate_sectional])
	calculation.calculate_frames(frame, frame+1)

	# update visualization
	basics.jobs.append([geometry.update_geometry_post])
	basics.jobs.append([basics.view_vertex_colors])
	basics.jobs.append([basics.print_data, "done"])

	bpy.ops.wm.phaenotyp_jobs()

def quads_approximate_sectional():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	basics.print_data("quads approximate sectional performance")

	# create temp dictionaries
	basics.models = {}
	basics.feas = {}

	# calculate new section
	basics.jobs.append([calculation.quads_approximate_sectional])

	# calculate frame
	calculation.calculate_frames(frame, frame+1)

	# calculate new visualization-mesh
	basics.jobs.append([geometry.update_geometry_post])

	# update view
	basics.jobs.append([basics.view_vertex_colors])

	# print done
	basics.jobs.append([basics.print_data, "done"])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()

def quads_utilization_sectional():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = scene["<Phaenotyp>"]["members"]
	frame = bpy.context.scene.frame_current

	basics.print_data("quads utilization sectional performance")

	# create temp dictionaries
	basics.models = {}
	basics.feas = {}

	# calculate new section
	basics.jobs.append([calculation.quads_utilization_sectional])

	# calculate frame
	calculation.calculate_frames(frame, frame+1)

	# calculate new visualization-mesh
	basics.jobs.append([geometry.update_geometry_post])

	# update view
	basics.jobs.append([basics.view_vertex_colors])

	# print done
	basics.jobs.append([basics.print_data, "done"])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()

def topolgy_decimate():
	basics.print_data("Decimate topological performance")
	calculation.decimate_topology()

def topolgy_decimate_apply():
	basics.print_data("Applied topological performance")
	calculation.decimate_topology_apply()
	reset()

def bf_start():
	basics.print_data("Start bruteforce")

	# show wireframe to see progress
	basics.view_wireframe()

	bf.start()

def ga_start():
	basics.print_data("Start genetic mutation over selected shape keys")

	# show wireframe to see progress
	basics.view_wireframe()

	ga.start()

def gd_start():
	basics.print_data("Start gradient descent over selected shape keys")

	# show wireframe to see progress
	basics.view_wireframe()

	gd.start()

def bm_install():
	basics.print_data("Install libraries for baysian modelling")

	# show wireframe to see progress
	basics.view_wireframe()

	bm.install_bayes()
	
def bm_start():
	basics.print_data("Start bayesian modeling over selected shape keys")

	# show wireframe to see progress
	basics.view_wireframe()

	bm.start()
	
def get_boundaries():
	basics.print_data("get boundaries")

	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type
	members = data["members"]
	quads = data["quads"]

	start = scene.frame_start
	end = scene.frame_end

	lowest = 0
	highest = 0

	# get forces of members
	if phaenotyp.calculation_type != "force_distribution":
		force_type = phaenotyp.forces_pn

		for frame in range(start, end):
			for id in members:
				member = members[id]
				results = member[force_type].get(str(frame))
				if results:
					# if utilization in viz
					if force_type == "utilization":
						if results > highest:
							highest = results
						if results < lowest:
							lowest = results

					# for more than one entrie
					else:
						for result in results:
							if result > highest:
								highest = result
							if result < lowest:
								lowest = result

	else:
		force_type = phaenotyp.forces_fd
		for frame in range(start, end):
			for id in members:
				member = members[id]
				results = member[force_type].get(str(frame))
				if results:
					if results > highest:
						highest = results
					if results < lowest:
						lowest = results

	max_diff = basics.return_max_diff_to_zero([lowest, highest])
	if abs(max_diff) < 0.001:
		max_diff = 0.001 # to avoid diff zero
	phaenotyp.viz_boundaries_members = max_diff

	# get forces of quads
	lowest = 0
	highest = 0

	force_type = phaenotyp.forces_quads
	for frame in range(start, end):
		for id in quads:
			quad = quads[id]
			result_1 = quad[force_type + "_1"]
			results = result_1.get(str(frame))
			if results:
				if results > highest:
					highest = results
				if results < lowest:
					lowest = results

				result_2 = quad[force_type + "_2"]
				results = result_1.get(str(frame))

				if results > highest:
					highest = results
				if results < lowest:
					lowest = results

	max_diff = basics.return_max_diff_to_zero([lowest, highest])
	if abs(max_diff) < 0.001:
		max_diff = 0.001 # to avoid diff zero
	phaenotyp.viz_boundaries_quads = max_diff

def get_boundary_diagram():
	basics.print_data("get boundaries")

	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type
	individuals = data["individuals"]

	fitness = phaenotyp.diagram_fitness

	lowest = 0
	highest = 0

	# get forces of members
	if phaenotyp.calculation_type != "force_distribution":
		for id, individual in individuals.items():
			results = individual["fitness"][fitness]
			if results > highest:
				highest = results
			if results < lowest:
				lowest = results

	max_diff = basics.return_max_diff_to_zero([lowest, highest])
	if abs(max_diff) < 0.001:
		max_diff = 0.001 # to avoid diff zero
	phaenotyp.diagram_scale = 1 / max_diff

def ranking():
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]

	basics.print_data("go to selected ranking")

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
	basics.print_data(text)

	frame_to_switch_to = int(ranked_indiviual[0])

	bpy.context.scene.frame_current = frame_to_switch_to

def render_single_frame(id_entry):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]

	environment = data["environment"]
	individuals = data["individuals"]

	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	image_id, entry = id_entry
	frame, chromosome, fitness = entry
	amount_of_digts = len(str(len(individuals))) # write in format 01, 001 or 0001 ...

	str_image_id = str(image_id).zfill(amount_of_digts)
	filename = directory + "/Phaenotyp-fitness_animation/image_id_" + str_image_id + "-individual_" + str(frame)

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

	text = "image_id " + str(image_id) + " chromosome " + str_chromosome + " done"
	basics.print_data(text)

def render_animation():
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]

	environment = data["environment"]
	individuals = data["individuals"]

	basics.print_data("render animation")

	# # change engine, shading
	# bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
	# bpy.context.scene.display.shading.light = 'FLAT'
	# bpy.context.scene.display.shading.color_type = 'VERTEX'

	# # set background to transparent
	# bpy.context.scene.render.film_transparent = True

	# # use stamp
	# bpy.context.scene.render.use_stamp = True
	# bpy.context.scene.render.use_stamp_note = True
	# bpy.context.scene.render.stamp_note_text = ""
	# bpy.context.scene.render.stamp_background[3] = 1
	# bpy.context.scene.render.stamp_background = (0, 0, 0, 1)

	# render all indiviuals
	image_id = 0 # to sort images by fitness in filemanager

	# sort by fitness
	list_result = []
	for name, individual in individuals.items():
		list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

	sorted_list = sorted(list_result, key = lambda x: x[2])

	for entry in sorted_list:
		basics.jobs.append([render_single_frame, [image_id, entry]])
		image_id += 1

	# print done
	basics.jobs.append([basics.print_data, "done"])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()

def text():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]

	members = data["members"]
	quads = data["quads"]
	frame = bpy.context.scene.frame_current

	basics.print_data("Generate output at the selected point")
	data["texts"] = []
	selected_objects = bpy.context.selected_objects

	# get selected vertex
	bpy.ops.object.mode_set(mode="OBJECT")
	if selected_objects[0].name_full ==  "<Phaenotyp>members_" + str(scene_id):
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

								# get geometry
								text = "member_type: " + member["member_type"]
								data_temp.append(text)

								text = "profile_type: " + member["profile_type"]
								data_temp.append(text)
								
								if member["profile"][str(frame)]:
									text = "profile: " + member["profile"][str(frame)]
									data_temp.append(text)
																								
								text = "height: " + str(round(member["height"][str(frame)], 3)) + " cm"
								data_temp.append(text)
								text = "width: " + str(round(member["width"][str(frame)], 3)) + " cm"
								data_temp.append(text)
								if member["wall_thickness"][str(frame)]:
									text = "wall_thickness: " + str(round(member["wall_thickness"][str(frame)], 3)) + " cm"
									data_temp.append(text)

								# results
								text = "axial: " + str(round(member["axial"][str(frame)][position], 3)) + " kN"
								data_temp.append(text)
								text = "moment_y: " + str(round(member["moment_y"][str(frame)][position], 3)) + " kNcm"
								data_temp.append(text)
								text = "moment_z: " + str(round(member["moment_z"][str(frame)][position], 3)) + " kNcm"
								data_temp.append(text)
								text = "moment_h: " + str(round(member["moment_h"][str(frame)][position], 3)) + " kNcm"
								data_temp.append(text)
								text = "shear_y: " + str(round(member["shear_y"][str(frame)][position], 3)) + " kN"
								data_temp.append(text)
								text = "shear_z: " + str(round(member["shear_z"][str(frame)][position], 3)) + " kN"
								data_temp.append(text)
								text = "torque: " + str(round(member["torque"][str(frame)][position], 3)) + " kNcm"
								data_temp.append(text)

								text = "tau_shear_y: " + str(round(member["tau_shear_y"][str(frame)][position], 3)) + " kN/cm²"
								data_temp.append(text)
								text = "tau_shear_z: " + str(round(member["tau_shear_z"][str(frame)][position], 3)) + " kN/cm²"
								data_temp.append(text)
								text = "tau_torsion: " + str(round(member["tau_torsion"][str(frame)][position], 3)) + " kN/cm²"
								data_temp.append(text)
								text = "sum_tau: " + str(round(member["sum_tau"][str(frame)][position], 3)) + " kN/cm²"
								data_temp.append(text)
								
								text = "sigma: " + str(round(member["sigma"][str(frame)][position], 3)) + " kN/cm²"
								data_temp.append(text)

								text = "utilization: " + str(round(member["utilization"][str(frame)], 3))
								data_temp.append(text)

								text = "overstress: " + str(member["overstress"][str(frame)])
								data_temp.append(text)

								def_pos = member["initial_positions"][str(frame)][position][0] - member["deflection"][str(frame)][position][0]
								text = "deflection x: " + str(round(def_pos, 3))
								data_temp.append(text)

								def_pos = member["initial_positions"][str(frame)][position][1] - member["deflection"][str(frame)][position][1]
								text = "deflection y: " + str(round(def_pos, 3))
								data_temp.append(text)

								def_pos = member["initial_positions"][str(frame)][position][2] - member["deflection"][str(frame)][position][2]
								text = "deflection z: " + str(round(def_pos, 3))
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

								# get height and wall thickness
								text = "height: " + str(round(member["height"][str(frame)], 3)) + " cm"
								data_temp.append(text)
								text = "wall_thickness: " + str(round(member["wall_thickness"][str(frame)], 3)) + " cm"
								data_temp.append(text)

								# results
								text = "axial: " + str(round(member["axial"][str(frame)], 3)) + " kN"
								data_temp.append(text)

								text = "sigma: " + str(round(member["sigma"][str(frame)], 3)) + " kN/cm²"
								data_temp.append(text)

								text = "utilization: " + str(round(member["utilization"][str(frame)], 3))
								data_temp.append(text)

								text = "overstress: " + str(member["overstress"][str(frame)])
								data_temp.append(text)

								data["texts"] = data_temp

	if selected_objects[0].name_full ==  "<Phaenotyp>quads_" + str(scene_id):
		for face in bpy.context.active_object.data.polygons:
			if face.select == True:
				# continue with this face:
				# (only one is selected)
				face_id = face.index
				bpy.ops.object.mode_set(mode="EDIT")

				# get quad, only available in pynite
				for id, quad in quads.items():
					if (quad["vertices_ids_viz"][0] == face.vertices[0] and
						quad["vertices_ids_viz"][1] == face.vertices[1] and
						quad["vertices_ids_viz"][2] == face.vertices[2] and
						quad["vertices_ids_viz"][3] == face.vertices[3]):

						data_temp = []

						text = "Quad: " + id
						data_temp.append(text)

						# get frame
						frame = bpy.context.scene.frame_current

						# get info
						text = "thickness: " + str(round(quad["thickness"][str(frame)], 3))
						data_temp.append(text)

						#weight, area

						# get results
						text = "membrane_xy: " + str(round(quad["membrane_xy"][str(frame)], 3))
						data_temp.append(text)
						text = "membrane_x: " + str(round(quad["membrane_x"][str(frame)], 3))
						data_temp.append(text)
						text = "membrane_y: " + str(round(quad["membrane_y"][str(frame)], 3))
						data_temp.append(text)

						text = "moment_xy: " + str(round(quad["moment_xy"][str(frame)], 3))
						data_temp.append(text)
						text = "moment_x: " + str(round(quad["moment_x"][str(frame)], 3))
						data_temp.append(text)
						text = "moment_y: " + str(round(quad["moment_y"][str(frame)], 3))
						data_temp.append(text)

						text = "shear_x: " + str(round(quad["shear_x"][str(frame)], 3))
						data_temp.append(text)
						text = "shear_y: " + str(round(quad["shear_y"][str(frame)], 3))
						data_temp.append(text)

						text = "T_xy_1: " + str(round(quad["T_xy_1"][str(frame)], 3))
						data_temp.append(text)
						text = "T_xy_2: " + str(round(quad["T_xy_2"][str(frame)], 3))
						data_temp.append(text)

						text = "s_x_1: " + str(round(quad["s_x_1"][str(frame)], 3))
						data_temp.append(text)
						text = "s_x_2: " + str(round(quad["s_x_2"][str(frame)], 3))
						data_temp.append(text)

						text = "s_y_1: " + str(round(quad["s_y_1"][str(frame)], 3))
						data_temp.append(text)
						text = "s_y_2: " + str(round(quad["s_y_2"][str(frame)], 3))
						data_temp.append(text)

						text = "s_1_1: " + str(round(quad["s_1_1"][str(frame)], 3))
						data_temp.append(text)
						text = "s_2_1: " + str(round(quad["s_2_1"][str(frame)], 3))
						data_temp.append(text)

						text = "s_1_2: " + str(round(quad["s_1_2"][str(frame)], 3))
						data_temp.append(text)
						text = "s_2_2: " + str(round(quad["s_2_2"][str(frame)], 3))
						data_temp.append(text)

						text = "alpha_1: " + str(round(quad["alpha_1"][str(frame)], 3))
						data_temp.append(text)
						text = "alpha_2: " + str(round(quad["alpha_2"][str(frame)], 3))
						data_temp.append(text)

						data["texts"] = data_temp

def selection():
	basics.print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	members = data["members"]
	quads = data["quads"]
	frame = bpy.context.scene.frame_current

	basics.print_data("Select edges by given key and value.")

	obj.hide_set(False)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.mode_set(mode = 'OBJECT')

	# get data from gui
	if phaenotyp.calculation_type == "force_distribution":
		key = phaenotyp.selection_key_fd
	else:
		if phaenotyp.selection_type == "member":
			key = phaenotyp.selection_key_pn
		else:
			key = phaenotyp.selection_key_quads

	compare = phaenotyp.selection_compare
	#value = int(phaenotyp.selection_value)
	value = float(phaenotyp.selection_value)
	#threshold = abs(int(phaenotyp.selection_threshold))
	threshold = abs(float(phaenotyp.selection_threshold))
	value_min = value - threshold
	value_max = value + threshold

	# set obj active and switch mode
	obj.hide_set(False)
	bpy.context.view_layer.objects.active = obj

	# set type of selection and deselect
	bpy.ops.object.mode_set(mode="EDIT")
	if phaenotyp.selection_type == "member": # for members
		bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
	else: # for quads
		bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
	bpy.ops.mesh.select_all(action='DESELECT')
	bpy.ops.object.mode_set(mode="OBJECT")

	# for members
	if phaenotyp.selection_type == "member": # for members
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

	# for quads
	else:
		# iterate edges
		faces = obj.data.polygons

		if key == "id":
			for face in faces:
				id = face.index

				# is this edge a member?
				quad = quads.get(str(id))
				if quad:
					if compare == "Equal":
						if value_min <= id <= value_max:
							face.select = True
						else:
							face.select = False

					if compare == "Greater":
						if id > value_min:
							face.select = True
						else:
							face.select = False

					if compare == "Less":
						if id < value_max:
							face.select = True
						else:
							face.select = False

		else:
			for face in faces:
				id = face.index
				# is this face a quad?
				quad = quads.get(str(id))
				if quad:
					value = quad[key][str(frame)]

					if compare == "Equal":
						if value_min <= value <= value_max:
							face.select = True
						else:
							face.select = False

					if compare == "Greater":
						if value > value_min:
							face.select = True
						else:
							face.select = False

					if compare == "Less":
						if value < value_max:
							face.select = True
						else:
							face.select = False


	# go into edit-mode and switch to wireframe
	bpy.ops.object.mode_set(mode="EDIT")
	bpy.context.space_data.shading.type = 'WIREFRAME'

def report_members():
	basics.print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	os.makedirs(os.path.join(directory, "Phaenotyp-members"), exist_ok=True)

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
	basics.print_data("Generate report overview in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	os.makedirs(os.path.join(directory, "Phaenotyp-frames"), exist_ok=True)

	directory += "/Phaenotyp-frames/"

	report.copy_sorttable(directory)

	sorted_frames = basics.sorted_keys(members[list(members)[0]]["axial"])
	start = sorted_frames[0] # first frame (if user is changing start frame)
	end = sorted_frames[len(sorted_frames)-1]

	report.report_frames(directory, start, end)

	# open file
	file_to_open = directory + "/max_sigma.html"
	webbrowser.open(file_to_open)

def report_quads():
	basics.print_data("Generate report overview in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	quads = data["quads"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	os.makedirs(os.path.join(directory, "Phaenotyp-quads"), exist_ok=True)

	directory += "/Phaenotyp-quads/"

	report.copy_sorttable(directory)

	sorted_frames = basics.sorted_keys(quads[list(quads)[0]]["membrane_xy"])
	start = sorted_frames[0] # first frame (if user is changing start frame)
	end = sorted_frames[len(sorted_frames)-1]

	report.report_quads(directory, start, end)

	# open file
	file_to_open = directory + "/membrane_xy.html"
	webbrowser.open(file_to_open)

def report_combined():
	basics.print_data("Generate report overview in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	os.makedirs(os.path.join(directory, "Phaenotyp-combined"), exist_ok=True)

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
	basics.print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current


	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	os.makedirs(os.path.join(directory, "Phaenotyp-chromosomes"), exist_ok=True)

	directory += "/Phaenotyp-chromosomes/"

	report.copy_sorttable(directory)
	report.report_chromosomes(directory)

	# open file
	file_to_open = directory + "/index.html"
	webbrowser.open(file_to_open)

def report_tree():
	basics.print_data("Generate report at frame in html-format")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	# create folder
	filepath = bpy.data.filepath
	directory = os.path.dirname(filepath)

	os.makedirs(os.path.join(directory, "Phaenotyp-tree"), exist_ok=True)

	directory += "/Phaenotyp-tree/"

	report.report_tree(directory)

	# open file
	file_to_open = directory + "/index.html"
	webbrowser.open(file_to_open)

def precast():
	basics.print_data("Precast result with recent shape-keys")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	nn.start()

def reset():
	basics.print_data("reset phaenotyp")

	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp

	# delete active hull and path of from_hull
	scene["<Phaenotyp>fh_hull"] = False
	scene["<Phaenotyp>fh_path"] = False
	scene["<Phaenotyp>fh_area"] = False

	# make structure visible
	# try only because the object is maybe allready deleted
	try:
		data = scene["<Phaenotyp>"]
		scene_id = data["scene_id"]
		obj = scene["<Phaenotyp>"]["structure"]
		obj.hide_set(False)

		# set active again to avoid missing panel
		bpy.context.view_layer.objects.active = obj

		# delete obj and meshes
		basics.delete_obj_if_existing("<Phaenotyp>support_" + str(scene_id))
		basics.delete_mesh_if_existing("<Phaenotyp>support_" + str(scene_id))

		basics.delete_obj_if_existing("<Phaenotyp>members_" + str(scene_id))
		basics.delete_mesh_if_existing("<Phaenotyp>members_" + str(scene_id))

		basics.delete_obj_if_existing("<Phaenotyp>quads_" + str(scene_id))
		basics.delete_mesh_if_existing("<Phaenotyp>quads_" + str(scene_id))

		# delete collection
		basics.delete_col_if_existing("<Phaenotyp>" + str(scene_id))

	except:
		pass

	# create / recreate data
	basics.create_data()

	# change view back to solid ...
	basics.revert_vertex_colors()

	# change props
	phaenotyp.calculation_type = "-"
	phaenotyp.type_of_joints = "-"
