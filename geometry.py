import bpy
import bmesh
from math import sqrt, radians, degrees, pi, atan2
from phaenotyp import basics, operators, material
from mathutils import Color, Vector, Matrix
import os

c = Color()

# variable to pass all stuff that needs to be fixed
to_be_fixed = None

def viz_update(self, context):
	'''
	Triggers the update of the vizulisation.
	This function is used to handle self and context.
	:param self: Passed from the panel.
	:param context: Passed from the panel.
	'''
	update_geometry_post()
	
def fh_update(self, context):
	'''
	Triggers the update from hull.
	:param self: Passed from the panel.
	:param context: Passed from the panel.
	'''
	scene = context.scene
	phaenotyp = scene.phaenotyp
	fh_methode = phaenotyp.fh_methode
	
	# check if all objects are available
	valid_objects = True
	hull = scene.get("<Phaenotyp>fh_hull")
	if not hull:
		valid_objects = False
		
	if fh_methode == "path":
		path = scene.get("<Phaenotyp>fh_path")
		if not path:
			valid_objects = False
	
	# run update
	if valid_objects:
		operators.from_hull()
		
def amount_of_loose_parts():
	'''
	Is returning the amount of loose parts.
	:return total_vert_sel: The amount of loose parts as integer.
	'''
	obj = bpy.context.active_object

	bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
	bpy.ops.mesh.select_all(action='DESELECT')
	bpy.ops.mesh.select_loose()
	return obj.data.total_vert_sel

def amount_of_doubles():
	'''
	Is returning the amount vertices at same position with threshold of 0.001.
	:return total_vert_sel: The amount of loose parts as integer.
	'''
	obj = bpy.context.active_object
	vertices = obj.data.vertices
	
	amount = 0
	for vertex in vertices:
		for other in vertices:
			if vertex != other:
				v_0 = vertex.co
				v_1 = other.co
				
				v = v_1 - v_0
				dist = v.length
				
				if v.length < 0.0001:
					amount += 1
	
	return amount
		
def triangulation():
	'''
	The function is iterating trough all faces and checks the amount of vertices.
	This function is only working for triangulated faces and not edges.
	:return triangulated: Bool True of triangulated or False if not.
	'''
	# get selected faces
	obj = bpy.context.active_object
	mode = bpy.context.object.mode
	bpy.ops.object.mode_set(mode = 'OBJECT')
	triangulated = True
	for face in obj.data.polygons:
		# check triangulation
		if len(face.vertices) != 3:
			# set False, if one face is not tri
			triangulated = False

	# go back to previous mode
	bpy.ops.object.mode_set(mode = mode)
	return triangulated

def amount_of_selected_faces():
	'''
	Is iterating trough all faces and check if the selction is True.
	:return selected_faces: The amount of selected faces as integer.
	'''
	obj = bpy.context.active_object
	bpy.ops.object.mode_set(mode = 'OBJECT')
	selected_faces = []
	for face in obj.data.polygons:
		# collect all selected faces
		if face.select == True:
			selected_faces.append(face)

	return len(selected_faces)

def parts():
	'''
	Get lists of indices from connected vertices
	Is checking for the amount of parts in the mesh. Is based on the answer from BlackCutpoint
	https://blender.stackexchange.com/questions/75332/how-to-find-the-number-of-loose-parts-with-blenders-python-api
	:return parts: Is returning the parts as list of ids of vertices
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	
	parts = data["process"].get("parts")
	if parts:
		# only create parts if not available
		pass
	
	else:
		mesh = obj.data
		paths = {v.index:set() for v in mesh.vertices}

		for e in mesh.edges:
			paths[e.vertices[0]].add(e.vertices[1])
			paths[e.vertices[1]].add(e.vertices[0])

		parts_temp = []

		while True:
			try:
				i=next(iter(paths.keys()))
			except StopIteration:
				break

			part = {i}
			cur = {i}

			while True:
				eligible = {sc for sc in cur if sc in paths}
				if not eligible:
					break

				cur = {ve for sc in eligible for ve in paths[sc]}
				part.update(cur)
				for key in eligible: paths.pop(key)

			parts_temp.append(part)
		
		data["process"]["parts"] = {}
		for id, part in enumerate(parts_temp):
			entries = []
			for entry in part:
				entries.append(entry)
			data["process"]["parts"][str(id)] = entries
		
		parts = data["process"]["parts"]
	
	return parts

def delete_selected_faces():
	'''
	Is handling the mode-switch and deletes all selected faces.
	'''
	obj = bpy.context.active_object
	bpy.ops.object.mode_set(mode='OBJECT')
	selected_faces = []
	for face in obj.data.polygons:
		# collect all selected faces
		if face.select == True:
			selected_faces.append(face)

	bpy.ops.object.mode_set(mode = 'EDIT')
	#support_ids = selected_faces[0].vertices
	bpy.ops.mesh.delete(type='EDGE_FACE')

def volume(mesh):
	'''
	Volume of the structure via bmesh at current frame.
	:param mesh: Mesh of the structure as basis.
	:return frame_volume: Volume as float.
	'''
	bm = bmesh.new()
	bm.from_mesh(mesh)
	frame_volume = bm.calc_volume()

	return frame_volume

def area(faces):
	'''
	Area of the frame as overall sum of faces. Users can delete faces to
	influence this as fitness in ga.
	:param faces: Faces of the mesh as basis.
	:return frame_area: Area as float.
	'''
	frame_area = 0
	for face in faces:
		frame_area += face.area

	return frame_area

def area_projected(face, vertices):
	'''
	Get projected area of a given face. Based on answer from Nikos Athanasiou:
	https://stackoverflow.com/questions/24467972/calculate-area-of-polygon-given-x-y-coordinates
	:param face: Face to work with.
	:param vertices: Vertices of the face to work with.
	:return area_projected: Projected area as float.
	'''
	vertex_ids = face.vertices
	vertices_temp = []
	for vertex_id in vertex_ids:
		vertex = vertices[vertex_id]
		vertices_temp.append(vertex.co)

	n = len(vertices_temp)
	a = 0.0
	for i in range(n):
		j = (i + 1) % n
		v_i = vertices_temp[i]
		v_j = vertices_temp[j]

		a += v_i[0] * v_j[1]
		a -= v_j[0] * v_i[1]

	area_projected = abs(a) / 2.0

	return area_projected

def perimeter(edge_keys, vertices):
	'''
	Get distances and perimeter of the given face.
	:param edge_keys: Edge_keys from the face as list.
	:param vertices: Vertices of the face.
	:return distances: Distance as list of floats.
	:return perimeter: Perimeter as float.
	'''
	distances = []
	for edge_key in edge_keys:
		vertex_0_id = edge_key[0]
		vertex_1_id = edge_key[1]

		vertex_0_co = vertices[vertex_0_id].co
		vertex_1_co = vertices[vertex_1_id].co

		dist_vector = vertex_0_co - vertex_1_co
		dist = dist_vector.length
		distances.append(dist)

	perimeter = sum(distances)

	return distances, perimeter

def rise(vertices):
	'''
	Rise of the structure as fitness. The function is iterating through
	all vertices and returns the distance between the highest and lowest
	point.
	:param vertices: Vertices of the given structure.
	:return frame_rise: Rise as float
	'''
	highest = 0
	lowest = 0

	for vertex in vertices:
		z = vertex.co[2]

		# find highest
		if z > highest:
			highest = z

		# find lowest
		if z < lowest:
			lowest = z

	frame_rise = highest-lowest
	return frame_rise

def span(vertices, supports):
	'''
	Span of the structure as fitness. The function is iterating through
	all vertices and returns the highest distance between all supports.
	:param vertices: Vertices of the given structure.
	:param supports: Supports of the given structure.
	:return frame_span: Span as float
	'''
	highest = 0

	for current in supports:
		for other in supports:
			if current != other:
				current_co = vertices[int(current)].co
				other_co = vertices[int(other)].co

				dist_v = other_co - current_co
				dist = dist_v.length

				# find highest
				if dist > highest:
					highest = dist

	frame_span = highest
	return frame_span

def cantilever(vertices, supports):
	# get cantilever of frame
	# (lowest distance from all vertices to all supports)
	highest = 0

	for vertex in vertices:
		to_closest_support = float('inf')
		for support in supports:
			vertex_co = vertex.co
			support_co = vertices[int(support)].co

			if vertex_co != support_co:
				dist_v = support_co - vertex_co
				dist = dist_v.length

				# find highest
				if dist < to_closest_support:
					to_closest_support = dist

		# find highest
		if to_closest_support > highest:
			highest = to_closest_support

	frame_cantilever = highest

	# return 0 if there is only one support
	if frame_cantilever == float('inf'):
		frame_cantilever = 0

	return frame_cantilever

def set_shape_keys(shape_keys, chromosome):
	for id, key in enumerate(shape_keys):
		if id > 0: # to exlude basis
			key.value = chromosome[id-1]
			
def create_supports(structure_obj, supports):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]
	
	mesh = bpy.data.meshes.new("<Phaenotyp>support_" + str(scene_id))
	obj = bpy.data.objects.new(mesh.name, mesh)
	col = bpy.data.collections.get("<Phaenotyp>" + str(scene_id))
	col.objects.link(obj)
	bpy.context.view_layer.objects.active = obj

	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = structure_obj.matrix_world

	verts = []
	edges = []
	faces = []

	structure_obj_vertices = structure_obj.data.vertices
	len_verts = 0

	for id, support in supports.items():
		id = int(id)

		# transfer parameters
		loc_x = support[0]
		loc_y = support[1]
		loc_z = support[2]

		rot_x = support[3]
		rot_y = support[4]
		rot_z = support[5]

		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		v = mat @ structure_obj_vertices[id].co

		x = v[0]
		y = v[1]
		z = v[2]

		# to set position
		offset = Vector((x, y, z))

		# pyramide floor
		v_0 = Vector((-0.1, 0.1,-0.1)) + offset
		v_1 = Vector(( 0.1, 0.1,-0.1)) + offset
		v_2 = Vector(( 0.1,-0.1,-0.1)) + offset
		v_3 = Vector((-0.1,-0.1,-0.1)) + offset
		v_4 = Vector(( 0.0, 0.0, 0.0)) + offset

		verts.append(v_0)
		verts.append(v_1)
		verts.append(v_2)
		verts.append(v_3)
		verts.append(v_4)

		edges.append([0+len_verts, 1+len_verts])
		edges.append([1+len_verts, 2+len_verts])
		edges.append([2+len_verts, 3+len_verts])
		edges.append([3+len_verts, 0+len_verts])

		edges.append([0+len_verts, 4+len_verts])
		edges.append([1+len_verts, 4+len_verts])
		edges.append([2+len_verts, 4+len_verts])
		edges.append([3+len_verts, 4+len_verts])

		# loc_x
		lx = 1 if loc_x == True else 0
		v_5 = Vector(( 0.0*lx, 0.0,-0.2*lx)) + offset
		v_6 = Vector(( 0.2*lx, 0.0,-0.2*lx)) + offset

		verts.append(v_5)
		verts.append(v_6)

		edges.append([5+len_verts, 6+len_verts])

		# loc_y
		ly = 1 if loc_y == True else 0
		v_7 = Vector(( 0.0, 0.0*ly,-0.2*ly)) + offset
		v_8 = Vector(( 0.0, 0.2*ly,-0.2*ly)) + offset

		verts.append(v_7)
		verts.append(v_8)

		edges.append([7+len_verts, 8+len_verts])

		# loc_z
		lz = 1 if loc_z == True else 0
		v_9 = Vector(( 0.0, 0.0,-0.2*lz)) + offset
		v_10 = Vector(( 0.0, 0.0,-0.4*lz)) + offset

		verts.append(v_9)
		verts.append(v_10)

		edges.append([9+len_verts, 10+len_verts])

		# rot_x
		rx = 1 if rot_x == True else 0
		v_11 = Vector(( 0.20*rx, 0.02*rx,-0.22*rx)) + offset
		v_12 = Vector(( 0.20*rx,-0.02*rx,-0.22*rx)) + offset
		v_13 = Vector(( 0.20*rx,-0.02*rx,-0.18*rx)) + offset
		v_14 = Vector(( 0.20*rx, 0.02*rx,-0.18*rx)) + offset

		verts.append(v_11)
		verts.append(v_12)
		verts.append(v_13)
		verts.append(v_14)

		edges.append([11+len_verts, 12+len_verts])
		edges.append([12+len_verts, 13+len_verts])
		edges.append([13+len_verts, 14+len_verts])
		edges.append([14+len_verts, 11+len_verts])

		# rot_y
		ry = 1 if rot_y == True else 0
		v_15 = Vector(( 0.02*ry, 0.20*ry,-0.22*ry)) + offset
		v_16 = Vector((-0.02*ry, 0.20*ry,-0.22*ry)) + offset
		v_17 = Vector((-0.02*ry, 0.20*ry,-0.18*ry)) + offset
		v_18 = Vector(( 0.02*ry, 0.20*ry,-0.18*ry)) + offset

		verts.append(v_15)
		verts.append(v_16)
		verts.append(v_17)
		verts.append(v_18)

		edges.append([15+len_verts, 16+len_verts])
		edges.append([16+len_verts, 17+len_verts])
		edges.append([17+len_verts, 18+len_verts])
		edges.append([18+len_verts, 15+len_verts])

		# rot_z
		rz = 1 if rot_z == True else 0
		v_19 = Vector(( 0.02*rz, 0.02*rz,-0.40*rz)) + offset
		v_20 = Vector((-0.02*rz, 0.02*rz,-0.40*rz)) + offset
		v_21 = Vector((-0.02*rz,-0.02*rz,-0.40*rz)) + offset
		v_22 = Vector(( 0.02*rz,-0.02*rz,-0.40*rz)) + offset

		verts.append(v_19)
		verts.append(v_20)
		verts.append(v_21)
		verts.append(v_22)

		edges.append([19+len_verts, 20+len_verts])
		edges.append([20+len_verts, 21+len_verts])
		edges.append([21+len_verts, 22+len_verts])
		edges.append([22+len_verts, 19+len_verts])

		len_verts += 23

	mesh.from_pydata(verts, edges, faces)

def create_members(structure_obj, members):
	# create mesh and object
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]
	mesh = bpy.data.meshes.new("<Phaenotyp>members_" + str(scene_id))
	obj = bpy.data.objects.new(mesh.name, mesh)
	col = bpy.data.collections.get("<Phaenotyp>" + str(scene_id))
	col.objects.link(obj)
	bpy.context.view_layer.objects.active = obj
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current

	verts = []
	edges = []
	faces = []

	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = structure_obj.matrix_world

	structure_obj_vertices = structure_obj.data.vertices

	len_verts = 0

	for id, member in members.items():
		if phaenotyp.calculation_type != "force_distribution":
			member["mesh_vertex_ids"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
		else:
			member["mesh_vertex_ids"] = [0, 0]

		id = int(id)

		vertex_0_id = member["vertex_0_id"]
		vertex_1_id = member["vertex_1_id"]

		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		vertex_0_co = mat @ structure_obj_vertices[vertex_0_id].co
		vertex_1_co = mat @ structure_obj_vertices[vertex_1_id].co

		# create vertices
		if phaenotyp.calculation_type != "force_distribution":
			for i in range(11):
				pos = (vertex_0_co*(i) + vertex_1_co*(10-i))*0.1

				v = Vector(pos)
				verts.append(v)

				member["mesh_vertex_ids"][i] = len_verts+i

			# add edges
			edges.append([0 + len_verts, 1 + len_verts])
			edges.append([1 + len_verts, 2 + len_verts])
			edges.append([2 + len_verts, 3 + len_verts])
			edges.append([3 + len_verts, 4 + len_verts])
			edges.append([4 + len_verts, 5 + len_verts])
			edges.append([5 + len_verts, 6 + len_verts])
			edges.append([6 + len_verts, 7 + len_verts])
			edges.append([7 + len_verts, 8 + len_verts])
			edges.append([8 + len_verts, 9 + len_verts])
			edges.append([9 + len_verts, 10 + len_verts])

			# update counter
			len_verts += 11

		else:
			v_0 = Vector(vertex_0_co)
			verts.append(v_0)
			member["mesh_vertex_ids"][0] = len_verts

			v_1 = Vector(vertex_1_co)
			verts.append(v_1)
			member["mesh_vertex_ids"][1] = len_verts+1

			# add edges
			edges.append([0 + len_verts, 1 + len_verts])

			# update counter
			len_verts += 2

	mesh.from_pydata(verts, edges, faces)

	# create vertex_color
	attribute = obj.data.attributes.get("force")
	if attribute:
		text = "existing attribute:" + str(attribute)
	else:
		bpy.ops.geometry.color_attribute_add(name="force", domain='POINT', data_type='FLOAT_COLOR', color=(255, 0, 255, 1))

	# create material
	material_name =  "<Phaenotyp>members"
	member_material = bpy.data.materials.get(material_name)
	if member_material == None:
		mat = bpy.data.materials.new(material_name)
		
		mat.use_nodes = True
		nodetree = mat.node_tree

		# add color attribute
		ca = nodetree.nodes.new(type="ShaderNodeVertexColor")

		# set group
		ca.layer_name = "force"

		# connect to color attribute to base color
		input = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']
		output = ca.outputs['Color']
		nodetree.links.new(input, output)
	
	obj.data.materials.append(bpy.data.materials.get(material_name))
	obj.active_material_index = len(obj.data.materials) - 1
	
	# create modifiere if not existing
	modifier = obj.modifiers.get('<Phaenotyp>')
	if modifier:
		text = "existing modifier:" + str(modifier)
	else:
		# append node group from setup.blend
		# this is easier as rebuilding by code
		addon_path = os.path.dirname(__file__)
		filepath = os.path.join(addon_path, "setup.blend")
		node_tree_section = os.path.join(filepath, "NodeTree")
		bpy.ops.wm.append(
			filepath = os.path.join(node_tree_section, "<Phaenotyp>"),
			directory = node_tree_section + os.sep,
			filename = "<Phaenotyp>"
		)
		
		# add new modifier
		modifier = obj.modifiers.new(name="Phaenotyp", type='NODES')

		# add node group
		modifier.node_group = bpy.data.node_groups["<Phaenotyp>"]

	# create vertex_groups
	bpy.ops.object.mode_set(mode = 'OBJECT')

	type_group = obj.vertex_groups.get("type")
	if not type_group:
		type_group = obj.vertex_groups.new(name="type")
			
	height_group = obj.vertex_groups.get("height")
	if not height_group:
		height_group = obj.vertex_groups.new(name="height")

	width_group = obj.vertex_groups.get("width")
	if not width_group:
		width_group = obj.vertex_groups.new(name="width")

	angle_group = obj.vertex_groups.get("angle")
	if not angle_group:
		angle_group = obj.vertex_groups.new(name="angle")
			
	# assign to group
	for id, member in members.items():
		id = str(id)
		vertex_ids = member["mesh_vertex_ids"]
		
		# avoid no height at frame without calculation
		# if no height is available, no info is available
		if str(frame) not in member["height"]:
			member["height"][str(frame)] = member["height_first"]
			member["width"][str(frame)] = member["width_first"]
			member["wall_thickness"][str(frame)] = member["wall_thickness_first"]
			member["profile"][str(frame)] = member["profile_first"]
			member["angle"][str(frame)] = member["angle_first"]
		
		profile_type = member["profile_type"]		
		if profile_type in ["round_hollow", "round_solid"]:
			# set 0.1 to define as pipe in gn
			type_group.add(vertex_ids, 0.0, 'REPLACE')

		if profile_type in ["rect_hollow", "rect_solid"]:
			# set 0.2 to define as pipe in gn
			type_group.add(vertex_ids, 0.1, 'REPLACE')
			
		if profile_type == "standard_profile":
			# set 0.3 to define as standard profile in gn
			type_group.add(vertex_ids, 0.2, 'REPLACE')
			
		# pass height and width
		height = member["height"][str(frame)]*0.01
		height_group.add(vertex_ids, height, 'REPLACE')
		width = member["width"][str(frame)]*0.01
		width_group.add(vertex_ids, width, 'REPLACE')
		
		# claculate angle depending on the normal
		if member["orientation"] == "normal":
			vertex_0 = structure_obj_vertices[member["vertex_0_id"]]
			vertex_1 = structure_obj_vertices[member["vertex_1_id"]]

			# Kante
			v_0 = structure_obj.matrix_world @ vertex_0.co
			v_1 = structure_obj.matrix_world @ vertex_1.co

			# Normale
			n_0 = structure_obj.matrix_world.to_3x3() @ vertex_0.normal
			n_1 = structure_obj.matrix_world.to_3x3() @ vertex_1.normal
			avg_normal = (n_0 + n_1).normalized()

			# Tangente entlang der Kante
			tangent = (v_1 - v_0).normalized()

			# Fallback-Achse für Aufbau lokalen Systems (globale Z)
			fallback = Vector((0, 0, 1))

			# Sicherstellen, dass Kreuzprodukt funktioniert (nicht parallel)
			if abs(tangent.dot(fallback)) > 0.99:
				fallback = Vector((0, 1, 0))

			# Lokales Koordinatensystem (x, y, z): garantiert rechtshändig
			z_axis = tangent
			x_axis = fallback.cross(z_axis).normalized()
			y_axis = z_axis.cross(x_axis).normalized()

			# Matrix Welt → Lokales Profilkoordinatensystem
			local_matrix = Matrix((x_axis, y_axis, z_axis)).transposed()

			# Transformiere avg_normal in lokalen Raum
			local_vec = local_matrix.inverted() @ avg_normal

			# Jetzt kommt's: atan2(y, x) gibt den Winkel **im lokalen Koordinatensystem**
			angle = degrees(atan2(-local_vec.y, local_vec.x)) % 360

			# Optional angle offset
			angle = angle + member["angle"][str(frame)]
			angle = angle * 0.001
			
		else:
			angle = member["angle"][str(frame)] * 0.001
		
		angle_group.add(vertex_ids, angle, 'REPLACE')			

def create_quads(structure_obj, quads):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]
	
	# create mesh and object
	mesh = bpy.data.meshes.new("<Phaenotyp>quads_" + str(scene_id))
	obj = bpy.data.objects.new(mesh.name, mesh)
	col = bpy.data.collections.get("<Phaenotyp>" + str(scene_id))
	col.objects.link(obj)
	bpy.context.view_layer.objects.active = obj
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current

	verts = []
	edges = []
	faces = []

	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = structure_obj.matrix_world

	structure_obj_vertices = structure_obj.data.vertices

	# to keep track of the newly created mesh
	# the whole mesh is recreated when a new member oder quad is added
	used_verts = {}
	len_verts = 0
	len_faces = 0

	for id, quad in quads.items():
		vertices_ids_structure = quad["vertices_ids_structure"]
		
		# add or update nodes
		# this is necessary because faces can share same vertices
		vertices_ids_viz = []		
		for vertex_id in vertices_ids_structure:
			# create entry in temporary dictionary
			if str(vertex_id) not in used_verts:
				# like suggested here by Gorgious and CodeManX:
				# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
				vertex_co = mat @ structure_obj_vertices[vertex_id].co
				
				# append to verts for the new mesh
				verts.append(vertex_co)
				
				# to keep track of used vertices
				# key = original id in structure, value = new id in mesh for viz
				used_verts[str(vertex_id)] = len_verts
				vertices_ids_viz.append(len_verts)
				
				# update id of new vertices
				len_verts += 1
			
			else:
				existing_id = used_verts[str(vertex_id)]
				vertices_ids_viz.append(existing_id)
		
		# add face
		faces.append(vertices_ids_viz)
		
		# store for later
		quad["face_id_viz"] = len_faces
		
		# update list
		len_faces += 1
		
		# save new ids to data for later access
		quad["vertices_ids_viz"] = vertices_ids_viz
		
	mesh.from_pydata(verts, edges, faces)

	# create vertex_color
	attribute_1 = obj.data.attributes.get("force_1")
	attribute_2 = obj.data.attributes.get("force_2")
	
	if attribute_1:
		text = "existing attribute_1:" + str(attribute_1)
	else:
		bpy.ops.geometry.color_attribute_add(name="force_1", domain='POINT', data_type='FLOAT_COLOR', color=(255, 0, 255, 1))

	if attribute_2:
		text = "existing attribute_2:" + str(attribute_2)
	else:
		bpy.ops.geometry.color_attribute_add(name="force_2", domain='POINT', data_type='FLOAT_COLOR', color=(255, 0, 255, 1))

	# create material for side 1
	material_name_1 = "<Phaenotyp>quad_1"
	quad_material_1 = bpy.data.materials.get(material_name_1)
	if quad_material_1 == None:
		mat = bpy.data.materials.new(material_name_1)
		
		mat.use_nodes = True
		nodetree = mat.node_tree

		# add color attribute
		ca = nodetree.nodes.new(type="ShaderNodeVertexColor")

		# set group
		ca.layer_name = "force_1"

		# connect to color attribute to base color
		input = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']
		output = ca.outputs['Color']
		nodetree.links.new(input, output)

	obj.data.materials.append(bpy.data.materials.get(material_name_1))    
	obj.active_material_index = len(obj.data.materials) - 1

	# create material for side 2
	material_name_2 = "<Phaenotyp>quad_2"
	quad_material_2 = bpy.data.materials.get(material_name_2)
	if quad_material_2 == None:
		mat = bpy.data.materials.new(material_name_2)
		
		mat.use_nodes = True
		nodetree = mat.node_tree

		# add color attribute
		ca = nodetree.nodes.new(type="ShaderNodeVertexColor")

		# set group
		ca.layer_name = "force_2"

		# connect to color attribute to base color
		input = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']
		output = ca.outputs['Color']
		nodetree.links.new(input, output)

	obj.data.materials.append(bpy.data.materials.get(material_name_2))    
	obj.active_material_index = len(obj.data.materials) - 1
	
	# create vertex_group for thickness
	bpy.ops.object.mode_set(mode = 'OBJECT')
	thickness_group = obj.vertex_groups.get("thickness")
	if not thickness_group:
		thickness_group = obj.vertex_groups.new(name="thickness")

	# create modifiere if not existing
	modifier = obj.modifiers.get('<Phaenotyp>')
	if modifier:
		text = "existing modifier:" + str(modifier)
	else:
		modifier_subsurf = obj.modifiers.new(name="<Phaenotyp>", type='SUBSURF')
		modifier_subsurf.levels = 2
		modifier_subsurf.subdivision_type = 'SIMPLE'

		modifier_solidify = obj.modifiers.new(name="<Phaenotyp>", type='SOLIDIFY')
		modifier_solidify.thickness = 1
		modifier_solidify.vertex_group = "thickness"
		modifier_solidify.use_even_offset = True
		modifier_solidify.material_offset = 1
		modifier_solidify.offset = -1
		modifier_solidify.use_rim = False
	
	# set the thickness passed from gui
	for id, quad in quads.items():
		vertices_ids = quad["vertices_ids_viz"]
		thickness = quad["thickness_first"] * 0.01 # to convert from cm to m
		thickness_group.add(vertices_ids, thickness, 'REPLACE')

def create_stresslines(structure_obj, quads):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]
	
	# create mesh and object
	mesh = bpy.data.meshes.new("<Phaenotyp>stresslines_" + str(scene_id))
	obj = bpy.data.objects.new(mesh.name, mesh)
	col = bpy.data.collections.get("<Phaenotyp>" + str(scene_id))
	col.objects.link(obj)
	bpy.context.view_layer.objects.active = obj
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	frame = scene.frame_current
	
	data = scene["<Phaenotyp>"]
	structure = data["structure"]
	
	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = structure_obj.matrix_world
	
	structure_faces = structure.data.polygons
	
	verts = []
	edges = []
	faces = []
	
	len_verts = 0

	for id, quad in quads.items():
		face = structure_faces[int(id)]
		normal = face.normal
		center = face.center
		
		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		normal = mat @ normal
		center = mat @ center
		
		thickness = quad["thickness_first"] * 0.01
		
		# append vertices for first edge
		verts.append(center)
		verts.append(center + normal*0.2)
				
		# add first edge
		edges.append([len_verts, len_verts+1])
		
		# update id of new vertices
		len_verts += 2
		
		# append vertices for second edge
		verts.append(center)
		verts.append(center + normal*0.2)
				
		# add second edge
		edges.append([len_verts, len_verts+1])
		
		# update id of new vertices
		len_verts += 2
		
		# append vertices for third edge
		verts.append(center)
		verts.append(center + normal*0.2)
				
		# add third edge
		edges.append([len_verts, len_verts+1])
		
		# update id of new vertices
		len_verts += 2
		
		# append vertices for fourth edge
		verts.append(center)
		verts.append(center + normal*0.2)
				
		# add fourth edge
		edges.append([len_verts, len_verts+1])
		
		# update id of new vertices
		len_verts += 2
		
		# store for later for ids of start_first, end_first, start_second, end_second ...
		quad["stresslines_viz"] = [len_verts-8, len_verts-7, len_verts-6, len_verts-5, len_verts-4, len_verts-3, len_verts-2, len_verts-1]
		
	mesh.from_pydata(verts, edges, faces)

	# create vertex_color
	attribute = obj.data.attributes.get("stressline")
	if attribute:
		text = "existing attribute:" + str(attribute)
	else:
		bpy.ops.geometry.color_attribute_add(name="stressline", domain='POINT', data_type='FLOAT_COLOR', color=(255, 0, 255, 1))

	# create material
	material_name =  "<Phaenotyp>Stresslines_" + str(scene_id)
	stressline_material = bpy.data.materials.get(material_name)
	if stressline_material == None:
		mat = bpy.data.materials.new(material_name)
		
		mat.use_nodes = True
		nodetree = mat.node_tree

		# add color attribute
		ca = nodetree.nodes.new(type="ShaderNodeVertexColor")

		# set group
		ca.layer_name = "stressline"

		# connect to color attribute to base color
		input = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']
		output = ca.outputs['Color']
		nodetree.links.new(input, output)

	obj.data.materials.append(bpy.data.materials.get(material_name))
	obj.active_material_index = len(obj.data.materials) - 1
	
	# create modifiere if not existing
	modifier = obj.modifiers.get('<Phaenotyp>')
	if modifier:
		text = "existing modifier:" + str(modifiers)
	else:
		modifier_nodes = obj.modifiers.new(name="<Phaenotyp>", type='NODES')
		bpy.ops.node.new_geometry_node_group_assign()
		nodes = obj.modifiers['<Phaenotyp>'].node_group

		# set name to group
		if nodes.name == "<Phaenotyp>Stresslines_" + str(scene_id):
			node_group = bpy.data.node_groups["<Phaenotyp>Stresslines_" + str(scene_id)]
		else:
			nodes.name = "<Phaenotyp>Stresslines_" + str(scene_id)
			node_group = bpy.data.node_groups["<Phaenotyp>Stresslines_" + str(scene_id)]

		# mesh to curve
		mtc = node_group.nodes.new(type="GeometryNodeMeshToCurve")
		input = mtc.inputs[0] # mesh to curve, mesh
		output = node_group.nodes[0].outputs[0] # group input, geometry
		node_group.links.new(input, output)

		# curve to mesh
		ctm = node_group.nodes.new(type="GeometryNodeCurveToMesh")
		input = mtc.outputs[0] # mesh to curve, curve
		output = ctm.inputs[0] # curve to mesh, curve
		node_group.links.new(input, output)

		# pass radius to scale
		radii = node_group.nodes.new(type="GeometryNodeInputNamedAttribute")
		radii.name = "radius"
		radii.data_type = 'FLOAT'
		radii.inputs[0].default_value = "radius" # vertex group
		input = radii.outputs[0] # namend attribute
		output = ctm.inputs[2] # scale of ctm
		node_group.links.new(input, output)
		
		# profile to curve
		cc = node_group.nodes.new(type="GeometryNodeCurvePrimitiveCircle")
		cc.inputs[0].default_value = 8 # set amount of vertices of circle
		cc.inputs[4].default_value = 0.05 # diameter
		input = ctm.inputs[1] # curve to mesh, profile curve
		output = cc.outputs[0] # curve circe, curve
		node_group.links.new(input, output)

		# set material
		gnsm = node_group.nodes.new(type="GeometryNodeSetMaterial")
		gnsm.inputs[2].default_value = bpy.data.materials[ "<Phaenotyp>Stresslines_" + str(scene_id)]
		input = gnsm.inputs[0] # geometry
		output = ctm.outputs[0] # curve to mesh, mesh
		node_group.links.new(input, output)

		# link to output
		output = gnsm.outputs[0] # gnsm, geometry
		input = node_group.nodes[1].inputs[0] # group output, geometry
		node_group.links.new(input, output)

	# create vertex_group for radius
	# radius is automatically choosen by geometry nodes for radius-input
	bpy.ops.object.mode_set(mode = 'OBJECT')
	radius_group = obj.vertex_groups.get("radius")
	if not radius_group:
		radius_group = obj.vertex_groups.new(name="radius")
	
	ids = [i for i in range(len(obj.data.vertices))]
	radius_group.add(ids, 0, 'REPLACE')
		
def update_translation():
	phaenotyp = bpy.context.scene.phaenotyp
	
	# update translation if activated
	if phaenotyp.assimilate_update == True:
		operators.assimilate()
		
	if phaenotyp.actuator_update == True:
		operators.actuator()
		
	if phaenotyp.goal_update == True:
		operators.reach_goal()
		
	if phaenotyp.wool_update == True:
		operators.wool_threads()
		
	if phaenotyp.crown_update == True:
		operators.crown_shyness()
	
def update_geometry_pre():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	quads = data["quads"]
	structure_obj_vertices = data["structure"]
	frame = bpy.context.scene.frame_current

	for id, member in members.items():
		id = int(id)

		# copy properties if not set by optimization
		# or the user changed the frame during optimization
		if str(frame) not in member["height"]:
			member["height"][str(frame)] = member["height_first"]
			member["width"][str(frame)] = member["width_first"]
			member["wall_thickness"][str(frame)] = member["wall_thickness_first"]
			member["profile"][str(frame)] = member["profile_first"]
			member["angle"][str(frame)] = member["angle_first"]
				
		# update material (like updated when passed from gui in material.py)
		profile_type = member["profile_type"]
		
		if profile_type == "round_hollow":
			diameter = member["height"][str(frame)]
			wall_thickness = member["wall_thickness"][str(frame)]
			Di = diameter - wall_thickness*2
			
			# moment of inertia, 32.9376 cm⁴
			member["Iy"][str(frame)] = pi * (diameter**4 - Di**4)/64
			member["Iz"][str(frame)] = member["Iy"][str(frame)]
			
			# torsional constant, 65.875 cm⁴
			member["J"][str(frame)] = pi * (diameter**4 - Di**4)/32
			
			# cross-sectional area, 8,64 cm²
			member["A"][str(frame)] = ((pi * (diameter*0.5)**2) - (pi * (Di*0.5)**2))
			
			# weight of profile, 6.78 kg/m
			member["weight_A"][str(frame)] =  member["A"][str(frame)] * member["rho"] * 0.1

			member["ir_y"][str(frame)] = sqrt(member["Iy"][str(frame)] / member["A"][str(frame)])
			member["ir_z"][str(frame)] = sqrt(member["Iz"][str(frame)] / member["A"][str(frame)])
			
		if profile_type == "round_solid":
			diameter = member["height"][str(frame)]
			wall_thickness = member["wall_thickness"][str(frame)]
			
			member["Iy"][str(frame)] = pi * (diameter**4)/64
			member["Iz"][str(frame)] = member["Iy"][str(frame)]
			member["J"][str(frame)] = pi * (diameter**4)/32
			member["A"][str(frame)] = ((pi * (diameter*0.5)**2))
			member["weight_A"][str(frame)] =  member["A"][str(frame)] * member["rho"] * 0.1
			member["ir_y"][str(frame)] = sqrt(member["Iy"][str(frame)] / member["A"][str(frame)])
			member["ir_z"][str(frame)] = sqrt(member["Iz"][str(frame)] / member["A"][str(frame)])
					
		if profile_type == "rect_hollow":
			height = member["height"][str(frame)]
			width = member["width"][str(frame)]
			t = member["wall_thickness"][str(frame)]
			
			# Innenmaße
			height_i = height - 2 * t
			width_i = width - 2 * t

			# Flächenträgheitsmomente
			member["Iy"][str(frame)] = (height * width**3 - height_i * width_i**3) / 12
			member["Iz"][str(frame)] = (width * height**3 - width_i * height_i**3) / 12

			# Näherung für Torsionskonstante eines rechteckigen Hohlprofils (nicht exakt!)
			# Für t << b,h:
			member["J"][str(frame)] = (2 * t) * (height * width - height_i * width_i) / 3

			# Querschnittsfläche
			member["A"][str(frame)] = height * width - height_i * width_i

			# Gewicht
			member["weight_A"][str(frame)] = member["A"][str(frame)] * member["rho"] * 0.1

			# Radius of gyration
			member["ir_y"][str(frame)] = sqrt(member["Iy"][str(frame)] / member["A"][str(frame)])
			member["ir_z"][str(frame)] = sqrt(member["Iz"][str(frame)] / member["A"][str(frame)])
				
		if profile_type == "rect_solid":
			height = member["height"][str(frame)]      # Breite (z-Richtung)
			width = member["width"][str(frame)]        # Höhe (y-Richtung)
			
			# Flächenträgheitsmomente
			member["Iy"][str(frame)] = (width * height**3) / 12  # um z-Achse
			member["Iz"][str(frame)] = (height * width**3) / 12  # um y-Achse

			# Torsionskonstante (Näherung für rechteckigen Querschnitt, Kasten)
			member["J"][str(frame)] = (height * width**3) * (1/3) if height <= width else (width * height**3) * (1/3)

			# Querschnittsfläche
			member["A"][str(frame)] = height * width

			# Gewicht
			member["weight_A"][str(frame)] = member["A"][str(frame)] * member["rho"] * 0.1

			# Radius of gyration
			member["ir_y"][str(frame)] = sqrt(member["Iy"][str(frame)] / member["A"][str(frame)])
			member["ir_z"][str(frame)] = sqrt(member["Iz"][str(frame)] / member["A"][str(frame)])
				
		if profile_type == "standard_profile":
			profile_id = member["profile"][str(frame)]
			profile = None
			for profile in material.profiles:
				if profile[0] == profile_id:
					current_profile = profile

			member["height"][str(frame)] = current_profile[2] * 0.1 # scale correctly from library
			member["width"][str(frame)] = current_profile[3] * 0.1 # scale correctly from library
					
			member["Iy"][str(frame)] = current_profile[8]
			member["Iz"][str(frame)] = current_profile[9]
			member["J"][str(frame)] = current_profile[10]
			member["A"][str(frame)] = current_profile[6]
			member["weight_A"][str(frame)] = member["A"][str(frame)] * member["rho"] * 0.1 # Gewicht vom Material
			member["ir_y"][str(frame)] = sqrt(member["Iy"][str(frame)] / member["A"][str(frame)])
			member["ir_z"][str(frame)] = sqrt(member["Iz"][str(frame)] / member["A"][str(frame)])
			
	for id, quad in quads.items():
		id = int(id)

		# copy properties if not set by optimization
		# or the user changed the frame during optimization
		if str(frame) not in quad["thickness"]:
			quad["thickness"][str(frame)] = quad["thickness_first"]
		
		# need to be updated for quads
		'''
		# update material (like updated when passed from gui in material.py)
		member["Iy"][str(frame)] = pi * (member["Do"][str(frame)]**4 - member["Di"][str(frame)]**4)/64
		member["Iz"][str(frame)] = member["Iy"][str(frame)]
		member["J"][str(frame)]  = pi * (member["Do"][str(frame)]**4 - member["Di"][str(frame)]**4)/(32)
		member["A"][str(frame)]  = ((pi * (member["Do"][str(frame)]*0.5)**2) - (pi * (member["Di"][str(frame)]*0.5)**2))
		member["weight_A"][str(frame)] =  member["A"][str(frame)]*member["d"] * 0.1
		member["ir"][str(frame)] = sqrt(member["Iy"][str(frame)]/member["A"][str(frame)])
		'''
		
	update_translation()

def hide_reveal(self, context):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]
	structure = data["structure"]
	
	objs = bpy.data.objects
	
	to_set = [
		[phaenotyp.viz_show_structure, structure.name_full],
		[phaenotyp.viz_show_supports, "<Phaenotyp>support_" + str(scene_id)],
		[phaenotyp.viz_show_loads, "<Phaenotyp>load_" + str(scene_id)],
		[phaenotyp.viz_show_members, "<Phaenotyp>members_" + str(scene_id)],
		[phaenotyp.viz_show_quads, "<Phaenotyp>quads_" + str(scene_id)],
		[phaenotyp.viz_show_stresslines, "<Phaenotyp>stresslines_" + str(scene_id)]
	]
	
	for viz_show, name in to_set:
		if viz_show == True:
			for obj in objs:
				if name in obj.name_full:
					obj.hide_set(False)
					obj.hide_render = False
		
		if viz_show == False:
			for obj in objs:
				if name in obj.name_full:
					obj.hide_set(True)
					obj.hide_render = True
		
		text = name + " visible " + str(viz_show)
		basics.print_data(text)
	
	
def rainbow(force, overstress, viz_boundaries, viz_scale):
	h = force*(-1) / viz_boundaries * viz_scale + 0.333
	if h > 0.666:
		h = 0.666
	if h < 0:
		h = 0
	s = 1
	
	if overstress == True:
		v = 0.25
	else:
		v = 1.0
	
	c.hsv = h,s,v
	return [c.r, c.g, c.b, 1.0]
	
def red_blue(force, overstress, viz_boundaries, viz_scale):
	if force > 0:
		h = 0
	else:
		h = 0.666
	
	s = 1
	
	if overstress == True:
		v = 0.25
	else:
		v = 1.0
	
	c.hsv = h,s,v
	return [c.r, c.g, c.b, 1.0]
	
def update_geometry_post():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]
	members = data["members"]
	structure_obj_vertices = data["structure"]
	frame = bpy.context.scene.frame_current
	
	# if members
	mesh_for_viz = bpy.data.objects.get("<Phaenotyp>members_" + str(scene_id))
	if mesh_for_viz:
		vertices = mesh_for_viz.data.vertices

		#radius_group = mesh_for_viz.vertex_groups.get("radius")
		height_group = mesh_for_viz.vertex_groups.get("height")
		width_group = mesh_for_viz.vertex_groups.get("width")
		wall_thickness_group = mesh_for_viz.vertex_groups.get("wall_thickness")
		profile_group = mesh_for_viz.vertex_groups.get("profile")
		angle_group = mesh_for_viz.vertex_groups.get("angle")
			
		attribute = mesh_for_viz.data.attributes.get("force")
		
		viz_deflection = phaenotyp.viz_deflection * 0.01
		
		viz_boundaries_members = abs(phaenotyp.viz_boundaries_members)
		viz_boundaries_quads = abs(phaenotyp.viz_boundaries_quads)
		
		viz_scale = phaenotyp.viz_scale / 100 # for percentage
		
		viz_stressline_scale = phaenotyp.viz_stressline_scale
		viz_stressline_length = phaenotyp.viz_stressline_length
		
		for id, member in members.items():
			id = int(id)

			mesh_vertex_ids = member["mesh_vertex_ids"]

			# update radius and others
			vertex_ids = member["mesh_vertex_ids"]
			height = member["height"][str(frame)]*0.01
			width = member["width"][str(frame)]*0.01
			angle = member["angle"][str(frame)]*0.01
			
			# pass parameters to vertex groups
			if height_group: height_group.add(vertex_ids, height, 'REPLACE')
			if width_group: width_group.add(vertex_ids, width, 'REPLACE')
			if angle_group: angle_group.add(vertex_ids, angle, 'REPLACE')

			if phaenotyp.calculation_type != "force_distribution":
				# get forcetyp and force
				result = member[phaenotyp.forces_pn]

				for i in range(11):
					position = member["deflection"][str(frame)][i]
					x = position[0]*(1-viz_deflection) + member["initial_positions"][str(frame)][10-i][0]*viz_deflection
					y = position[1]*(1-viz_deflection) + member["initial_positions"][str(frame)][10-i][1]*viz_deflection
					z = position[2]*(1-viz_deflection) + member["initial_positions"][str(frame)][10-i][2]*viz_deflection
					vertices[mesh_vertex_ids[i]].co = (x,y,z)
					
					overstress = member["overstress"][str(frame)]
					
					# if utilization in viz
					if phaenotyp.forces_pn == "utilization":
						force = result[str(frame)] - 1
						color = rainbow(force, overstress, viz_boundaries_members, viz_scale)

					# for 11 entries
					else:
						# for all forces with 10 entries
						# 10th value is the same like 11th entrie
						# it should be ok for the viz only
						# report is showing all entries
						if len(result[str(frame)]) < 11 and i == 10:
							force = result[str(frame)][9]
						else:
							force = result[str(frame)][i]
						
						color = rainbow(force, overstress, viz_boundaries_members, viz_scale)

					attribute.data[mesh_vertex_ids[i]].color = color
				
			# for force disbribution
			else:
				# get forcetyp and force
				result = member[phaenotyp.forces_fd]

				for i in range(2):
					# apply transformation
					x = member["initial_positions"][str(frame)][i][0]
					y = member["initial_positions"][str(frame)][i][1]
					z = member["initial_positions"][str(frame)][i][2]
					vertices[mesh_vertex_ids[i]].co = (x,y,z)

					force = result[str(frame)]
					overstress = member["overstress"][str(frame)]
					color = rainbow(force, overstress, viz_boundaries_members, viz_scale)
					attribute.data[mesh_vertex_ids[i]].color = color

	# update quads
	quads = data.get("quads")
	if quads:
		structure_obj_vertices = data["structure"]
		mesh_for_viz = bpy.data.objects["<Phaenotyp>quads_" + str(scene_id)]
		vertices = mesh_for_viz.data.vertices
		faces = mesh_for_viz.data.polygons

		thickness_group = mesh_for_viz.vertex_groups.get("thickness")
		
		attribute_1 = mesh_for_viz.data.attributes.get("force_1")
		attribute_2 = mesh_for_viz.data.attributes.get("force_2")
		
		# for both sides
		nodes_1 = [[] for i in range(len(vertices))]
		nodes_2 = [[] for i in range(len(vertices))]
		
		# list of overstressed node_ids
		# if a quad is overstressed, all nodes are drawn darker
		overstressed = []
		
		# list of thickness for with each connected quad
		thickness = [[] for i in range(len(vertices))]
		
		for id, quad in quads.items():
			id = int(id)
			
			# get selected forcetyp and force
			result_1 = quad[str(phaenotyp.forces_quads) + "_1"]
			result_2 = quad[str(phaenotyp.forces_quads) + "_2"]
			force_1 = result_1[str(frame)]
			force_2 = result_2[str(frame)]
			
			# append forces to nodes to create average afterwards
			keys = quad["vertices_ids_viz"]
			for key in keys:
				nodes_1[key].append(force_1)
				nodes_2[key].append(force_2)

			for i in range(4):
				position = quad["deflection"][str(frame)][i]
				x = position[0]*(1-viz_deflection) + quad["initial_positions"][str(frame)][i][0]*viz_deflection
				y = position[1]*(1-viz_deflection) + quad["initial_positions"][str(frame)][i][1]*viz_deflection
				z = position[2]*(1-viz_deflection) + quad["initial_positions"][str(frame)][i][2]*viz_deflection
				
				# get node of the corresponding vertex id of the viz mesh
				node_id = quad["vertices_ids_viz"][i]
				vertices[node_id].co = (x,y,z)
			
				t = quad["thickness"][str(frame)] * 0.01
				thickness[node_id].append(t)
			
			if quad["overstress"][str(frame)]:
				for key in keys:
					overstressed.append(key)
		
		# get average of thickness for each connecting quad
		for i, t in enumerate(thickness):
			t = sum(t) / len(t)
			
			# apply to each vertex
			thickness_group.add([i], t, 'REPLACE')
		
		viz_factor = 1
		# side 1	
		for i, forces in enumerate(nodes_1):
			try:
				force = sum(forces) / len(forces)
			except:
				force = 0
			
			if i in overstressed:
				overstress = True
			else:
				overstress = False
			
			color = rainbow(force, overstress, viz_boundaries_quads, viz_scale)

			# colorize faces
			attribute_1.data[i].color = color

		# side 2
		for i, forces in enumerate(nodes_2):
			try:
				force = sum(forces) / len(forces)
			except:
				force = 0

			if i in overstressed:
				overstress = True
			else:
				overstress = False
			
			color = rainbow(force, overstress, viz_boundaries_quads, viz_scale)

			# colorize faces
			attribute_2.data[i].color = color

		# change stresslines
		quads_viz = bpy.data.objects["<Phaenotyp>quads_" + str(scene_id)]
		quads_vertices = quads_viz.data.vertices
		quads_faces = quads_viz.data.polygons
		
		stress_viz = bpy.data.objects["<Phaenotyp>stresslines_" + str(scene_id)]
		stress_vertices = stress_viz.data.vertices
		
		attribute = stress_viz.data.attributes.get("stressline")
		
		# update radius scale
		viz_stressline_scale = phaenotyp.viz_stressline_scale * 0.01
		radius_group = stress_viz.vertex_groups.get("radius")
		
		for id, quad in quads.items():
			face = quads_faces[quad["face_id_viz"]]
			normal = face.normal
			center = face.center
			thickness = quad["thickness"][str(frame)] * 0.01
			overstress = quad["overstress"][str(frame)]
			
			v_0 = quad["vertices_ids_viz"][0]
			v_1 = quad["vertices_ids_viz"][1]
			v_2 = quad["vertices_ids_viz"][2]
			v_3 = quad["vertices_ids_viz"][3]
			
			v_0_co = quads_vertices[v_0].co
			v_1_co = quads_vertices[v_1].co
			v_2_co = quads_vertices[v_2].co
			v_3_co = quads_vertices[v_3].co
				
			e_0 = (v_1_co + v_0_co) / 2
			e_1 = (v_3_co + v_2_co) / 2

			mid = (e_1 + e_0) / 2
			t = e_1 - e_0
			t = t*viz_stressline_length/200
			
			a_1_1 = quad["alpha_1"][str(frame)]
			a_2_1 = a_1_1 + 90
			a_1_2 = quad["alpha_2"][str(frame)]
			a_2_2 = a_1_1 + 90
			
			s_1_1 = quad["s_1_1"][str(frame)]
			s_2_1 = quad["s_2_1"][str(frame)]
			s_1_2 = quad["s_1_2"][str(frame)]
			s_2_2 = quad["s_2_2"][str(frame)]
			
			o_1_1 = 0
			o_2_1 = 0
			o_1_2 = thickness
			o_2_2 = thickness
			
			v_1_1 = [0,1]
			v_2_1 = [4,5]
			v_1_2 = [2,3]
			v_2_2 = [6,7]
			
			a = [a_1_1, a_2_1, a_1_2, a_2_2] # alphas
			s = [s_1_1, s_2_1, s_1_2, s_2_2] # forces
			o = [o_1_1, o_2_1, o_1_2, o_2_2] # offset
			v = [v_1_1, v_2_1, v_1_2, v_2_2] # vertex
			
			for i in range(4):
				mat = Matrix.Rotation(radians(a[i]), 4, normal)
				vec = Vector(t)
				vec.rotate(mat)
				
				i_0 = v[i][0]
				i_1 = v[i][1]
				
				# set radius
				r = abs(s[i]) * viz_stressline_scale
				ids = [quad["stresslines_viz"][i_0], quad["stresslines_viz"][i_1]]
				radius_group.add(ids, r, 'REPLACE')
				
				# set color
				color = red_blue(s[i], overstress, viz_boundaries_quads, viz_scale)
				attribute.data[quad["stresslines_viz"][i_0]].color = color
				attribute.data[quad["stresslines_viz"][i_1]].color = color
					
				# set position of first edge			
				stress_vertices[quad["stresslines_viz"][i_0]].co = mid - vec - normal * o[i]
				stress_vertices[quad["stresslines_viz"][i_1]].co = mid + vec - normal * o[i]
			
def create_loads(structure_obj, loads_v, loads_e, loads_f):
	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = structure_obj.matrix_world
	
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	scene_id = data["scene_id"]
	
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type

	for id, load in loads_v.items():
		id = int(id)

		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		v = mat @ structure_obj.data.vertices[id].co

		x = v[0] # text pos x
		y = v[1] # text pos y
		z = v[2] # text pos z

		name = "<Phaenotyp>support_" + str(id)
		font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>load_text")

		text = "" + "\n"

		text = text + "Type: vertices\n"
		text = text + "FX: " + str(load[0]) + "\n"
		text = text + "FY: " + str(load[1]) + "\n"
		text = text + "FZ: " + str(load[2]) + "\n"
		
		if calculation_type not in ["geometrical", "force_distribution"]:
			text = text + "MX: " + str(load[3]) + "\n"
			text = text + "MY: " + str(load[4]) + "\n"
			text = text + "MZ: " + str(load[5]) + "\n"
		
		font_curve.body = text
		obj = bpy.data.objects.new(name="<Phaenotyp>load_" + str(scene_id), object_data=font_curve)

		# set scale and position
		obj.location = x, y, z
		obj.scale = 0.1, 0.1, 0.1

		# link object to collection
		bpy.data.collections["<Phaenotyp>" + str(scene_id)].objects.link(obj)

	for id, load in loads_e.items():
		id = int(id)
		vertex_0_id = structure_obj.data.edges[id].vertices[0]
		vertex_1_id = structure_obj.data.edges[id].vertices[1]

		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		vertex_0 = mat @ structure_obj.data.vertices[vertex_0_id].co
		vertex_1 = mat @ structure_obj.data.vertices[vertex_1_id].co

		mid = (vertex_0 + vertex_1) / 2

		x = mid[0] # text pos x
		y = mid[1] # text pos y
		z = mid[2] # text pos z

		name = "<Phaenotyp>support_" + str(id)
		font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>load_text")

		text = "" + "\n"

		text = text + "Type: edges\n"
		text = text + "FX: " + str(load[0]) + "\n"
		text = text + "FY: " + str(load[1]) + "\n"
		text = text + "FZ: " + str(load[2]) + "\n"
		
		if calculation_type not in ["geometrical", "force_distribution"]:
			text = text + "Fx: " + str(load[3]) + "\n"
			text = text + "Fy: " + str(load[4]) + "\n"
			text = text + "Fz: " + str(load[5]) + "\n"
		
		font_curve.body = text
		obj = bpy.data.objects.new(name="<Phaenotyp>load_" + str(scene_id), object_data=font_curve)

		# set scale and position
		obj.location = x, y, z
		obj.scale = 0.1, 0.1, 0.1

		# link object to collection
		bpy.data.collections["<Phaenotyp>" + str(scene_id)].objects.link(obj)

	for id, load in loads_f.items():
		id = int(id)

		face = structure_obj.data.polygons[id]

		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		center = mat @ face.center

		x = center[0] # text pos x
		y = center[1] # text pos y
		z = center[2] # text pos z

		name = "<Phaenotyp>support_" + str(id)
		font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>load_text")

		text = "" + "\n"

		text = text + "Type: faces\n"
		text = text + "n: " + str(load[0]) + "\n"
		text = text + "p: " + str(load[1]) + "\n"
		text = text + "z: " + str(load[2]) + "\n"

		font_curve.body = text
		obj = bpy.data.objects.new(name="<Phaenotyp>load_" + str(scene_id), object_data=font_curve)

		# set scale and position
		obj.location = x, y, z
		obj.scale = 0.1, 0.1, 0.1

		# link object to collection
		bpy.data.collections["<Phaenotyp>" + str(scene_id)].objects.link(obj)

def create_diagram(self, context):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	
	data = bpy.context.scene['<Phaenotyp>']
	scene_id = data["scene_id"]
	individuals = data["individuals"]
	
	fitness = phaenotyp.diagram_fitness
	key_0 = phaenotyp.diagram_key_0
	key_1 = phaenotyp.diagram_key_1
	
	chromosome = individuals["0"]["chromosome"]

	diagram_name = "<Phaenotyp>diagram_" + str(scene_id)
	
	fitness_available = individuals["0"]["fitness"].get(fitness)
	if fitness_available:
		if len(chromosome) > key_0 and len(chromosome) > key_1:
			# delete current obj and mesh
			obj = bpy.data.objects.get(diagram_name)
			if obj:
				bpy.data.objects.remove(obj, do_unlink=True)

			mesh = bpy.data.meshes.get(diagram_name)
			if mesh:
				bpy.data.meshes.remove(mesh, do_unlink=True)
			
			# delete labels
			for obj in bpy.data.objects:
				if "<Phaenotyp>diagram_label_" + str(scene_id) in obj.name_full:
					bpy.data.objects.remove(obj, do_unlink=True)
			
			# create mesh and object
			mesh = bpy.data.meshes.new(diagram_name)
			obj = bpy.data.objects.new(mesh.name, mesh)
			col = bpy.data.collections.get("<Phaenotyp>" + str(scene_id))
			col.objects.link(obj)
			bpy.context.view_layer.objects.active = obj
			scene = bpy.context.scene
			phaenotyp = scene.phaenotyp
			frame = scene.frame_current
			
			data = scene["<Phaenotyp>"]
			individuals = data["individuals"]
			
			# list for geometry
			verts = []
			edges = []
			faces = []
			
			len_verts = 0
			
			values = []
			
			for id, individual in individuals.items():
				x = individual["chromosome"][key_0]
				y = individual["chromosome"][key_1]
				z = individual["fitness"][fitness]
				values.append(z)
				
				verts.append([x,y,0])
				verts.append([x,y,z])
				
				edge = [len_verts, len_verts+1]
				edges.append(edge)
				
				len_verts += 2
			
			mesh.from_pydata(verts, edges, faces)
			
			# create vertex_color
			attribute = obj.data.attributes.get("diagram")
			if attribute:
				text = "existing attribute:" + str(attribute)
			else:
				bpy.ops.geometry.color_attribute_add(name="diagram", domain='POINT', data_type='FLOAT_COLOR', color=(255, 0, 255, 1))

			# create material
			material_name =  "<Phaenotyp>diagram_" + str(scene_id)
			stressline_material = bpy.data.materials.get(material_name)
			if stressline_material == None:
				mat = bpy.data.materials.new(material_name)
				
				mat.use_nodes = True
				nodetree = mat.node_tree

				# add color attribute
				ca = nodetree.nodes.new(type="ShaderNodeVertexColor")

				# set group
				ca.layer_name = "diagram"

				# connect to color attribute to base color
				input = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']
				output = ca.outputs['Color']
				nodetree.links.new(input, output)

			obj.data.materials.append(bpy.data.materials.get(material_name))
			obj.active_material_index = len(obj.data.materials) - 1
			
			# create modifiere if not existing
			modifier = obj.modifiers.get(diagram_name)
			if modifier is None:
				modifier = obj.modifiers.new(name=diagram_name, type='NODES')

			node_group = bpy.data.node_groups.get(diagram_name)
			if node_group is None:
				node_group = bpy.data.node_groups.new(diagram_name, "GeometryNodeTree")

				# alte Default-Nodes löschen, falls Blender welche anlegt
				for n in list(node_group.nodes):
					node_group.nodes.remove(n)

				# group input und output
				group_in = node_group.nodes.new("NodeGroupInput")
				group_in.location = (-600, 0)

				group_out = node_group.nodes.new("NodeGroupOutput")
				group_out.location = (600, 0)

				# sicherstellen, dass es einen Geometry Ein und Ausgang gibt
				if "Geometry" not in node_group.interface.items_tree:
					node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
					node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

				# mesh to curve
				mtc = node_group.nodes.new(type="GeometryNodeMeshToCurve")
				mtc.location = (-350, 0)

				# curve circle
				cc = node_group.nodes.new(type="GeometryNodeCurvePrimitiveCircle")
				cc.location = (-350, -220)
				cc.inputs[0].default_value = 8
				cc.inputs[4].default_value = 0.05

				# curve to mesh
				ctm = node_group.nodes.new(type="GeometryNodeCurveToMesh")
				ctm.location = (-80, 0)
				ctm.inputs[3].default_value = True

				# set material
				gnsm = node_group.nodes.new(type="GeometryNodeSetMaterial")
				gnsm.location = (250, 0)
				gnsm.inputs[2].default_value = bpy.data.materials["<Phaenotyp>diagram_" + str(scene_id)]

				# links
				node_group.links.new(mtc.inputs[0], group_in.outputs["Geometry"])
				node_group.links.new(ctm.inputs[0], mtc.outputs[0])
				node_group.links.new(ctm.inputs[1], cc.outputs[0])
				node_group.links.new(gnsm.inputs[0], ctm.outputs[0])
				node_group.links.new(group_out.inputs["Geometry"], gnsm.outputs[0])

			modifier.node_group = node_group

			# create vertex_group for radius
			# radius is automatically choosen by geometry nodes for radius-input
			bpy.ops.object.mode_set(mode = 'OBJECT')
			radius_group = obj.vertex_groups.get("radius")
			if not radius_group:
				radius_group = obj.vertex_groups.new(name="radius")
			
			# set scale to match z size
			#scale = basics.return_max_diff_to_zero([1, obj.dimensions[2]])
			#obj.dimensions[2] = scale
			
			obj.scale[2] = phaenotyp.diagram_scale
			
			# change radius
			ids = [i for i in range(len(obj.data.vertices))]
			radius_group.add(ids, 0.5, 'REPLACE')
			
			ids = ids[0::2]
			radius_group.add(ids, 0.1, 'REPLACE')
			
			# change color
			attribute = obj.data.attributes.get("diagram")
			
			min_v = min(values)
			max_v = max(values)
			
			for i, v in enumerate(values):
				v = basics.remap(v, min_v, max_v, 0, 1)
				
				v_0_id = i*2
				v_1_id = v_0_id + 1
				
				attribute.data[v_0_id].color = [1-v, 0, v, 1]
				attribute.data[v_1_id].color = [1-v, 0, v, 1]
			
			scale = 0.05
			
			# create text for x
			for i in range(0, 11):
				x = round(i*0.1, 1)
				font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>diagram_" + str(scene_id))
				font_curve.body = str(x)
				font_curve.align_x = 'LEFT'
				font_curve.align_y = 'CENTER'
				obj = bpy.data.objects.new(name="<Phaenotyp>diagram_label_" + str(scene_id), object_data=font_curve)
				obj.location = x, -0.1, 0
				obj.scale = [scale, scale, scale]
				obj.rotation_euler[2] = -1.5708
				bpy.data.collections["<Phaenotyp>" + str(scene_id)].objects.link(obj)

			# create label for x
			font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>diagram_" + str(scene_id))
			font_curve.body = "Shape-key = " + str(key_0)
			font_curve.align_x = 'LEFT'
			font_curve.align_y = 'CENTER'
			obj = bpy.data.objects.new(name="<Phaenotyp>diagram_label_" + str(scene_id), object_data=font_curve)
			obj.location = 0, -0.25, 0
			obj.scale = [scale, scale, scale]
			bpy.data.collections["<Phaenotyp>" + str(scene_id)].objects.link(obj)

			# create text for y
			for i in range(0, 11):
				y = round(i*0.1, 1)
				font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>diagram_" + str(scene_id))
				font_curve.body = str(y)
				font_curve.align_x = 'RIGHT'
				font_curve.align_y = 'CENTER'
				obj = bpy.data.objects.new(name="<Phaenotyp>diagram_label_" + str(scene_id), object_data=font_curve)
				obj.location = -0.1, y, 0
				obj.scale = [scale, scale, scale]
				bpy.data.collections["<Phaenotyp>" + str(scene_id)].objects.link(obj)

			# create label for y
			font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>diagram_" + str(scene_id))
			font_curve.body = "Shape-key = " + str(key_1)
			font_curve.align_x = 'LEFT'
			font_curve.align_y = 'CENTER'
			obj = bpy.data.objects.new(name="<Phaenotyp>diagram_label_" + str(scene_id), object_data=font_curve)
			obj.location = -0.25, 1, 0
			obj.scale = [scale, scale, scale]
			obj.rotation_euler[2] = -1.5708
			bpy.data.collections["<Phaenotyp>" + str(scene_id)].objects.link(obj)
