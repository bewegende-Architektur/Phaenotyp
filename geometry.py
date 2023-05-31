import bpy
import bmesh
from math import sqrt, pi
from phaenotyp import operators
from mathutils import Color, Vector
c = Color()

# variable to pass all stuff that needs to be fixed
to_be_fixed = None

def amount_of_mesh_parts():
	'''
	Is checking for the amount of parts in the mesh. Is based on the answer from BlackCutpoint
	https://blender.stackexchange.com/questions/75332/how-to-find-the-number-of-loose-parts-with-blenders-python-api
	:return len(parts): Is returning the amount of parts as integer. 
	'''
	obj = bpy.context.object
	mesh = obj.data
	paths = {v.index:set() for v in mesh.vertices}

	for e in mesh.edges:
		paths[e.vertices[0]].add(e.vertices[1])
		paths[e.vertices[1]].add(e.vertices[0])

	parts = []

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

		parts.append(part)

	return len(parts)

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
				
				if v.length < 0.001:
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

def delete_selected_faces():
	'''
	Is handling the mode-switch and deletes all selected faces.
	'''
	obj = bpy.context.active_object
	bpy.ops.object.mode_set(mode = 'OBJECT')
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
	mesh = bpy.data.meshes.new("<Phaenotyp>support")
	obj = bpy.data.objects.new(mesh.name, mesh)
	col = bpy.data.collections.get("<Phaenotyp>")
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
	mesh = bpy.data.meshes.new("<Phaenotyp>member")
	obj = bpy.data.objects.new(mesh.name, mesh)
	col = bpy.data.collections.get("<Phaenotyp>")
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
	name = "<Phaenotyp>member"
	existing = bpy.data.materials.get("<Phaenotyp>member")
	if existing == None:
		mat = bpy.data.materials.new(name)
		obj.data.materials.append(mat)
		obj.active_material_index = len(obj.data.materials) - 1

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

	# create modifiere if not existing
	modifier = obj.modifiers.get('<Phaenotyp>')
	if modifier:
		text = "existing modifier:" + str(modifiers)
	else:
		modifier_nodes = obj.modifiers.new(name="<Phaenotyp>", type='NODES')
		bpy.ops.node.new_geometry_node_group_assign()
		nodes = obj.modifiers['<Phaenotyp>'].node_group

		# set name to group
		if nodes.name == "<Phaenotyp>Nodes":
			node_group = bpy.data.node_groups['<Phaenotyp>Nodes']
		else:
			nodes.name = "<Phaenotyp>Nodes"
			node_group = bpy.data.node_groups['<Phaenotyp>Nodes']

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

		# profile to curve
		cc = node_group.nodes.new(type="GeometryNodeCurvePrimitiveCircle")
		cc.inputs[0].default_value = 8 # set amount of vertices of circle
		input = ctm.inputs[1] # curve to mesh, profile curve
		output = cc.outputs[0] # curve circe, curve
		node_group.links.new(input, output)

		# set material
		gnsm = node_group.nodes.new(type="GeometryNodeSetMaterial")
		gnsm.inputs[2].default_value = bpy.data.materials["<Phaenotyp>member"]
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

	# assign to group
	for id, member in members.items():
		id = str(id)
		vertex_ids = member["mesh_vertex_ids"]

		# copy Do and Di if not set by optimization
		# or the user changed the frame during optimization
		if str(frame) not in member["Do"]:
			member["Do"][str(frame)] = member["Do_first"]
			member["Di"][str(frame)] = member["Di_first"]

		radius = member["Do"][str(frame)]*0.01
		radius_group.add(vertex_ids, radius, 'REPLACE')

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

def update_members_pre():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	structure_obj_vertices = data["structure"]
	frame = bpy.context.scene.frame_current
	mesh_for_viz = bpy.data.objects["<Phaenotyp>member"]
	vertices = mesh_for_viz.data.vertices

	radius_group = mesh_for_viz.vertex_groups.get("radius")
	attribute = mesh_for_viz.data.attributes.get("force")

	for id, member in members.items():
		id = int(id)

		# copy properties if not set by optimization
		# or the user changed the frame during optimization
		if str(frame) not in member["Do"]:
			member["Do"][str(frame)] = member["Do_first"]
			member["Di"][str(frame)] = member["Di_first"]

		# update material (like updated when passed from gui in material.py)
		member["Iy"][str(frame)] = pi * (member["Do"][str(frame)]**4 - member["Di"][str(frame)]**4)/64
		member["Iz"][str(frame)] = member["Iy"][str(frame)]
		member["J"][str(frame)]  = pi * (member["Do"][str(frame)]**4 - member["Di"][str(frame)]**4)/(32)
		member["A"][str(frame)]  = ((pi * (member["Do"][str(frame)]*0.5)**2) - (pi * (member["Di"][str(frame)]*0.5)**2))
		member["kg_A"][str(frame)] =  member["A"][str(frame)]*member["d"] * 0.1
		member["ir"][str(frame)] = sqrt(member["Iy"][str(frame)]/member["A"][str(frame)])
	
	update_translation()
		
def update_members_post():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	structure_obj_vertices = data["structure"]
	frame = bpy.context.scene.frame_current
	mesh_for_viz = bpy.data.objects["<Phaenotyp>member"]
	vertices = mesh_for_viz.data.vertices

	radius_group = mesh_for_viz.vertex_groups.get("radius")
	attribute = mesh_for_viz.data.attributes.get("force")
			
	for id, member in members.items():
		id = int(id)

		mesh_vertex_ids = member["mesh_vertex_ids"]

		# update radius
		vertex_ids = member["mesh_vertex_ids"]
		radius = member["Do"][str(frame)]*0.01
		radius_group.add(vertex_ids, radius, 'REPLACE')

		if phaenotyp.calculation_type != "force_distribution":
			# get forcetyp and force
			result = member[phaenotyp.forces_pn]

			for i in range(11):
				position = member["deflection"][str(frame)][i]
				f = phaenotyp.viz_deflection * 0.01
				x = position[0]*(1-f) + member["initial_positions"][str(frame)][10-i][0]*f
				y = position[1]*(1-f) + member["initial_positions"][str(frame)][10-i][1]*f
				z = position[2]*(1-f) + member["initial_positions"][str(frame)][10-i][2]*f
				vertices[mesh_vertex_ids[i]].co = (x,y,z)

				# if utilization in viz
				if phaenotyp.forces_pn == "utilization":
					# red or blue?
					force = result[str(frame)] - 1
					if force > 0:
						h = 0
					else:
						h = 0.666

					# define s
					s = 1 * abs(force) * phaenotyp.viz_scale * 0.01

					# define v
					if member["overstress"][str(frame)] == True:
						v = 0.25
					else:
						v = 1.0

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

					# red or blue?
					if force > 0:
						h = 0
					else:
						h = 0.666

					# define s
					s = 1 * abs(force) * phaenotyp.viz_scale * 0.01

					# define v
					if member["overstress"][str(frame)] == True:
						v = 0.25
					else:
						v = 1.0

				c.hsv = h,s,v
				attribute.data[mesh_vertex_ids[i]].color = [c.r, c.g, c.b, 1.0]

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

				# red or blue?
				force = result[str(frame)]

				if force > 0:
					h = 0
				else:
					h = 0.666

				# define s
				s = 1 * abs(force) * phaenotyp.viz_scale * 0.01

				# define v
				if member["overstress"][str(frame)] == True:
					v = 0.25
				else:
					v = 1.0

				c.hsv = h,s,v
				attribute.data[mesh_vertex_ids[i]].color = [c.r, c.g, c.b, 1.0]

def create_loads(structure_obj, loads_v, loads_e, loads_f):
	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = structure_obj.matrix_world

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

		text = text + "type: vertices\n"
		text = text + "x: " + str(load[0]) + "\n"
		text = text + "y: " + str(load[1]) + "\n"
		text = text + "z: " + str(load[2]) + "\n"

		font_curve.body = text
		obj = bpy.data.objects.new(name="<Phaenotyp>load", object_data=font_curve)

		# set scale and position
		obj.location = x, y, z
		obj.scale = 0.1, 0.1, 0.1

		# link object to collection
		bpy.data.collections["<Phaenotyp>"].objects.link(obj)

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

		text = text + "type: edges\n"
		text = text + "x: " + str(load[0]) + "\n"
		text = text + "y: " + str(load[1]) + "\n"
		text = text + "z: " + str(load[2]) + "\n"

		font_curve.body = text
		obj = bpy.data.objects.new(name="<Phaenotyp>load", object_data=font_curve)

		# set scale and position
		obj.location = x, y, z
		obj.scale = 0.1, 0.1, 0.1

		# link object to collection
		bpy.data.collections["<Phaenotyp>"].objects.link(obj)

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

		text = text + "type: faces\n"
		text = text + "n: " + str(load[0]) + "\n"
		text = text + "p: " + str(load[1]) + "\n"
		text = text + "z: " + str(load[2]) + "\n"

		font_curve.body = text
		obj = bpy.data.objects.new(name="<Phaenotyp>load", object_data=font_curve)

		# set scale and position
		obj.location = x, y, z
		obj.scale = 0.1, 0.1, 0.1

		# link object to collection
		bpy.data.collections["<Phaenotyp>"].objects.link(obj)
