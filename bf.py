import bpy
import bmesh
import random
from phaenotyp import basics, geometry, calculation, progress

def print_data(text):
	"""
	Print data for debugging
	:param text: Needs a text as string (Do not pass as list)
	"""
	print("Phaenotyp |", text)

def create_indivdual(chromosome):
	"""
	Creates an individual for bruteforce mode.
	:param chromosome: The chromosome is a list of floats from 0 to 10.
	"""
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]
	frame = bpy.context.scene.frame_current

	environment = data["environment"]
	individuals = data["individuals"]

	# apply shape keys
	for id, key in enumerate(shape_keys):
		if id > 0: # to exlude basis
			key.value = chromosome[id-1]*0.1

	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome
	individual["fitness"] = {}

	individuals[str(frame)] = individual

def generate_basis():
	"""
	Creates the basis individual for bruteforce mode.
	It is the basis for calculating the weighted fitness of all other individuals.
	"""
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		run_st = calculation.run_st_pn
		interweave_results = calculation.interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		run_st = calculation.run_st_fd
		interweave_results = calculation.interweave_results_fd

	# create list of trusses
	trusses = {}

	# create chromosome all set to 0
	chromosome = []
	for gnome_len in range(len(shape_keys)-1): # -1 to exlude basis
		gene = 0
		chromosome.append(gene)

	# update scene
	bpy.context.scene.frame_current = 0
	bpy.context.view_layer.update()

	create_indivdual(chromosome) # and change frame to shape key

	# calculate new properties for each member
	geometry.update_members_pre()

	# created a truss object of PyNite and add to dict
	truss = prepare_fea()
	trusses[0] = truss

	if phaenotyp.calculation_type != "geometrical":
		# run mp and get results
		feas = calculation.run_mp(trusses)

		# wait for it and interweave results to data
		interweave_results(feas, members)

def bruteforce(chromosomes):
	"""
	Mainfunction to run brutforce.
	:param chromosomes: List of chromosomes as lists of floats from 0 to 10.
	"""
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]

	# create list of trusses
	trusses = {}

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		run_st = calculation.run_st_pn
		interweave_results = calculation.interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		run_st = calculation.run_st_fd
		interweave_results = calculation.interweave_results_fd

	# for progress
	end = bpy.context.scene.frame_end

	for i, chromosome in enumerate(chromosomes):
		# update scene
		frame = i+1  # exclude basis indivual
		bpy.context.scene.frame_current = frame
		bpy.context.view_layer.update()

		create_indivdual(chromosome) # and change frame to shape key

		# calculate new properties for each member
		geometry.update_members_pre()

		# created a truss object of PyNite and add to dict
		truss = prepare_fea()
		trusses[frame] = truss

	if phaenotyp.calculation_type != "geometrical":
		# run mp and get results
		feas = calculation.run_mp(trusses)

		# wait for it and interweave results to data
		interweave_results(feas, members)
