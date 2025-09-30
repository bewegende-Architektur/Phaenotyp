import bpy
import bmesh

import sys
import os
path_addons = os.path.dirname(__file__) # path to the folder of addons
path_phaenotyp = path_addons + "/phaenotyp"
sys.path.append(path_addons)
from Pynite import FEModel3D
from Pynite.Section import Section

from numpy import array, empty, append, poly1d, polyfit, linalg, zeros, intersect1d, arctan, sin, cos
from phaenotyp import basics, material, geometry
from math import sqrt, tanh, pi, degrees, radians

from subprocess import Popen, PIPE
import pickle
import gc
gc.disable()

def check_scipy():
	"""
	Checking if scipy is available and is setting the value to data.
	"""
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]

	try:
		import scipy
		data["scipy_available"] = True

	except:
		data["scipy_available"] = False

def replace_data(entry):
	'''
	Will set a new entry in data.
	This is importand for setting new loads every frame et cetera.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type
	data = scene["<Phaenotyp>"]

	# extract key and value
	key, value = entry

	# clear and set again
	data[key] = {}
	data[key] = value

def prepare_fea_pn(frame):
	'''
	Is preparing the calculaton of the current frame for for PyNite.
	:return model: FEModel3D function of PyNite
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type
	data = scene["<Phaenotyp>"]

	supports = data["supports"]
	members = data["members"]
	quads = data["quads"]
	loads_v = data["loads_v"]
	loads_e = data["loads_e"]
	loads_f = data["loads_f"]

	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()

	geometry.update_geometry_pre()

	model = FEModel3D()
	basics.timer.start()

	psf_members = phaenotyp.psf_members
	psf_quads = phaenotyp.psf_quads
	psf_loads = phaenotyp.psf_loads

	for mat in material.library:
		name = mat[0]
		E = mat[2]
		G = mat[3]
		nu = None # replace later
		rho = None # replace later
		model.add_material(name, E, G, nu, rho)

	# apply chromosome if available
	individuals = data.get("individuals")
	if individuals:
		shape_keys = data["structure"].data.shape_keys.key_blocks
		chromosome = individuals[str(frame)]["chromosome"]
		geometry.set_shape_keys(shape_keys, chromosome)

	# get absolute position of vertex (when using shape-keys, animation et cetera)
	dg = bpy.context.evaluated_depsgraph_get()
	obj = data["structure"].evaluated_get(dg)

	mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)

	vertices = mesh.vertices
	edges = mesh.edges
	faces = mesh.polygons

	# to be collected:
	data["frames"][str(frame)] = {}
	frame_volume = 0
	frame_area = 0
	frame_length = 0
	frame_weight = 0
	frame_rise = 0
	frame_span = 0
	frame_cantilever = 0

	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = obj.matrix_world

	# add nodes from vertices
	for vertex in vertices:
		vertex_id = vertex.index
		name = str(vertex_id)

		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		v = mat @ vertex.co

		# apply to all vertices to work for edges and faces also
		vertex.co = v

		x = v[0] * 100 # convert to cm for calculation
		y = v[1] * 100 # convert to cm for calculation
		z = v[2] * 100 # convert to cm for calculation

		# only create Node if needed for the model
		create = False
		for member_id, member in members.items():
			if vertex_id in [member["vertex_0_id"], member["vertex_1_id"]]:
				create = True
				break

		for quad_id, quad in quads.items():
			if vertex_id in quad["vertices_ids_structure"]:
				create = True
				break

		if create:
			model.add_node(name, x,y,z)

	# define support
	for id, support in supports.items():
		model.def_support(id, support[0], support[1], support[2], support[3], support[4], support[5])

	# create members
	for id, member in members.items():
		vertex_0_id = member["vertex_0_id"]
		vertex_1_id = member["vertex_1_id"]

		v_0 = vertices[vertex_0_id].co
		v_1 = vertices[vertex_1_id].co

		# save initial_positions to mix with deflection
		initial_positions = []
		for i in range(11):
			position = (v_0*(i) + v_1*(10-i))*0.1
			x = position[0]
			y = position[1]
			z = position[2]
			initial_positions.append([x,y,z])
		member["initial_positions"][str(frame)] = initial_positions

		node_0 = str(vertex_0_id)
		node_1 = str(vertex_1_id)
		material_name = member["material_name"]

		if member["member_type"] == "full":
			tension_only = False
			comp_only = False

		if member["member_type"] == "tension_only":
			tension_only = True
			comp_only = False

		if member["member_type"] == "comp_only":
			tension_only = False
			comp_only = True

		# create a section for every member
		# the id is similar to the member id
		section = Section(
			model, id,
			A = member["A"][str(frame)],
			Iz = member["Iz"][str(frame)],
			Iy = member["Iy"][str(frame)],
			J = member["J"][str(frame)])

		model.sections[id] = section

		model.add_member(
			id,	node_0, node_1,
			member["material_name"], id,
			tension_only=tension_only,
			comp_only=comp_only
		)

		# release Moments
		if phaenotyp.type_of_joints == "release_moments":
			model.def_releases(id,
				False, False, False, False, True, True,
				False, False, False, False, True, True)

		# add self weight
		weight_A = member["weight_A"][str(frame)]
		kN = weight_A * -0.0000981

		# add self weight as distributed load
		model.add_member_dist_load(id, "FZ", kN*psf_members, kN*psf_members)

		# calculate lenght of parts (maybe usefull later ...)
		length = (v_0 - v_1).length
		frame_length += length

		# calculate and add weight to overall weight of structure
		weight = length * weight_A
		frame_weight += weight

		# store in member
		member["weight"][str(frame)] = weight
		member["length"][str(frame)] = length

	# create quads
	for id, quad in quads.items():
		E = quad["E"]
		G = quad["G"]
		nu = quad["nu"]
		rho = quad["rho"]

		# unique name of the material trough parameters
		material_name = (
			"material_" +
			"E" + "_" +
			"G" + "_" +
			"nu" +  "_" +
			"rho")

		if material_name not in model.materials:
			model.add_material(material_name, E, G, nu, rho)

		vertex_ids = quad["vertices_ids_structure"]

		# get thickness of frame or first
		t = quad["thickness"].get(str(frame))

		v_0 = str(vertex_ids[0])
		v_1 = str(vertex_ids[1])
		v_2 = str(vertex_ids[2])
		v_3 = str(vertex_ids[3])

		model.add_quad(id, v_0, v_1, v_2, v_3, t, material_name, kx_mod=1.0, ky_mod=1.0)

		# save position before to morph with deflection afterwards
		initial_positions = [
			vertices[vertex_ids[0]].co,
			vertices[vertex_ids[1]].co,
			vertices[vertex_ids[2]].co,
			vertices[vertex_ids[3]].co,
			]
		quad["initial_positions"][str(frame)] = initial_positions

		# self weight
		face = data["structure"].data.polygons[int(id)]
		area = face.area
		weight_A = t * rho
		weight = weight_A * area * 10000 # in cm
		for vertex_id in quads[id]["vertices_ids_structure"]:
			vertex_id = str(vertex_id)
			# area * thickness * density * 0.25 (to distribute to all four faces) - for gravity
			z = weight * (-0.25)
			model.add_node_load(vertex_id, 'FZ', z * 0.00000981 * psf_quads) # to cm and force

		quad["area"][str(frame)] = area # in m²
		quad["weight_A"][str(frame)] = t * weight_A
		quad["weight"][str(frame)] = weight_A * area # in kg

		frame_weight += weight_A * area # in kg

	# add loads
	for id, load in loads_v.items():
		model.add_node_load(id, 'FX', load[0] * psf_loads)
		model.add_node_load(id, 'FY', load[1] * psf_loads)
		model.add_node_load(id, 'FZ', load[2] * psf_loads)

		model.add_node_load(id, 'MX', load[3] * psf_loads)
		model.add_node_load(id, 'MY', load[4] * psf_loads)
		model.add_node_load(id, 'MZ', load[5] * psf_loads)

	for id, load in loads_e.items():
		model.add_member_dist_load(id, 'FX', load[0]*0.01 * psf_loads, load[0]*0.01 * psf_loads) # m to cm
		model.add_member_dist_load(id, 'FY', load[1]*0.01 * psf_loads, load[1]*0.01 * psf_loads) # m to cm
		model.add_member_dist_load(id, 'FZ', load[2]*0.01 * psf_loads, load[2]*0.01 * psf_loads) # m to cm

		model.add_member_dist_load(id, 'Fx', load[3]*0.01 * psf_loads, load[3]*0.01 * psf_loads) # m to cm
		model.add_member_dist_load(id, 'Fy', load[4]*0.01 * psf_loads, load[4]*0.01 * psf_loads) # m to cm
		model.add_member_dist_load(id, 'Fz', load[5]*0.01 * psf_loads, load[5]*0.01 * psf_loads) # m to cm

	for id, load in loads_f.items():
		# apply force to quad if a quad is available
		quad = quads.get(str(id))
		if quad:
			# int(id), otherwise crashing Speicherzugriffsfehler
			face = data["structure"].data.polygons[int(id)]
			normal = face.normal

			edge_keys = face.edge_keys
			area = face.area # in m²

			load_normal = load[0]
			load_projected = load[1]
			load_area_z = load[2]

			area_projected = geometry.area_projected(face, vertices)

			# a quad is available to apply forces to
			for vertex_id in quads[id]["vertices_ids_structure"]:
				vertex_id = str(vertex_id)
				x,y,z = 0,0,0

				# load normal
				area_load = load_normal * area
				x += area_load * normal[0]
				y += area_load * normal[1]
				z += area_load * normal[2]

				# load projected
				area_load = load_projected * area_projected
				z += area_load * 0.25 # divided by four points of each quad

				# load z
				area_load = load_area_z * area
				z += area_load * 0.25 # divided by four points of each quad

				model.add_node_load(vertex_id, 'FX', x * psf_loads) # to cm
				model.add_node_load(vertex_id, 'FY', y * psf_loads) # to cm
				model.add_node_load(vertex_id, 'FZ', z * psf_loads) # to cm

		# apply force to members
		else:
			# int(id), otherwise crashing Speicherzugriffsfehler
			face = data["structure"].data.polygons[int(id)]
			normal = face.normal

			edge_keys = face.edge_keys
			area = face.area # in m²

			load_normal = load[0]
			load_projected = load[1]
			load_area_z = load[2]

			area_projected = geometry.area_projected(face, vertices)

			distances, perimeter = geometry.perimeter(edge_keys, vertices)

			# define loads for each edge
			edge_load_normal = []
			edge_load_projected = []
			edge_load_area_z = []

			ratio = 1 / len(edge_keys)
			for edge_id, dist in enumerate(distances):
				# load_normal
				area_load = load_normal * area
				edge_load = area_load * ratio / dist * 0.01 # m to cm
				edge_load_normal.append(edge_load)

				# load projected
				area_load = load_projected * area_projected
				edge_load = area_load * ratio / dist * 0.01 # m to cm
				edge_load_projected.append(edge_load)

				# load in z
				area_load = load_area_z * area
				edge_load = area_load * ratio / dist * 0.01 # m to cm
				edge_load_area_z.append(edge_load)

			# i is the id within the class (0, 1, 3 and maybe more)
			# edge_id is the id of the edge in the mesh -> the member
			for i, edge_key in enumerate(edge_keys):
				# get name <---------------------------------------- maybe better method?
				for edge in edges:
					if edge.vertices[0] in edge_key:
						if edge.vertices[1] in edge_key:
							name = str(edge.index)

				# edge_load_normal <--------------------------------- to be tested / checked
				x = edge_load_normal[i] * normal[0]
				y = edge_load_normal[i] * normal[1]
				z = edge_load_normal[i] * normal[2]

				model.add_member_dist_load(name, 'FX', x, x)
				model.add_member_dist_load(name, 'FY', y, y)
				model.add_member_dist_load(name, 'FZ', z, z)

				# edge_load_projected
				z = edge_load_projected[i]
				model.add_member_dist_load(name, 'FZ', z, z)

				# edge_load_area_z
				z = edge_load_area_z[i]
				model.add_member_dist_load(name, 'FZ', z, z)

	# store frame based data
	data["frames"][str(frame)]["volume"] = geometry.volume(mesh)
	data["frames"][str(frame)]["area"] = geometry.area(faces)
	data["frames"][str(frame)]["length"] = frame_length
	data["frames"][str(frame)]["weight"] = frame_weight
	data["frames"][str(frame)]["rise"] = geometry.rise(vertices)
	data["frames"][str(frame)]["span"] = geometry.span(vertices, supports)
	data["frames"][str(frame)]["cantilever"] = geometry.cantilever(vertices, supports)

	# get duration
	text = calculation_type + " preparation for frame " + str(frame) + " done"
	text +=  basics.timer.stop()
	basics.print_data(text)

	# created a model object of PyNite and add to dict
	basics.models[frame] = model

def prepare_fea_fd(frame):
	'''
	Is preparing the calculaton of the current frame for for force disbribution.
	:return model: List of [points_array, supports_ids, edges_array, forces_array].
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type
	data = scene["<Phaenotyp>"]

	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()

	geometry.update_geometry_pre()

	basics.timer.start()

	psf_members = phaenotyp.psf_members
	psf_loads = phaenotyp.psf_loads

	# apply chromosome if available
	individuals = data.get("individuals")
	if individuals:
		shape_keys = data["structure"].data.shape_keys.key_blocks
		chromosome = individuals[str(frame)]["chromosome"]
		geometry.set_shape_keys(shape_keys, chromosome)

	# get absolute position of vertex (when using shape-keys, animation et cetera)
	dg = bpy.context.evaluated_depsgraph_get()
	obj = data["structure"].evaluated_get(dg)

	mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)

	vertices = mesh.vertices
	edges = mesh.edges
	faces = mesh.polygons

	# to be collected:
	data["frames"][str(frame)] = {}
	frame_volume = 0
	frame_area = 0
	frame_length = 0
	frame_weight = 0
	frame_rise = 0
	frame_span = 0
	frame_cantilever = 0

	# to sum up loads
	forces = []
	for i in range(len(vertices)):
		forces.append(array([0.0, 0.0, 0.0]))

	# like suggested here by Gorgious and CodeManX:
	# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
	mat = obj.matrix_world

	# add nodes from vertices
	points = []
	for vertex in vertices:
		# like suggested here by Gorgious and CodeManX:
		# https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
		v = mat @ vertex.co

		# apply to all vertices to work for edges and faces also
		vertex.co = v

		x = v[0] * 100 # convert to cm for calculation
		y = v[1] * 100 # convert to cm for calculation
		z = v[2] * 100 # convert to cm for calculation

		pos = [x,y,z]
		points.append(pos)

	points_array = array(points)

	# define support
	fixed = []
	supports = data["supports"]
	for id, support in supports.items():
		id = int(id)
		fixed.append(id)

	supports_ids = fixed

	# create members
	members = data["members"]
	keys = []
	lenghtes = []
	for id, member in members.items():
		vertex_0_id = member["vertex_0_id"]
		vertex_1_id = member["vertex_1_id"]

		key = [vertex_0_id, vertex_1_id]
		keys.append(key)

		v_0 = vertices[vertex_0_id].co
		v_1 = vertices[vertex_1_id].co

		# save initial_positions to mix with deflection
		initial_positions = []
		for position in [v_0, v_1]:
			x = position[0]
			y = position[1]
			z = position[2]
			initial_positions.append([x,y,z])
		member["initial_positions"][str(frame)] = initial_positions

		# add self weight
		weight_A = member["weight_A"][str(frame)]
		kN = weight_A * -0.0000981

		# calculate lenght of parts (maybe usefull later ...)
		length = (v_0 - v_1).length
		frame_length += length

		# calculate and add weight to overall weight of structure
		weight = length * weight_A
		frame_weight += weight

		# for calculation
		lenghtes.append(length)

		# add self weight
		self_weight = kN * length * 100 * psf_members
		forces[vertex_0_id] += array([0.0, 0.0, self_weight*0.5])
		forces[vertex_1_id] += array([0.0, 0.0, self_weight*0.5])

		# store in member
		member["weight"][str(frame)] = weight
		member["length"][str(frame)] = length

	edges_array = array(keys)

	# add loads
	loads_v = data["loads_v"]
	for id, load in loads_v.items():
		forces[int(id)] += array([load[0]*100*psf_loads, load[1]*100*psf_loads, load[2]*100*psf_loads])

	loads_e = data["loads_e"]
	for id, load in loads_e.items():
		member = members[id]
		vertex_0_id = member["vertex_0_id"]
		vertex_1_id = member["vertex_1_id"]
		length = lenghtes[int(id)]
		f = length * 0.5 * 100 * psf_loads # half of the member, m to cm + psf
		forces[int(vertex_0_id)] += array([load[0]*f, load[1]*f, load[2]*f])
		forces[int(vertex_1_id)] += array([load[0]*f, load[1]*f, load[2]*f])

	loads_f = data["loads_f"]
	for id, load in loads_f.items():
		# int(id), otherwise crashing Speicherzugriffsfehler
		face = data["structure"].data.polygons[int(id)]
		normal = face.normal

		edge_keys = face.edge_keys
		area = face.area

		load_normal = load[0]
		load_projected = load[1]
		load_area_z = load[2]

		area_projected = geometry.area_projected(face, vertices)
		distances, perimeter = geometry.perimeter(edge_keys, vertices)

		# define loads for each edge
		edge_load_normal = []
		edge_load_projected = []
		edge_load_area_z = []

		ratio = 1 / len(edge_keys)
		for edge_id, dist in enumerate(distances):
			# load normal
			area_load = load_normal * area
			edge_load = area_load * ratio / dist * 0.01 *psf_loads # m to cm + psf
			edge_load_normal.append(edge_load)

			# load projected
			area_load = load_projected * area_projected
			edge_load = area_load * ratio / dist * 0.01 *psf_loads # m to cm + psf
			edge_load_projected.append(edge_load)

			# load in z
			area_load = load_area_z * area
			edge_load = area_load * ratio / dist * 0.01 *psf_loads # m to cm + psf
			edge_load_area_z.append(edge_load)

		# i is the id within the class (0, 1, 3 and maybe more)
		# edge_id is the id of the edge in the mesh -> the member
		for i, edge_key in enumerate(edge_keys):
			for edge in edges:
				if edge.vertices[0] in edge_key:
					if edge.vertices[1] in edge_key:
						id = edge.index

			x = edge_load_normal[i] * normal[0]
			y = edge_load_normal[i] * normal[1]
			z = edge_load_normal[i] * normal[2]

			member = members[str(id)]
			vertex_0_id = member["vertex_0_id"]
			vertex_1_id = member["vertex_1_id"]
			length = lenghtes[int(id)]
			f = length * 0.5 * 100 # half of the member, m to cm
			forces[int(vertex_0_id)] += array([x*f, y*f, z*f])
			forces[int(vertex_1_id)] += array([x*f, y*f, z*f])

			# edge_load_projected
			z = edge_load_projected[i]
			forces[int(vertex_0_id)] += array([0.0, 0.0, z*f])
			forces[int(vertex_1_id)] += array([0.0, 0.0, z*f])

			# edge_load_area_z
			z = edge_load_area_z[i]
			forces[int(vertex_0_id)] += array([0.0, 0.0, z*f])
			forces[int(vertex_1_id)] += array([0.0, 0.0, z*f])

	# move all forces from the supports to the next load
	# (is ignored if the both vertices are supports)
	for id, member in members.items():
		vertex_0_id = member["vertex_0_id"]
		vertex_1_id = member["vertex_1_id"]

		if vertex_0_id in supports_ids:
			forces[int(vertex_1_id)] += forces[int(vertex_0_id)]

		if vertex_1_id in supports_ids:
			forces[int(vertex_0_id)] += forces[int(vertex_1_id)]

	forces_array = array(forces)

	# store frame based data
	data["frames"][str(frame)]["volume"] = geometry.volume(mesh)
	data["frames"][str(frame)]["area"] = geometry.area(faces)
	data["frames"][str(frame)]["length"] = frame_length
	data["frames"][str(frame)]["weight"] = frame_weight
	data["frames"][str(frame)]["rise"] = geometry.rise(vertices)
	data["frames"][str(frame)]["span"] = geometry.span(vertices, supports)
	data["frames"][str(frame)]["cantilever"] = geometry.cantilever(vertices, supports)

	# get duration
	text = calculation_type + " preparation for frame " + str(frame) + " done"
	text +=  basics.timer.stop()
	basics.print_data(text)

	# created a model object of PyNite and add to dict
	model = [points_array, supports_ids, edges_array, forces_array]
	basics.models[str(frame)] = model

def run_mp(models):
	'''
	Is calculating the given models, pickles them for mp.
	:param models: Needs a list of models from any prepare_fea as dict with frame as key.
	:return models: Returns the calculated models as dict with the frame as key.
	'''
	# get pathes
	path_addons = os.path.dirname(__file__) # path to the folder of addons
	path_script = path_addons + "/mp.py"
	path_python = sys.executable # path to bundled python
	path_blend = bpy.data.filepath # path to stored blender file
	directory_blend = os.path.dirname(path_blend) # directory of blender file
	name_blend = bpy.path.basename(path_blend) # name of file

	# pickle models to file
	path_export = directory_blend + "/Phaenotyp-export_mp.p"
	export_models = open(path_export, 'wb')
	pickle.dump(models, export_models)
	export_models.close()

	# scipy_available to pass forward
	if bpy.context.scene["<Phaenotyp>"]["scipy_available"]:
		scipy_available = "True" # as string
	else:
		scipy_available = "False" # as string

	# calculation_type
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type

	task = [path_python, path_script, directory_blend, scipy_available, calculation_type]
	# feedback from python like suggested from Markus Amalthea Magnuson and user3759376 here
	# https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
	p = Popen(task, stdout=PIPE, bufsize=1)
	lines_iterator = iter(p.stdout.readline, b"")
	while p.poll() is None:
		for line in lines_iterator:
			nline = line.rstrip()
			#print(nline.decode("utf8"), end = "\r\n",flush =True) # yield line

	# get models back from mp
	path_import = directory_blend + "/Phaenotyp-return_mp.p"
	file = open(path_import, 'rb')
	imported_models = pickle.load(file)
	file.close()

	basics.feas = imported_models

def interweave_results_pn(frame):
	'''
	Function to integrate the results of PyNite.
	:param feas: Feas as dict with frame as key.
	:param members: Pass the members from <Phaenotyp>
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type
	members = data["members"]
	quads = data["quads"]

	frame = str(frame)
	model = basics.feas[frame]
	basics.timer.start()

	for id in members:
		member = members[id]
		model_member = model.members[id]

		L = model_member.L() # Member length
		T = model_member.T() # Member local transformation matrix

		axial = []
		moment_y = []
		moment_z = []
		shear_y = []
		shear_z = []
		torque = []

		for i in range(11): # get the forces at 11 positions and
			x = L/10*i

			axial_pos = model_member.axial(x) * (-1) # Druckkraft minus
			axial.append(axial_pos)

			moment_y_pos = model_member.moment("My", x)
			moment_y.append(moment_y_pos)

			moment_z_pos = model_member.moment("Mz", x)
			moment_z.append(moment_z_pos)

			shear_y_pos = model_member.shear("Fy", x)
			shear_y.append(shear_y_pos)

			shear_z_pos = model_member.shear("Fz", x)
			shear_z.append(shear_z_pos)

			torque_pos = model_member.torque(x)
			torque.append(torque_pos)

		member["axial"][frame] = axial
		member["moment_y"][frame] = moment_y
		member["moment_z"][frame] = moment_z
		member["shear_y"][frame] = shear_y
		member["shear_z"][frame] = shear_z
		member["torque"][frame] = torque
		
		profile_type = member["profile_type"]
			
		if profile_type in ["round_hollow", "round_solid"]:
			A = member["A"][frame]
			J = member["J"][frame]
			Do = member["height"][frame]

			# buckling
			member["ir_y"][frame] = sqrt(J/A) # für runde Querschnitte, in  cm
			member["ir_z"][frame] = sqrt(J/A) # für runde Querschnitte, in  cm

			# bucklng resolution
			buckling_resolution = member["buckling_resolution"]

			# modulus from the moments of area
			# Wy and Wz are the same within a pipe
			member["Wy"][frame] = member["Iy"][frame]/(Do/2)

			# polar modulus of torsion
			member["WJ"][frame] = J/(Do/2)

			# calculation of the longitudinal stresses
			long_stress = []
			for i in range(11): # get the stresses at 11 positions and
				moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				if axial[i] > 0:
					s = axial[i]/A + moment_h/member["Wy"][frame]
				else:
					s = axial[i]/A - moment_h/member["Wy"][frame]
				long_stress.append(s)

			# get max stress of the beam
			# (can be positive or negative)
			member["long_stress"][frame] = long_stress
			member["max_long_stress"][frame] = basics.return_max_diff_to_zero(long_stress) #  -> is working as fitness

			# calculation of the shear stresses from shear force
			# (always positive)
			tau_shear = []
			shear_h = []    # Querkraft in Hauptrichung
			for i in range(11): # get the stresses at 11 positions and
				s_h = sqrt(shear_y[i]**2+shear_z[i]**2)
				shear_h.append(s_h)

				tau = 1.333 * s_h/A # for pipes
				tau_shear.append(tau) # Schubspannung

			member["shear_h"][frame] = shear_h  # Querkraft

			# get max shear stress of shear force of the beam
			# shear stress is mostly small compared to longitudinal
			# in common architectural usage and only importand with short beam length
			member["tau_shear_y"][frame] = tau_shear  # Schubspannung
			member["tau_shear_z"][frame] = tau_shear
			member["max_tau_shear_y"][frame] = max(tau_shear)  # max Schubspannung
			member["max_tau_shear_z"][frame] = max(tau_shear)  # max Schubspannung

			# Calculation of the torsion stresses
			# (always positiv)
			Do = member["height"][frame]
			if member["wall_thickness"][frame] == None:	Di = 0
			else: Di = Do - member["wall_thickness"][frame]
			s = Do-Di   # WAndstärke
			Dm = (Do-Di)/2  # mittlere Dicke
			Wjd = 0.5*pi*Dm*s  # Formel für dünnwandige Rohrquerschnitte nach Preussler
			# kann man aber auch schon in Materil.py geben
			tau_torsion = []
			if Di/Do < 0.85:  # für Vollquerschnitte wie gehabt, gilt auch für dickwandige Rohrquerschnitte
				for i in range(11): # get the stresses at 11 positions and
					tau = abs(torque[i]/member["WJ"][frame])
					tau_torsion.append(tau)
			else: # für dünnwandige Hohlquerschnitte neue Formel
				for i in range(11): # get the stresses at 11 positions and
					tau = abs(torque[i]/Wjd)
					tau_torsion.append(tau)
			
			# get max torsion stress of the beam
			member["tau_torsion"][frame] = tau_torsion  # Torsionsspannungen
			member["max_tau_torsion"][frame] = max(tau_torsion)  # max Torsionsspannungen

			# torsion stress is mostly small compared to longitudinal
					# combine shear and torque
			# (always positiv)
			sum_tau = []  # Schub und Torsion überlagerbar
			for i in range(11): # get the stresses at 11 positions and
				tau = tau_shear[i] + tau_torsion[i]
				sum_tau.append(tau)

			member["sum_tau"][frame] = sum_tau
			member["max_sum_tau"][frame] = max(sum_tau)

			# Vergleichsspannung nach Mises, nicht mehr, da an verschiedenen Stellen
			#sigmav = []
			#for i in range(11): # get the stresses at 11 positions and
				#sv = sqrt(long_stress[i]**2 + 3*sum_tau[i]**2)
				#sigmav.append(sv)

			#member["sigmav"][frame] = sigmav
			#member["max_sigmav"][frame] = max(sigmav)
			# check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

			member["sigma"][frame] = member["long_stress"][frame]
			member["max_sigma"][frame] = member["max_long_stress"][frame]

			# overstress
			member["overstress"][frame] = False

			# check overstress and add 1.05 savety factor
			safety_factor = 1.05
			# prüft nur y, da gleich wie z
			if abs(member["max_tau_shear_y"][frame]) > safety_factor*member["acceptable_shear"]:
				member["overstress"][frame] = True

			if abs(member["max_tau_torsion"][frame]) > safety_factor*member["acceptable_torsion"]:
				member["overstress"][frame] = True

			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigmav"]:
				member["overstress"][frame] = True

			# buckling
			if member["axial"][frame][0] < 0: # nur für Druckstäbe, axial kann nicht flippen?
				member["lamda"][frame] = L*buckling_resolution*0.5/member["ir_y"][frame] # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
				if member["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
					kn = member["knick_model"]
					function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
					member["acceptable_sigma_buckling"][frame] = function_to_run(member["lamda"][frame])
					if member["lamda"][frame] > 250: # Schlankheit zu schlank
						member["acceptable_sigma_buckling"][frame] = function_to_run(250)
						member["overstress"][frame] = True
					if safety_factor*abs(member["acceptable_sigma_buckling"][frame]) > abs(member["max_sigma"][frame]): # Sigma
						member["overstress"][frame] = True

				else:
					member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]

			# without buckling
			else:
				member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]
				member["lamda"][frame] = None # to avoid missing KeyError


			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigma"]:
				member["overstress"][frame] = True

			# lever_arm
			lever_arm = []
			moment_h = []
			for i in range(11):
				# moment_h
				m_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				moment_h.append(m_h)

				# to avoid division by zero
				if member["axial"][frame][i] < 0.1: # überprüfen ev kleiner
					lv = m_h / 0.1
				else:
					lv = m_h / member["axial"][frame][i]

				lv = abs(lv) # absolute highest value within member
				lever_arm.append(lv)

			member["moment_h"][frame] = moment_h
			member["lever_arm"][frame] = lever_arm
			member["max_lever_arm"][frame] = max(lever_arm)

			# Ausnutzungsgrad
			member["utilization"][frame] = abs(member["max_long_stress"][frame] / member["acceptable_sigma_buckling"][frame])

			# Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
			normalkraft_energy=[]
			moment_energy=[]
			strain_energy = []

			for i in range(10): # get the energie at 10 positions for 10 section
				# Berechnung der strain_energy für Normalkraft
				ne = (axial[i]**2)*(L/10)/(2*member["E"]*A)
				normalkraft_energy.append(ne)

				# Berechnung der strain_energy für Moment
				moment_hq = moment_y[i]**2 + moment_z[i]**2 # hier ist das quadrat
				# me = (moment_hq * L/10) / (member["E"] * member["Wy"][frame] * Do) # meue Formel nun, noch überprüfen ob gleich (2 statt Do)
				me = (moment_hq * L/10) / (member["E"] * member["Iy"][frame] * 2) # laut https://roymech.org/Useful_Tables/Beams/Strain_Energy.html
				moment_energy.append(me)

				# Summe von Normalkraft und Moment-Verzerrunsenergie
				value = ne + me
				strain_energy.append(value)

			member["strain_energy"][frame] = strain_energy
			member["normal_energy"][frame] = normalkraft_energy
			member["moment_energy"][frame] = moment_energy

		if profile_type == "rect_hollow":
			# Nur die Schub- und Torsionsspannungen sind anders als bei "rect_solid"
			# shorten and accessing once
			A = member["A"][frame]
			Iy = member["Iy"][frame] # passt das?
			Iz = member["Iz"][frame] # passt das
			# buckling
			member["ir_y"][frame] = sqrt(Iy/A)
			member["ir_z"][frame] = sqrt(Iz/A)
			# bucklng resolution
			buckling_resolution = member["buckling_resolution"]

			# modulus from the moments of area

			member["Wy"][frame] = member["Iy"][frame]/(height/2)
			member["Wz"][frame] = member["Iz"][frame]/(width/2)

			# calculation of the longitudinal stresses
			long_stress = []
			for i in range(11): # get the stresses at 11 positions and
				# moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				if axial[i] > 0:
					s = axial[i]/A + abs(moment_y[i]/member["Wy"][frame]) + abs(moment_z[i]/member["Wz"][frame])
				else:
					s = axial[i]/A - abs(moment_y[i]/member["Wy"][frame]) - abs(moment_z[i]/member["Wz"][frame])
				long_stress.append(s)

			# get max stress of the beam
			# (can be positive or negative)
			member["long_stress"][frame] = long_stress
			member["max_long_stress"][frame] = basics.return_max_diff_to_zero(long_stress) #  -> is working as fitness

			# calculation of the shear stresses from shear force
			tau_shear_y = [] # nun zwei Scherspannungen
			tau_shear_z = []
			#shear_h = []

			for i in range(11): # get the stresses at 11 positions and
				# in y Richrtung
				# s_y = sqrt(shear_y[i]**2+shear_z[i]**2)
				s_y = member["shear_y"][frame][i]
				s_z = member["shear_z"][frame][i]
				shear_y.append(s_y) # jetzt in y und z richtung
				shear_z.append(s_z)

				tau_y = abs(1.0 * s_y/A) # for hollow rectangle, maximale tritt in Mitte auf,
				tau_shear_y.append(tau_y)
				tau_z = abs( 1.0 * s_z/A) # for hollow rectangle, maximale tritt in Mitte auf wird maßgebend sein, ev die größere für Schubbemessun nehmen
				tau_shear_z.append(tau_z)

			# get max shear stress of shear force of the beam
			# shear stress is mostly small compared to longitudinal, in common architectural usage and only importand with short beam lenght
			member["tau_shear_y"][frame] = tau_shear_y  # jetzt x und z
			member["tau_shear_z"][frame] = tau_shear_z # wird maßgebend sein
			member["max_tau_shear_y"][frame] = max(tau_shear_y)
			member["max_tau_shear_z"][frame] = max(tau_shear_z) # wird maßgebend sein, ev nur das größere ausweisen

			# Calculation of the torsion stresses

			tau_torsion = []
			height = member["height"][frame]
			width = member["width"][frame]
			t = member["wall_thickness"][frame]
			
			for i in range(11): # get the stresses at 11 positions and
				tau = abs(torque[i]/(2 * height-t)*(width-t))*t  #### Formel nach Wandinger-Torsion, Trägheitsmoment nicht erforderlich, sondern direkt mit Am =mittlere Fläche und Wanddicke errechnet
				# Torsionsspannung in senkrechten und horizontalen Steg gleich, daher nur tau und nicht tau_z und tau_y
				# muss height und width und t noch übernommen werden?
				tau_torsion.append(tau)

			# get max torsion stress of the beam
			member["tau_torsion"][frame] = tau_torsion
			member["max_tau_torsion"][frame] = max(tau_torsion)

			# calculation of the shear stresses from shear force and torsion
			# (always positiv)

			sum_tau = []  # Schub und Torsion überlagerbar
			for i in range(11): # get the stresses at 11 positions and
				tau = tau_shear_z[i] + tau_torsion[i] # nur Schub aus Qz und Torsionsspannung an der Längsseite überlagert, da maßgebden
			sum_tau.append(tau)

			member["sum_tau"][frame] = sum_tau
			member["max_sum_tau"][frame] = max(sum_tau)
			#sum_tau_y = []
			#sum_tau_z = []
			#for i in range(11): # get the stresses at 11 positions and
				#tau_y = tau_shear_y[i] + tau_torsion[i]
				#sum_tau_y.append(tau)
				#tau_z = tau_shear_z[i] + tau_torsion[i] # meist größer wegen senkrechter Last
				#sum_tau_z.append(tau)
			
			#member["sum_tau_y"][frame] = sum_tau_y
			#member["sum_tau_z"][frame] = sum_tau_z  #
			#member["max_sum_tau_y"][frame] = max(sum_tau_y)
			#member["max_sum_tau_z"][frame] = max(sum_tau_z) # meist größer wegen senkrechter Last

			# vergleichsspannung nach von misess, nicht, da an verschiedenen Stellen

			#sigmav = []
			#for i in range(11): # get the stresses at 11 positions and
				#sv = sqrt(long_stress[i]**2 + 3*sum_tau_z[i]**2)  # vorläufig hier nur die durch z-Querkräfte verurachte Scherspannung genommen
				#sigmav.append(sv)

			#member["sigmav"][frame] = sigmav
			#member["max_sigmav"][frame] = max(sigmav)
			# check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung
			member["sigma"][frame] = member["long_stress"][frame]
			member["max_sigma"][frame] = member["max_long_stress"][frame]

			# overstress
			member["overstress"][frame] = False

			# check overstress and add 1.05 savety factor
			safety_factor = 1.05
			if abs(member["max_tau_shear_y"][frame]) > safety_factor*member["acceptable_shear"]:
				member["overstress"][frame] = True

			if abs(member["max_tau_shear_z"][frame]) > safety_factor*member["acceptable_shear"]:
				member["overstress"][frame] = True
				
			if abs(member["max_tau_torsion"][frame]) > safety_factor*member["acceptable_torsion"]:
				member["overstress"][frame] = True
			
			# Ist das korrekt?
			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigmav"]:
				member["overstress"][frame] = True

			# buckling
			if member["axial"][frame][0] < 0: # nur für Druckstäbe, axial kann nicht flippen?
				# hier als ir das kleinere von ir_z und ir_y nehmen
				if member["ir_y"][frame] < member["ir_z"][frame]: ir = member["ir_y"][frame]
				else: ir = member["ir_z"][frame]
				
				member["lamda"][frame] = L*buckling_resolution*0.5/ir # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
				if member["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
					kn = member["knick_model"]
					function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
					member["acceptable_sigma_buckling"][frame] = function_to_run(member["lamda"][frame])
					if member["lamda"][frame] > 250: # zu schlank
						member["acceptable_sigma_buckling"][frame] = function_to_run(250)
						member["overstress"][frame] = True
					if safety_factor*abs(member["acceptable_sigma_buckling"][frame]) > abs(member["max_sigma"][frame]): # Sigma
						member["overstress"][frame] = True

				else:
					member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]

			# without buckling
			else:
				member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]
				member["lamda"][frame] = None # to avoid missing KeyError


			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigma"]:
				member["overstress"][frame] = True

			# lever_arm
			lever_arm = []  # noch nicht überarbeitet
			moment_h = []  # noch nicht überarbeitet
			for i in range(11):
				# moment_h
				m_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				moment_h.append(m_h)

				# to avoid division by zero
				if member["axial"][frame][i] < 0.1:
					lv = m_h / 0.1
				else:
					lv = m_h / member["axial"][frame][i]

				lv = abs(lv) # absolute highest value within member
				lever_arm.append(lv)

			member["moment_h"][frame] = moment_h
			member["lever_arm"][frame] = lever_arm
			member["max_lever_arm"][frame] = max(lever_arm)

			# Ausnutzungsgrad
			member["utilization"][frame] = abs(member["max_long_stress"][frame] / member["acceptable_sigma_buckling"][frame])

			# Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
			normalkraft_energy = []
			moment_energy = []
			strain_energy = []

			for i in range(10): # get the energie at 10 positions for 10 section
				# Berechnung der strain_energy für Normalkraft
				ne = (axial[i]**2)*(L/10)/(2*member["E"]*A)
				normalkraft_energy.append(ne)

				# Berechnung der strain_energy für Moment
				# moment_hq = moment_y[i]**2+moment_z[i]**2
				moment_y = member["moment_y"][frame][i]
				moment_z = member["moment_z"][frame][i]
				me = (moment_y**2 * L/10) / (2 * member["E"] * member["Iy"][frame]) + (moment_z**2 * L/10) / (2 * member["E"] * member["Iz"][frame]) # KD 2025-09_26
				#  nach https://roymech.org/Useful_Tables/Beams/Strain_Energy.html
				moment_energy.append(me)

				# Summe von Normalkraft und Moment-Verzerrunsenergie
				value = ne + me
				strain_energy.append(value)

			member["strain_energy"][frame] = strain_energy
			member["normal_energy"][frame] = normalkraft_energy
			member["moment_energy"][frame] = moment_energy

		if profile_type == "rect_solid":
			# Schub- und Torsionsspannungen sind anders als bei "rect_solid"
			# shorten and accessing once
			A = member["A"][frame]
			Iy = member["Iy"][frame] # passt das?
			Iz = member["Iz"][frame]  # passt das?
			# buckling
			member["ir_y"][frame] = sqrt(Iy/A)
			member["ir_z"][frame] = sqrt(Iz/A)
			# bucklng resolution
			buckling_resolution = member["buckling_resolution"]

			# modulus from the moments of area
			member["Wy"][frame] = member["Iy"][frame]/(height/2)
			member["Wz"][frame] = member["Iz"][frame]/(width/2)
			
			###### Stimmt das?
			height = float(member["height"][frame])  # kürzere Seite = t
			width  = float(member["width"][frame])   # längere Seite = b

			# b = längere Seite, t = kürzere Seite
			b = max(width, height)
			t = min(width, height)

			# Effektives Wt so, dass tau_max = T / Wt_eff gilt
			Wt = (b * t**2) / (3.0 + 1.8 * (t/b))

			member["Wt"][frame] = Wt
			######

			member["Wt"][frame] = member["Wt"][frame]   # neu
			# calculation of the longitudinal stresses
			long_stress = []
			for i in range(11): # get the stresses at 11 positions and
				# moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				if axial[i] > 0:
					s = axial[i]/A + abs(moment_y[i]/member["Wy"][frame]) + abs(moment_z[i]/member["Wz"][frame])
				else:
					s = axial[i]/A - abs(moment_y[i]/member["Wy"][frame]) - abs(moment_z[i]/member["Wz"][frame])
				long_stress.append(s)

			# get max stress of the beam
			# (can be positive or negative)
			member["long_stress"][frame] = long_stress
			member["max_long_stress"][frame] = basics.return_max_diff_to_zero(long_stress) #  -> is working as fitness

			# calculation of the shear stresses from shear force

			tau_shear_y = []
			tau_shear_z = []
			for i in range(11): # get the stresses at 11 positions and
				# in y Richrtung
				s_y = member["shear_y"][frame][i]
				s_z = member["shear_z"][frame][i]

				tau_y = abs(1.5 * s_y/A) # for solid rectangle, maximale tritt in Mitte auf
				tau_shear_y.append(tau_y)
				tau_z = abs(1.5 * s_z/A) # for solid rectangle, maximale tritt in Mitte auf
				tau_shear_z.append(tau_z)
			
			# get max shear stress of shear force of the beam
			# shear stress is mostly small compared to longitudinal, in common architectural usage and only importand with short beam lenght
			member["tau_shear_y"][frame] = tau_shear_y  # jetzt y und z
			member["tau_shear_z"][frame] = tau_shear_z # wird maßgebend sein, ev die größere für Schubbemessun nehmen
			member["max_tau_shear_y"][frame] = max(tau_shear_y) # jetzt y und z
			member["max_tau_shear_z"][frame] = max(tau_shear_z) # jetzt y und z, ev nur das größere ausweisen

			# Calculation of the torsion stresses

			tau_torsion = []
			for i in range(11): # get the stresses at 11 positions and
				tau = abs(torque[i]/Wt) # die größte Torsionsspannung ist am Rand der längeren Seite, nur diese wird berechnet
				tau_torsion.append(tau)

			# get max torsion stress of the beam
			member["tau_torsion"][frame] = tau_torsion
			member["max_tau_torsion"][frame] = max(tau_torsion)

			# calculation of the shear stresses from shear force and torsion
			# (always positiv)
			#sum_tau_y = []
			#sum_tau_z = []
			#for i in range(11): # get the stresses at 11 positions and
				#tau_y = tau_shear_y[i] + tau_torsion[i]
				#sum_tau_y.append(tau)
				#tau_z = tau_shear_z[i] + tau_torsion[i] # meist größer wegen senkrechter Last und stehenden Quuerschnitt
				#sum_tau_z.append(tau)
			#member["sum_tau_y"][frame] = sum_tau_y
			#member["sum_tau_z"][frame] = sum_tau_z # meist größer wegen senkrechter Last
			#member["max_sum_tau_y"][frame] = max(sum_tau_y)
			#member["max_sum_tau_z"][frame] = max(sum_tau_z) # meist größer wegen senkrechter Last

			sum_tau = []  # Schub und Torsion überlagerbar
			for i in range(11): # get the stresses at 11 positions and
				tau = tau_shear_z[i] + tau_torsion[i] # nur Schub aus Qz und Torsionsspannung an der Längsseite überlagert, da maßgebden
				sum_tau.append(tau)

			member["sum_tau"][frame] = sum_tau
			member["max_sum_tau"][frame] = max(sum_tau)


			# vergleichsspannung nach von misess, weggelassen, da nicht an gleicher STelle
			#sigmav = []
			#for i in range(11): # get the stresses at 11 positions and
				#sv = sqrt(long_stress[i]**2 + 3*sum_tau_z[i]**2)  # hier nur die durch z-Querkräfte verurachte Scherspannung genommen
				#sigmav.append(sv)

			#member["sigmav"][frame] = sigmav
			#member["max_sigmav"][frame] = max(sigmav)
			# check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

			member["sigma"][frame] = member["long_stress"][frame]
			member["max_sigma"][frame] = member["max_long_stress"][frame]

			# overstress
			member["overstress"][frame] = False

			# check overstress and add 1.05 savety factor
			safety_factor = 1.05
			if abs(member["max_tau_shear_y"][frame]) > safety_factor*member["acceptable_shear"]:
				member["overstress"][frame] = True

			if abs(member["max_tau_shear_z"][frame]) > safety_factor*member["acceptable_shear"]:
				member["overstress"][frame] = True
				
			if abs(member["max_tau_torsion"][frame]) > safety_factor*member["acceptable_torsion"]:
				member["overstress"][frame] = True
			
			# stimmt hier simga?
			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigmav"]:
				member["overstress"][frame] = True

			# buckling
			if member["axial"][frame][0] < 0: # nur für Druckstäbe, axial kann nicht flippen?
				# hier als ir das kleinere von ir_z und ir_y nehmen
				member["lamda"][frame] = L*buckling_resolution*0.5/member["ir"][frame] # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
				if member["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
					kn = member["knick_model"]
					function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
					member["acceptable_sigma_buckling"][frame] = function_to_run(member["lamda"][frame])
					if member["lamda"][frame] > 250: # zu schlank
						member["acceptable_sigma_buckling"][frame] = function_to_run(250)
						member["overstress"][frame] = True
					if safety_factor*abs(member["acceptable_sigma_buckling"][frame]) > abs(member["max_sigma"][frame]): # Sigma
						member["overstress"][frame] = True

				else:
					member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]

			# without buckling
			else:
				member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]
				member["lamda"][frame] = None # to avoid missing KeyError


			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigma"]:
				member["overstress"][frame] = True

			# lever_arm
			lever_arm = []  # noch nicht überarbeitet
			moment_h = []  # noch nicht überarbeitet
			for i in range(11):
				# moment_h
				m_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				moment_h.append(m_h)

				# to avoid division by zero
				if member["axial"][frame][i] < 0.1:
					lv = m_h / 0.1
				else:
					lv = m_h / member["axial"][frame][i]

				lv = abs(lv) # absolute highest value within member
				lever_arm.append(lv)

			member["moment_h"][frame] = moment_h
			member["lever_arm"][frame] = lever_arm
			member["max_lever_arm"][frame] = max(lever_arm)

			# Ausnutzungsgrad
			member["utilization"][frame] = abs(member["max_long_stress"][frame] / member["acceptable_sigma_buckling"][frame])

			# Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
			normalkraft_energy=[]
			moment_energy=[]
			strain_energy = []

			for i in range(10): # get the energie at 10 positions for 10 section
				# Berechnung der strain_energy für Normalkraft
				ne = (axial[i]**2)*(L/10)/(2*member["E"]*A)
				normalkraft_energy.append(ne)

				# Berechnung der strain_energy für Moment
				# moment_hq = moment_y[i]**2+moment_z[i]**2
				moment_y = member["moment_y"][frame][i]
				moment_z = member["moment_z"][frame][i]
				
				me = (moment_y**2 * L/10) / (2 * member["E"] * member["Iy"][frame]) + (moment_z**2 * L/10) / (2 * member["E"] * member["Iz"][frame]) # KD 2025-09_26
				#  nach https://roymech.org/Useful_Tables/Beams/Strain_Energy.html
				moment_energy.append(me)

				# Summe von Normalkraft und Moment-Verzerrunsenergie
				value = ne + me
				strain_energy.append(value)

			member["strain_energy"][frame] = strain_energy
			member["normal_energy"][frame] = normalkraft_energy
			member["moment_energy"][frame] = moment_energy

		if profile_type == "standard_profile":
			# Schub- und Torsionsspannungen sind anders als bei "rect_solid"
			# shorten and accessing once
			A = member["A"][frame] # passt das
			Iy = member["Iy"][frame] # passt das?
			Iz = member["Iz"][frame]  # passt das
			# noch Höhe, Breite und Flanschdicke notwendig
			# Torsionsträgheitsmoment nicht notwendig, da direkt mit Formel berechnet
			# buckling
			member["ir_y"][frame] = sqrt(Iy/A)
			member["ir_z"][frame] = sqrt(Iz/A)
			# bucklng resolution
			buckling_resolution = member["buckling_resolution"]

			# modulus from the moments of area
			
			height = member["height"][frame]
			width = member["width"][frame]

			member["Wy"][frame] = member["Iy"][frame]/(height/2)
			member["Wz"][frame] = member["Iz"][frame]/(width/2)
			# gebraucht wird Höhe, Breite  und Stegdicke

			# calculation of the longitudinal stresses
			long_stress = []
			for i in range(11): # get the stresses at 11 positions and
				# moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				if axial[i] > 0:
					s = axial[i]/A + abs(moment_y[i]/member["Wy"][frame]) + abs(moment_z[i]/member["Wz"][frame])
				else:
					s = axial[i]/A - abs(moment_y[i]/member["Wy"][frame]) - abs(moment_z[i]/member["Wz"][frame])
				long_stress.append(s)

			# get max stress of the beam
			# (can be positive or negative)
			member["long_stress"][frame] = long_stress
			member["max_long_stress"][frame] = basics.return_max_diff_to_zero(long_stress) #  -> is working as fitness
			
			tau_shear_y = []
			tau_shear_z = []
			#shear_h = []

			for i in range(11): # get the stresses at 11 positions and
				s_y = member["shear_y"][frame][i]
				s_z = member["shear_z"][frame][i]

				tau_y = abs(1.0 * s_y/A) # for I-Traeger maximale tritt in Steg auf, wegen Horizontallwirkung kaum massgebend
				tau_shear_y.append(tau_y)
				tau_z = abs(1.0 * s_z/A) # ev noch korrigieren,
				tau_shear_z.append(tau_z)

			# get max shear stress of shear force of the beam
			# shear stress is mostly small compared to longitudinal, in common architectural usage and only importand with short beam lenght
			member["tau_shear_y"][frame] = tau_shear_y  # jetzt x und z
			member["tau_shear_z"][frame] = tau_shear_z #  wid maßgebend sein
			member["max_tau_shear_y"][frame] = max(tau_shear_y)
			member["max_tau_shear_z"][frame] = max(tau_shear_z) # ev nur dieses ausweisen

			# Calculation of the torsion stresses

			tau_torsion = []
			
			current_profile = None
			for i in material.profiles:
				if i[0] == member["profile"][frame]:
					current_profile = i
				
			h = current_profile[2] # Höhe
			b = current_profile[3] # Breite
			d = current_profile[4] # Stegdicke
			
			for i in range(11): # get the stresses at 11 positions and
				tau = abs(torque[i]*1.5/(h * b * d)) # Sttps://www.tugraz.at/institute/isb/lehre/e-learning/spannungen-aus-torsion-311-antwort
				# Höhe, Breite und Stegdicke noch einlesen
				# größte tritt in beiden Flanschen in der MItte auf, keine Überlagerung mit Querkraftschub
				tau_torsion.append(tau)

			# get max torsion stress of the beam
			member["tau_torsion"][frame] = tau_torsion
			member["max_tau_torsion"][frame] = max(tau_torsion)

			# calculation of the shear stresses from shear force and torsion
			# (always positiv)
			sum_tau = []  # Schub und Torsion überlagerbar
			for i in range(11): # get the stresses at 11 positions and
				tau = tau_shear_z[i]  # nur Schub aus Qz, keine Torsion, da an anderer Stelle
				sum_tau.append(tau)

			member["sum_tau"][frame] = sum_tau
			member["max_sum_tau"][frame] = max(sum_tau)

			#sum_tau_y = []
			#sum_tau_z = []
			#for i in range(11): # get the stresses at 11 positions and
				#tau_y = tau_shear_y[i] #+ tau_torsion[i] keine Überlagerung da andere Stelle
				#sum_tau_y.append(tau)
				#tau_z = tau_shear_z[i] #+ tau_torsion[i]
				#sum_tau_z.append(tau)
			#member["sum_tau_y"][frame] = sum_tau_y
			#member["sum_tau_z"][frame] = sum_tau_z # meist größer wegen senkrechter Last
			#member["max_sum_tau_y"][frame] = max(sum_tau_y)
			#member["max_sum_tau_z"][frame] = max(sum_tau_z) # meist größer wegen senkrechter Last

			# vergleichsspannung nach von misess, weggelassen, da nicht an gleicher Stelle
			#sigmav = []
			#for i in range(11): # get the stresses at 11 positions and
				#sv = sqrt(long_stress[i]**2 + 3*sum_tau_z[i]**2)  # vorläufig hier nur die durch z-Querkräfte verurachte Scherspannung genommen
				#sigmav.append(sv)

			#member["sigmav"][frame] = sigmav
			#member["max_sigmav"][frame] = max(sigmav)
			# check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

			member["sigma"][frame] = member["long_stress"][frame]
			member["max_sigma"][frame] = member["max_long_stress"][frame]

			# overstress
			member["overstress"][frame] = False

			# check overstress and add 1.05 savety factor
			safety_factor = 1.05
			if abs(member["max_tau_shear_y"][frame]) > safety_factor*member["acceptable_shear"]:
				member["overstress"][frame] = True

			if abs(member["max_tau_shear_z"][frame]) > safety_factor*member["acceptable_shear"]:
				member["overstress"][frame] = True
				
			if abs(member["max_tau_torsion"][frame]) > safety_factor*member["acceptable_torsion"]:
				member["overstress"][frame] = True
			
			# ist sigma hier richtig?
			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigmav"]:
				member["overstress"][frame] = True
				
			# buckling
			if member["axial"][frame][0] < 0: # nur für Druckstäbe, axial kann nicht flippen?
				# hier als ir das kleinere von ir_z und ir_y nehmen
				if member["ir_y"][frame] < member["ir_z"][frame]: ir = member["ir_y"][frame]
				else: ir = member["ir_z"][frame]
				member["lamda"][frame] = L*buckling_resolution*0.5/ir # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
				if member["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
					kn = member["knick_model"]
					function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
					member["acceptable_sigma_buckling"][frame] = function_to_run(member["lamda"][frame])
					if member["lamda"][frame] > 250: # zu schlank
						member["acceptable_sigma_buckling"][frame] = function_to_run(250)
						member["overstress"][frame] = True
					if safety_factor*abs(member["acceptable_sigma_buckling"][frame]) > abs(member["max_sigma"][frame]): # Sigma
						member["overstress"][frame] = True

				else:
					member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]

			# without buckling
			else:
				member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]
				member["lamda"][frame] = None # to avoid missing KeyError


			if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigma"]:
				member["overstress"][frame] = True

			# lever_arm
			lever_arm = []  # noch nicht überarbeitet
			moment_h = []  # noch nicht überarbeitet
			for i in range(11):
				# moment_h
				m_h = sqrt(moment_y[i]**2+moment_z[i]**2)
				moment_h.append(m_h)

				# to avoid division by zero
				if member["axial"][frame][i] < 0.1:
					lv = m_h / 0.1
				else:
					lv = m_h / member["axial"][frame][i]

				lv = abs(lv) # absolute highest value within member
				lever_arm.append(lv)

			member["moment_h"][frame] = moment_h
			member["lever_arm"][frame] = lever_arm
			member["max_lever_arm"][frame] = max(lever_arm)

			# Ausnutzungsgrad
			member["utilization"][frame] = abs(member["max_long_stress"][frame] / member["acceptable_sigma_buckling"][frame])

			# Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
			normalkraft_energy=[]
			moment_energy=[]
			strain_energy = []

			for i in range(10): # get the energie at 10 positions for 10 section
				# Berechnung der strain_energy für Normalkraft
				ne = (axial[i]**2)*(L/10)/(2*member["E"]*A)
				normalkraft_energy.append(ne)

				# Berechnung der strain_energy für Moment
				# moment_hq = moment_y[i]**2+moment_z[i]**2
				moment_y = member["moment_y"][frame][i]
				moment_z = member["moment_z"][frame][i]
				me = (moment_y**2 * L/10) / (2 * member["E"] * member["Iy"][frame]) + (moment_z**2 * L/10) / (2 * member["E"] * member["Iz"][frame]) # KD 2025-09_26
				
				#  nach https://roymech.org/Useful_Tables/Beams/Strain_Energy.html
				moment_energy.append(me)

				# Summe von Normalkraft und Moment-Verzerrunsenergie
				value = ne + me
				strain_energy.append(value)

			member["strain_energy"][frame] = strain_energy
			member["normal_energy"][frame] = normalkraft_energy
			member["moment_energy"][frame] = moment_energy

		# deflection
		deflection = []

		# --> taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite
		scale_factor = 10.0

		cos_x = array([T[0,0:3]]) # Direction cosines of local x-axis
		cos_y = array([T[1,0:3]]) # Direction cosines of local y-axis
		cos_z = array([T[2,0:3]]) # Direction cosines of local z-axis

		DY_plot = empty((0, 3))
		DZ_plot = empty((0, 3))

		for i in range(11):
			# Calculate the local y-direction displacement
			dy_tot = model_member.deflection('dy', L/10*i)

			# Calculate the scaled displacement in global coordinates
			DY_plot = append(DY_plot, dy_tot*cos_y*scale_factor, axis=0)

			# Calculate the local z-direction displacement
			dz_tot = model_member.deflection('dz', L/10*i)

			# Calculate the scaled displacement in global coordinates
			DZ_plot = append(DZ_plot, dz_tot*cos_z*scale_factor, axis=0)

		# Calculate the local x-axis displacements at 20 points along the member's length
		DX_plot = empty((0, 3))

		Xi = model_member.i_node.X
		Yi = model_member.i_node.Y
		Zi = model_member.i_node.Z

		for i in range(11):
			# Displacements in local coordinates
			dx_tot = [[Xi, Yi, Zi]] + (L/10*i + model_member.deflection('dx', L/10*i)*scale_factor)*cos_x

			# Magnified displacements in global coordinates
			DX_plot = append(DX_plot, dx_tot, axis=0)

		# Sum the component displacements to obtain overall displacement
		D_plot = DY_plot + DZ_plot + DX_plot

		# <-- taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite

		# add to results
		for i in range(11):
			x = D_plot[i, 0] * 0.01
			y = D_plot[i, 1] * 0.01
			z = D_plot[i, 2] * 0.01

			deflection.append([x,y,z])

		member["deflection"][frame] = deflection

	nodes = model.nodes

	for id in quads:
		quad = quads[id]

		# read results from PyNite
		result = model.quads[id]

		# only take highest value to zero
		shear = result.shear()
		moment = result.moment()
		membrane = result.membrane()

		# from PyNite
		Qx = float(shear[0])
		Qy = float(shear[1])

		Mx = float(moment[0])
		My = float(moment[1])
		Mxy = float(moment[2])

		Sx = float(membrane[0])
		Sy = float(membrane[1])
		Txy = float(membrane[2])

		#print("Qx:", Qx, "Qy:", Qy, "Mx:", Mx, "My:", My, "Mxy:", Mxy, "Sx:", Sx, "Sy:", Sy, "Txy:", Txy)

		# get deflection
		node_ids = quad["vertices_ids_structure"]
		deflection = []
		for i in range(4):
			# deflection only
			x = nodes[str(node_ids[i])].DX["Combo 1"]*0.1
			y = nodes[str(node_ids[i])].DY["Combo 1"]*0.1
			z = nodes[str(node_ids[i])].DZ["Combo 1"]*0.1

			# add deflection to initial position
			initial = quad["initial_positions"][frame][i]
			x += initial[0]
			y += initial[1]
			z += initial[2]

			deflection.append([x,y,z])

		# get average lengthes to calculate force by unit
		initial = quad["initial_positions"][frame]
		v_0 = array(initial[0])
		v_1 = array(initial[1])
		v_2 = array(initial[2])
		v_3 = array(initial[3])

		x_0 = v_1 - v_0 # first edge x
		x_1 = v_3 - v_2 # second edge x
		y_0 = v_2 - v_1 # first edge y
		y_1 = v_3 - v_0 # second edge y

		# as descripted in quad example
		length_x = (linalg.norm(x_0) + linalg.norm(x_1)) * 0.5 * 100 # to convert into cm
		length_y = (linalg.norm(y_0) + linalg.norm(y_1)) * 0.5 * 100 # to convert into cm

		# Schnittkräfte in unit-cm

		shear_x = Qx # Querkraft in kN  # für Darstellung
		shear_y = Qy # Querkraft in kN  # für Darstellung

		moment_x = Mx  # Moment in kNcm   # für Darstellung
		moment_y = My  # Moment in kNcm   # für Darstellung
		moment_xy = Mxy  # Drillmoment in kNcm   # für Darstellung

		thickness = quad["thickness"][frame]

		membrane_x = Sx * thickness  # Spannung in kN/cm   # für Darstellung
		membrane_y = Sy * thickness  # Spannung in kN/cm   # für Darstellung
		membrane_xy = Txy * thickness  #  Schubspannung in kN/cm   # für Darstellung

		# die Querschnittswerte sind jetzt auf 1 cm Schalenbreite bezogen
		# area of the section, not the face
		A = thickness * 1 # Dicke in cm² pro cm Schalenbreite

		# J = 1 * (thickness)**3 / 12

		# für buckling
		ir = thickness * 0.28867 # in cm  - Breite kürzt sich weg, es bleibt 1/wurzel aus 12
		# ir = sqrt(J/A) # in cm
		# modulus from the moments of area
		Wy = (thickness**2)/6  # auf 1 cm Schalenbreite

		# Spannungen in x und y Richrtung an den Oberflächen 1 und 2
		'''
		s_x_1 = membrane_x + moment_x/Wy  # für Darstellung
		s_x_2 = membrane_x - moment_x/Wy  # für Darstellung
		s_y_1 = membrane_y + moment_y/Wy  # für Darstellung
		s_y_2 = membrane_y - moment_y/Wy  # für Darstellung
		T_xy_1 = membrane_xy +  moment_xy/Wy # am Plattenrand, für Darstellung
		T_xy_2 = membrane_xy -  moment_xy/Wy # am Plattenrand, für Darstellung
		'''

		s_x_1 = membrane_x - moment_x/Wy  # für Darstellung
		s_x_2 = membrane_x + moment_x/Wy  # für Darstellung
		s_y_1 = membrane_y - moment_y/Wy  # für Darstellung
		s_y_2 = membrane_y + moment_y/Wy  # für Darstellung
		T_xy_1 = membrane_xy -  moment_xy/Wy # am Plattenrand, für Darstellung
		T_xy_2 = membrane_xy +  moment_xy/Wy # am Plattenrand, für Darstellung


		# Schubspannungen in x und y Richtung  infolge Querkraft in Plattenmitte
		T_x = 1.5 * shear_x/A   # in Plattenmitte
		T_y = 1.5 * shear_y/A   # in Plattenmitte

		# Hauptspannungen 1 und 2 an den Oberflächen 1 und 2
		# based on:
		# https://www.umwelt-campus.de/fileadmin/Umwelt-Campus/User/TPreussler/Download/Festigkeitslehre/Foliensaetze/01_Spannungszustand.pdf
		# https://technikermathe.de/tm2-hauptnormalspannung-berechnen
		# midpoint

		# first side
		if s_x_1 - s_y_1 == 0: # avoid div zero
			alpha = 0
		else:
			alpha = degrees(0.5 * arctan((2 * T_xy_1) / (s_x_1 - s_y_1)))

		s_1 = (s_x_1 + s_y_1)/2 + sqrt(((s_x_1 - s_y_1)/2)**2 + T_xy_1**2)
		s_2 = (s_x_1 + s_y_1)/2 - sqrt(((s_x_1 - s_y_1)/2)**2 + T_xy_1**2)
		s_xi = (s_x_1 + s_y_1)/2 + (s_x_1 - s_y_1)/2 * cos(2*radians(alpha)) + T_xy_1 * sin(2*radians(alpha))

		#if abs(s_1) > abs(s_2):
		if abs(s_1) > abs(s_2):
			s_1_1 = s_1
			s_2_1 = s_2
		else:
			s_1_1 = s_2
			s_2_1 = s_1

		if abs(round(s_1_1,2)) == abs(round(s_xi,2)):
			alpha_1 = alpha + 90
		else:
			alpha_1 = alpha

		# second side
		if s_x_2 - s_y_2 == 0: # avoid div zero
			alpha = 0
		else:
			alpha = degrees(0.5 * arctan((2 * T_xy_2) / (s_x_2 - s_y_2)))

		s_1 = (s_x_2 + s_y_2)/2 + sqrt(((s_x_2 - s_y_2)/2)**2 + T_xy_2**2)
		s_2 = (s_x_2 + s_y_2)/2 - sqrt(((s_x_2 - s_y_2)/2)**2 + T_xy_2**2)
		s_xi = (s_x_2 + s_y_2)/2 + (s_x_2 - s_y_2)/2 * cos(2*radians(alpha)) + T_xy_2 * sin(2*radians(alpha))

		if abs(s_1) > abs(s_2):
			s_1_2 = s_1
			s_2_2 = s_2
		else:
			s_1_2 = s_2
			s_2_2 = s_1

		if abs(round(s_1_2,2)) == abs(round(s_xi,2)):
			alpha_2 = alpha + 90
		else:
			alpha_2 = alpha

		# long_stress_x = s_x
		# sigma = s_x
		# long_stress_y = s_y
		# sigma_y = s_y
		# shear_xy = membrane_xy
		# tau_shear_xy = 1.5 * shear_x/A # for quads
		# tau_shear_y = 1.5 * shear_y/A # for quads
		# tau_shear_y = 1.5 * shear_y/A # for quads

		# Vergleichsspannung an den beiden Oberflächen 1 und 2
		sigmav1 = sqrt(s_x_1**2 + s_y_1**2 - s_x_1*s_y_1 + 3*T_xy_1**2)
		sigmav2 = sqrt(s_x_2**2 + s_y_2**2 - s_x_2*s_y_2 + 3*T_xy_2**2)

		# der größere Wert wird für die weitere Optimierung verwendet
		if sigmav2 > sigmav1:
			sigmav = sigmav2
		else:
			sigmav = sigmav1

		# Vergleichsspannung in Plattenmitte
		sigmav_m = sqrt(abs((membrane_x/A)**2 + (membrane_y/A)**2 - (membrane_x/A) * (membrane_y/A) + 3 * T_x * T_y))  # falls notwendig

		overstress = False
		# check overstress and add 1.05 safety factor
		safety_factor = 1.05
		#if abs(tau_shear) > safety_factor*quad["acceptable_shear"]:
		#	overstress = True

		if sigmav > safety_factor*quad["acceptable_sigmav"]:
			overstress = True

		# buckling in x-Richtung
		if membrane_x < 0: # nur für Druckstäbe, axial kann nicht flippen?
			quad["lamda"][frame] = length_x*5/ir # es wird hier von einer Knicklänge von 5 x der Elementlänge vorerst ausgegagen, in cm
			if quad["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
				kn = quad["knick_model"]
				function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
				acceptable_sigma_buckling_x = function_to_run(quad["lamda"][frame])
				if quad["lamda"][frame] > 250: # Schlankheit zu schlank
					acceptable_sigma_buckling_x = function_to_run(250)
					overstress = True
				if safety_factor*abs(acceptable_sigma_buckling_x) > abs(sigmav): # Sigma
					overstress = True

			else:
				acceptable_sigma_buckling_x = quad["acceptable_sigma"]
		# without buckling
		else:
			acceptable_sigma_buckling_x = quad["acceptable_sigma"]
			quad["lamda"][frame] = None # to avoid missing KeyError


		# buckling in y-Richtung
		if membrane_y < 0: # nur für Druckstäbe, axial kann nicht flippen?
			quad["lamda"][frame] = length_y*5/ir # es wird hier von einer Knicklänge von 5 x der Elementlänge vorerst ausgegagen, in cm
			if quad["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
				kn = quad["knick_model"]
				function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
				acceptable_sigma_buckling_y = function_to_run(quad["lamda"][frame])
				if quad["lamda"][frame] > 250: # Schlankheit zu schlank
					acceptable_sigma_buckling_y = function_to_run(250)
					overstress = True
				if safety_factor*abs(acceptable_sigma_buckling_y) > abs(sigmav): # Sigma
					overstress = True

			else:
				acceptable_sigma_buckling_y = quad["acceptable_sigma"]

		# without buckling
		else:
			acceptable_sigma_buckling_y = quad["acceptable_sigma"]
			quad["lamda"][frame] = None # to avoid missing KeyError

		# das kleinere ist maßgbend
		if acceptable_sigma_buckling_x < acceptable_sigma_buckling_y:
			quad["acceptable_sigma_buckling"][frame] = acceptable_sigma_buckling_x
		else:
			quad["acceptable_sigma_buckling"][frame] = acceptable_sigma_buckling_y

		if abs(sigmav) > safety_factor*quad["acceptable_sigma"]:
			overstress = True

		# Ausnutzungsgrad
		utilization = abs(sigmav / quad["acceptable_sigma_buckling"][frame])

		# vorerst noch weglassen
		# Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
		# Berechnung der strain_energy für Normalkraft
		# normalkraft_energie = (long_stress**2)*(length_x)/(2*quad["E"]*A)

		# Berechnung der strain_energy für Moment
		# moment_hq = moment_x**2+moment_y**2
		# moment_energie = (moment_hq * length_x) / (quad["E"] * Wy * thickness)

		# Summe von Normalkraft und Moment-Verzerrunsenergie
		# strain_energy = normalkraft_energie + moment_energie

		# save to dict
		quad["shear_x"][frame] = shear_x
		quad["shear_y"][frame] = shear_y

		quad["moment_x"][frame] = moment_x
		quad["moment_y"][frame] = moment_y
		quad["moment_xy"][frame] = moment_xy

		quad["membrane_x"][frame] = membrane_x
		quad["membrane_y"][frame] = membrane_y
		quad["membrane_xy"][frame] = membrane_xy

		quad["length_x"][frame] = length_x
		quad["length_y"][frame] = length_y

		quad["deflection"][frame] = deflection

		quad["ir"][frame] = ir
		quad["A"][frame] = A
		#quad["J"][frame] = J
		quad["Wy"][frame] = Wy
		#quad["moment_h"][frame] = moment_h
		#quad["long_stress"][frame] = long_stress
		#quad["shear_h"][frame] = shear_h
		#quad["tau_shear"][frame] = tau_shear
		quad["sigmav"][frame] = sigmav
		#quad["sigma"][frame] = quad["long_stress"][frame]

		quad["s_x_1"][frame] = s_x_1
		quad["s_x_2"][frame] = s_x_2
		quad["s_y_1"][frame] = s_y_1
		quad["s_y_2"][frame] = s_y_2
		quad["T_xy_1"][frame] = T_xy_1
		quad["T_xy_2"][frame] = T_xy_2

		quad["s_1_1"][frame] = s_1_1
		quad["s_2_1"][frame] = s_2_1
		quad["s_1_2"][frame] = s_1_2
		quad["s_2_2"][frame] = s_2_2

		quad["alpha_1"][frame] = alpha_1
		quad["alpha_2"][frame] = alpha_2

		quad["overstress"][frame] = overstress
		quad["utilization"][frame] = utilization

		#quad["strain_energy"][frame] = strain_energy
		#quad["normal_energy"][frame] = normalkraft_energie
		#quad["moment_energy"][frame] = moment_energie

	# get duration
	text = calculation_type + " involvement for frame " + str(frame) + " done"
	text +=  basics.timer.stop()
	basics.print_data(text)

	data["done"][str(frame)] = True

	# set frame for viz
	bpy.context.scene.frame_current = int(frame)
	bpy.context.view_layer.update()

def interweave_results_fd(frame):
	'''
	Function to integrate the results of force distribution.
	:param feas: Feas as dict with frame as key.
	:param members: Pass the members from <Phaenotyp>
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	members = data["members"]
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type

	frame = str(frame)
	model = basics.feas[frame]
	basics.timer.start()

	for id, member in members.items():
		id = int(id)
		# shorten
		I = member["Iy"][str(frame)]
		A = member["A"][str(frame)]
		E = member["E"]
		acceptable_sigma = member["acceptable_sigma"]
		L = member["length"][str(frame)] * 100

		force = model[id]
		sigma = force / A

		# with 500 cm, Do 60, Di 50, -10 kN
		'''
		print("I", I) # 32.9376 cm4
		print("A", A) # 8,64 cm2
		print("E", E) # 21000
		print("acceptable_sigma", acceptable_sigma) # 16.5
		print("L", L) # 500 cm
		print("force", force) # 10 kN
		print("sigma", sigma) # 1,16 kN/cm²
		'''

		overstress = False

		# if pressure check for buckling
		if force < 0:
			# based on:
			# https://www.johannes-strommer.com/rechner/knicken-von-edges_arrayn-euler/
			# euler buckling case 2: s = L
			FK = pi**2 * E * I / L**2
			S = FK / force
			if abs(S) < 2.5:
				overstress = True

			'''
			print("FK", FK) # 27,31 kN
			print("S", S) # 2,73 kN
			print("")
			'''

		# if tensile force
		else:
			if sigma > acceptable_sigma:
				overstress = True

		utilization = basics.avoid_div_zero(abs(acceptable_sigma), abs(sigma))

		member["axial"][str(frame)] = force
		member["sigma"][str(frame)] = sigma
		member["overstress"][str(frame)] = overstress
		member["utilization"][str(frame)] = utilization

	# get duration
	text = calculation_type + " involvement for frame " + str(frame) + " done"
	text +=  basics.timer.stop()
	basics.print_data(text)

	data["done"][str(frame)] = True

def calculate_frames(start, end):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	calculation_type = phaenotyp.calculation_type
	data = scene["<Phaenotyp>"]
	members = data["members"]
	quads = data["quads"]

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = prepare_fea_pn
		interweave_results = interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = prepare_fea_fd
		interweave_results = interweave_results_fd

	# create list of models in basics.models
	for frame in range(start, end):
		basics.jobs.append([prepare_fea, frame])

	# run mp and get results
	basics.jobs.append([run_mp, basics.models])

	# wait for it and interweave results to data
	for frame in range(start, end):
		basics.jobs.append([interweave_results, frame])

def approximate_sectional():
	'''
	Is adapting the diameters of force distribution step by step.
	Overstressed elements are sized by a factor of 1.05 and
	non overstressed are sized by 0.95.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	for id, member in members.items():
		if member["overstress"][str(frame)] == True:
			member["Do"][str(frame)] = member["Do"][str(frame)] * 1.05
			member["Di"][str(frame)] = member["Di"][str(frame)] * 1.05

		else:
			member["Do"][str(frame)] = member["Do"][str(frame)] * 0.95
			member["Di"][str(frame)] = member["Di"][str(frame)] * 0.95

		# set miminum size of Do and Di to avoid division by zero
		Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
		if member["Di"][str(frame)] < 0.1:
			member["Di"][str(frame)] = 0.1
			member["Do"][str(frame)] = member["Di"][str(frame)] * Do_Di_ratio

def simple_sectional():
	'''
	Is adapting the diameters of PyNite step by step.
	Overloaded Elements are sized by a factor of 1.2 and
	non overstressed are sized by 0.8.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	for id, member in members.items():
		if abs(member["max_long_stress"][str(frame)]/member["acceptable_sigma_buckling"][str(frame)]) > 1:
			member["Do"][str(frame)] = member["Do"][str(frame)] * 1.2
			member["Di"][str(frame)] = member["Di"][str(frame)] * 1.2

		else:
			member["Do"][str(frame)] = member["Do"][str(frame)] * 0.8
			member["Di"][str(frame)] = member["Di"][str(frame)] * 0.8

		# set miminum size of Do and Di to avoid division by zero
		Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
		if member["Di"][str(frame)] < 0.1:
			member["Di"][str(frame)] = 0.1
			member["Do"][str(frame)] = member["Di"][str(frame)] * Do_Di_ratio

def utilization_sectional():
	'''
	Is adapting the diameters of force distribution step by step.
	The reduction is based on the utilization of the elements.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	for id, member in members.items():
		ang = member["utilization"][str(frame)]

		# bei Fachwerkstäben
		#faktor_d = sqrt(abs(ang))

		# bei Biegestäben
		faktor_d= (abs(ang))**(1/3)

		Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
		member["Do"][str(frame)] = member["Do"][str(frame)] * faktor_d
		member["Di"][str(frame)] = member["Di"][str(frame)] * faktor_d

		# set miminum size of Do and Di to avoid division by zero
		Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
		if member["Di"][str(frame)] < 0.1:
			member["Di"][str(frame)] = 0.1
			member["Do"][str(frame)] = member["Di"][str(frame)] * Do_Di_ratio

def utilization_sectional_standardprofil():
	'''
	Is adapting the diameters of force distribution step by step.
	The reduction is based on the utilization of the elements.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	for id, member in members.items():
		ang = member["utilization"][str(frame)]
		faktor_d= (abs(ang))**(1/2)
		# neue Trägerhöhe:
		member["height"][str(frame)] = member["height"][str(frame)] * faktor_d
		# neue Trägerbreite:
		#iyr=0.0014*height**2+0.2791*height-35.215 # Zusammenhang Iy/A in Abhängigkeit der Trägerhöhe laut Profiltabellen
		if height < 30 # cm
				member["width"][str(frame)] = member["height"][str(frame)] # Breite bei HEB wie Höhe, bei IPE schmäler
		else
				member["width"][str(frame)] = 30 # Breite in cm

		# set miminum size of I-Träger: 100 mm
		if member["height"][str(frame)] < 10: # 10 cm
			member["height"][str(frame)] = 10
			member["width"][str(frame)] = 10
			
def complex_sectional():
	'''
	Is adapting the diameters of force distribution step by step.
	The reduction is based on the max_long_stress of the elements.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	frame = bpy.context.scene.frame_current

	for id, member in members.items():
		#treshhold bei Prüfung!
		# without buckling (Zugstab)

		if abs(member["max_long_stress"][str(frame)]/member["acceptable_sigma_buckling"][str(frame)]) > 1:
			faktor_a = 1+(abs(member["max_long_stress"][str(frame)])/member["acceptable_sigma_buckling"][str(frame)]-1)*0.36

		else:
			faktor_a = 0.5 + 0.6*(tanh((abs(member["max_long_stress"][str(frame)])/member["acceptable_sigma_buckling"][str(frame)] -0.5)*2.4))

		# bei Fachwerkstäben
		#faktor_d = sqrt(abs(faktor_a))

		# bei Biegestäben
		faktor_d = (abs(faktor_a))**(1/3)

		member["Do"][str(frame)] = member["Do"][str(frame)]*faktor_d
		member["Di"][str(frame)] = member["Di"][str(frame)]*faktor_d

		# set miminum size of Do and Di to avoid division by zero
		Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
		if member["Di"][str(frame)] < 0.1:
			member["Di"][str(frame)] = 0.1
			member["Do"][str(frame)] = member["Di"][str(frame)] * Do_Di_ratio

def quads_approximate_sectional():
	'''
	Is adapting the thickness of quads step by step.
	The reduction is based on the overstress of the elements.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	quads = data["quads"]
	frame = bpy.context.scene.frame_current

	for id, quad in quads.items():
		if quad["overstress"][str(frame)]:
			quad["thickness"][str(frame)] = quad["thickness"][str(frame)] * 1.1

		else:
			quad["thickness"][str(frame)] = quad["thickness"][str(frame)] * 0.9

def quads_utilization_sectional():
	'''
	Is adapting the thickness of quads by utilization.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	quads = data["quads"]
	frame = bpy.context.scene.frame_current

	for id, quad in quads.items():
		ang = quad["utilization"][str(frame)]
		faktor_d = (abs(ang))**(1/3) # taken from members
		quad["thickness"][str(frame)] = quad["thickness"][str(frame)] * faktor_d

def decimate_topology():
	'''
	Is creating a vertex-group with the utilization of each member.
	This vertex-group is used with a decimation modifiere to remove
	the elements with less load by given factor in the modifiers tab.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	obj = data["structure"] # applied to structure
	frame = bpy.context.scene.frame_current

	obj.hide_set(False)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.mode_set(mode = 'OBJECT')

	# create vertex-group if not existing
	decimate_group = obj.vertex_groups.get("<Phaenotyp>decimate")
	if not decimate_group:
		decimate_group = obj.vertex_groups.new(name="<Phaenotyp>decimate")

	# create factor-list
	weights = []
	for vertex in obj.data.vertices:
		weights.append([])

	# create factors for nodes from members
	for id, member in members.items():
		factor = member["utilization"][str(frame)]
		# first node
		vertex_0_id = member["vertex_0_id"]
		weights[vertex_0_id].append(factor)

		# second node
		vertex_1_id = member["vertex_1_id"]
		weights[vertex_1_id].append(factor)

	# sum up forces of each node and get highest value
	sums = []
	highest_sum = 0
	for id, weights_per_node in enumerate(weights):
		sum = 0
		if len(weights_per_node) > 0:
			for weight in weights_per_node:
				sum = sum + weight
				if sum > highest_sum:
					highest_sum = sum

		sums.append(sum)

	for id, sum in enumerate(sums):
		weight = 1 / highest_sum * sum
		decimate_group.add([id], weight, 'REPLACE')

	# delete modifiere if existing
	try:
		bpy.ops.object.modifier_remove(modifier="<Phaenotyp>decimate")
	except:
		pass

	# create decimate modifiere
	mod = obj.modifiers.new("<Phaenotyp>decimate", "DECIMATE")
	mod.ratio = 0.4
	mod.vertex_group = "<Phaenotyp>decimate"

	# select and switch to wireframe to see the edges
	bpy.context.view_layer.objects.active = obj
	basics.view_wireframe()

def decimate_topology_apply():
	'''
	Reset the modifiere to avoid that the user
	is workin gwith the decimated structure.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]
	obj = data["structure"] # applied to structure
	frame = bpy.context.scene.frame_current

	obj.hide_set(False)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.mode_set(mode = 'OBJECT')

	structure = data.get("structure")
	mod_name = "<Phaenotyp>decimate"
	mod = structure.modifiers[mod_name]

	# set structure to active
	bpy.context.view_layer.objects.active = structure
	obj.select_set(True)

	# go to object-mode
	bpy.ops.object.mode_set(mode='OBJECT')

	# apply modifiere
	bpy.ops.object.modifier_apply(modifier=mod_name)

def copy_d_t_from_prev(frame):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	quads = data["quads"]
	members = data["members"]

	# copy previous frame to current
	for id, member in members.items():
		member["Do"][str(frame)] = member["Do"][str(frame-1)]
		member["Di"][str(frame)] = member["Di"][str(frame-1)]

		member["overstress"][str(frame)] = member["overstress"][str(frame-1)]
		member["utilization"][str(frame)] = member["utilization"][str(frame-1)]
		member["max_long_stress"][str(frame)] = member["max_long_stress"][str(frame-1)]
		member["acceptable_sigma_buckling"][str(frame)] = member["acceptable_sigma_buckling"][str(frame-1)]

	for id, quad in quads.items():
		quad["thickness"][str(frame)] = quad["thickness"][str(frame-1)]
		quad["overstress"][str(frame)] = quad["overstress"][str(frame-1)]

def sectional_optimization(frame):
	'''
	Is handling the different types of optimization for animation, bf,
	gd and ga. The function is reading the type of calculation from
	phaenotyp directly.
	:param start: Start frame to begin at.
	:param end: End frame to stop with.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.get("shape_keys")
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = prepare_fea_pn
		interweave_results = interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = prepare_fea_fd
		interweave_results = interweave_results_fd

	# update scene
	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()

	if phaenotyp.calculation_type == "force_distribution":
		if phaenotyp.optimization_fd == "approximate":
			approximate_sectional()

	else:
		if phaenotyp.optimization_pn == "simple":
			simple_sectional()

		if phaenotyp.optimization_pn == "utilization":
			utilization_sectional()

		if phaenotyp.optimization_pn == "complex":
			complex_sectional()

		if phaenotyp.optimization_quads == "approximate":
			quads_approximate_sectional()

		if phaenotyp.optimization_quads == "utilization":
			quads_utilization_sectional()

	# apply shape keys
	if shape_keys:
		#.get(key_blocks)
		shape_keys = data.shape_keys
		chromosome = data.chromosome[str(frame)]
		geometry.set_shape_keys(shape_keys, chromosome)

	text = "sectional_optimization for " + str(frame) + " done"
	basics.print_data(text)

def set_basis_fitness():
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	individuals = data["individuals"]
	individuals["0"]["fitness"]["weighted"] = 1

def calculate_fitness(frame):
	'''
	Is calculating the fitness fo the given frame.
	:param frame: Frame to work with
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	members = data["members"]
	quads = data["quads"]

	bpy.context.scene.frame_current = frame

	environment = data["environment"]
	individuals = data["individuals"]

	# calculate fitness
	individual = individuals[str(frame)]

	# volume
	volume = data["frames"][str(frame)]["volume"]
	fitness_volume = volume

	# area
	area = data["frames"][str(frame)]["area"]
	fitness_area = area

	# weight
	weight = data["frames"][str(frame)]["weight"]
	fitness_weight = weight

	# rise
	rise = data["frames"][str(frame)]["rise"]
	fitness_rise = rise

	# span
	span = data["frames"][str(frame)]["span"]
	fitness_span = span

	# cantilever
	cantilever = data["frames"][str(frame)]["cantilever"]
	fitness_cantilever = cantilever

	if phaenotyp.calculation_type != "geometrical":
		if phaenotyp.calculation_type != "force_distribution":
			# deflection for members
			forces = []
			for id, member in members.items():
				v_0 = member["initial_positions"][str(frame)]
				v_1 = member["deflection"][str(frame)]

				v_0 = array(v_0)
				v_1 = array(v_1)

				# mulitply with 0.5  because two vertices per member
				dist = (linalg.norm(v_1) + linalg.norm(v_0)) * 0.5

				forces.append(dist)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			fitness_deflection_members = basics.avoid_div_zero(sum_forces, len(forces))

			# deflection for quads
			forces = []
			for id, quad in quads.items():
				for i in range(4):
					v_0 = quad["initial_positions"][str(frame)][i]
					v_1 = quad["deflection"][str(frame)][i]

					v_0 = array(v_0)
					v_1 = array(v_1)

					# mulitply with 0.25  because four vertices per quad
					dist = (linalg.norm(v_1) + linalg.norm(v_0)) * 0.25

					forces.append(dist)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			fitness_deflection_quads = basics.avoid_div_zero(sum_forces, len(forces))

			# average_sigma members
			forces = []
			for id, member in members.items():
				force = member["max_sigma"][str(frame)]
				forces.append(force)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			fitness_average_sigma_members = basics.avoid_div_zero(sum_forces, len(forces))

			# average_sigmav quads
			forces = []
			for id, quad in quads.items():
				force = quad["sigmav"][str(frame)]
				forces.append(force)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			fitness_average_sigmav_quads = basics.avoid_div_zero(sum_forces, len(forces))

		else:
			# average_sigma for force_distribution -> max_sigma = sigma
			forces = []
			for id, member in members.items():
				force = member["sigma"][str(frame)]
				forces.append(force)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			fitness_average_sigma_members = sum_forces / len(forces)

		if phaenotyp.calculation_type != "force_distribution":
			# average_strain_energy
			forces = []
			for id, member in members.items():
				values = []
				for value in member["strain_energy"][str(frame)]:
					values.append(value)
				force = basics.return_max_diff_to_zero(values)
				forces.append(force)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			if len(forces) > 0:
				fitness_average_strain_energy = sum_forces / len(forces)
			else:
				fitness_average_strain_energy = 0

		'''
		if environment["fitness_function"] == "lever_arm_model":
			forces = []
			for id, member in members.items():
				force = member["max_lever_arm"][str(frame)]
				forces.append(force)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			fitness = sum_forces *(-1)

		if environment["fitness_function"] == "lever_arm_bending":
			forces = []
			for id, member in members.items():
				force = member["max_lever_arm"][str(frame)]
				forces.append(force)

			sum_forces = 0
			for force in forces:
				sum_forces = sum_forces + abs(force)

			fitness = sum_forces
		'''

	# pass to individual
	individual["fitness"]["volume"] = fitness_volume
	individual["fitness"]["area"] = fitness_area
	individual["fitness"]["weight"] = fitness_weight
	individual["fitness"]["rise"] = fitness_rise
	individual["fitness"]["span"] = fitness_span
	individual["fitness"]["cantilever"] = fitness_cantilever
	if phaenotyp.calculation_type != "geometrical":
		individual["fitness"]["deflection_members"] = fitness_deflection_members
		individual["fitness"]["average_sigma_members"] = fitness_average_sigma_members
		if phaenotyp.calculation_type != "force_distribution":
			individual["fitness"]["deflection_quads"] = fitness_deflection_quads
			individual["fitness"]["average_sigmav_quads"] = fitness_average_sigmav_quads
			individual["fitness"]["average_strain_energy"] = fitness_average_strain_energy

	if frame != 0:
		# get from basis
		basis_fitness = individuals["0"]["fitness"]

		# flipped values
		if phaenotyp.fitness_volume_invert:
			weighted = basics.avoid_div_zero(1, fitness_volume) * basis_fitness["volume"] * phaenotyp.fitness_volume
		# the values of weighted at basis is 1, all other frames are weighted to this value
		else:
			weighted = basics.avoid_div_zero(1, basis_fitness["volume"]) * fitness_volume * phaenotyp.fitness_volume

		if phaenotyp.fitness_area_invert:
			weighted += basics.avoid_div_zero(1, fitness_area) * basis_fitness["area"] * phaenotyp.fitness_area
		else:
			weighted += basics.avoid_div_zero(1, basis_fitness["area"]) * fitness_area * phaenotyp.fitness_area

		if phaenotyp.fitness_weight_invert:
			weighted += basics.avoid_div_zero(1, fitness_weight) * basis_fitness["weight"] * phaenotyp.fitness_weight
		else:
			weighted += basics.avoid_div_zero(1, basis_fitness["weight"]) * fitness_weight * phaenotyp.fitness_weight

		if phaenotyp.fitness_rise_invert:
			weighted += basics.avoid_div_zero(1, fitness_rise) * basis_fitness["rise"] * phaenotyp.fitness_rise
		else:
			weighted += basics.avoid_div_zero(1, basis_fitness["rise"]) * fitness_rise * phaenotyp.fitness_rise

		if phaenotyp.fitness_span_invert:
			weighted += basics.avoid_div_zero(1, fitness_span) * basis_fitness["span"] * phaenotyp.fitness_span
		else:
			weighted += basics.avoid_div_zero(1, basis_fitness["span"]) * fitness_span * phaenotyp.fitness_span

		if phaenotyp.fitness_cantilever_invert:
			weighted += basics.avoid_div_zero(1, fitness_cantilever) * basis_fitness["cantilever"] * phaenotyp.fitness_cantilever
		else:
			weighted += basics.avoid_div_zero(1, basis_fitness["cantilever"]) * fitness_cantilever * phaenotyp.fitness_cantilever

		if phaenotyp.calculation_type != "geometrical":
			if phaenotyp.fitness_deflection_members_invert:
				weighted += basics.avoid_div_zero(1, fitness_deflection_members) * basis_fitness["deflection_members"] * phaenotyp.fitness_deflection_members
			else:
				weighted += basics.avoid_div_zero(1, basis_fitness["deflection_members"]) * fitness_deflection_members * phaenotyp.fitness_deflection_members

			weighted += basics.avoid_div_zero(1, basis_fitness["average_sigma_members"]) * fitness_average_sigma_members * phaenotyp.fitness_average_sigma_members

			if phaenotyp.calculation_type != "force_distribution":
				if phaenotyp.fitness_deflection_quads_invert:
					weighted += basics.avoid_div_zero(1, fitness_deflection_quads) * basis_fitness["deflection_quads"] * phaenotyp.fitness_deflection_quads
				else:
					weighted += basics.avoid_div_zero(1, basis_fitness["deflection_quads"]) * fitness_deflection_quads * phaenotyp.fitness_deflection_quads

				weighted += basics.avoid_div_zero(1, basis_fitness["average_sigmav_quads"]) * fitness_average_sigmav_quads * phaenotyp.fitness_average_sigmav_quads
				weighted += basics.avoid_div_zero(1, basis_fitness["average_strain_energy"]) * fitness_average_strain_energy * phaenotyp.fitness_average_strain_energy


		# if all sliders are set to one, the weight is 6 (with 6 fitness sliders)
		weight = phaenotyp.fitness_volume
		weight += phaenotyp.fitness_area
		weight += phaenotyp.fitness_weight
		weight += phaenotyp.fitness_rise
		weight += phaenotyp.fitness_span
		weight += phaenotyp.fitness_cantilever
		if phaenotyp.calculation_type != "geometrical":
			weight += phaenotyp.fitness_deflection_members
			weight += phaenotyp.fitness_deflection_quads
			weight += phaenotyp.fitness_average_sigma_members
			if phaenotyp.calculation_type != "force_distribution":
				weight += phaenotyp.fitness_average_sigmav_quads
				weight += phaenotyp.fitness_average_strain_energy

		# the overall weighted-value is always 1 for the basis individual
		individual["fitness"]["weighted"] = basics.avoid_div_zero(weighted, weight)

	text = "calculate fitness for frame " + str(frame) + " done"
	basics.print_data(text)
