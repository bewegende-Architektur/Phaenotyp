import bpy
from phaenotyp import operators, geometry, calculation, progress
import numpy as np

def print_data(text):
	"""
	Print data for debugging
	:param text: Needs a text as string (Do not pass as list)
	"""
	print("Phaenotyp |", text)

def generate_basis():
	'''
	Generate the basis individual to work with.
	The fitness of all others are weighted with this first individual.
	'''
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
	frame = 0
	bpy.context.scene.frame_start = frame
	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()

	# create indiviual
	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome
	individual["fitness"] = {}

	individuals[str(frame)] = individual

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		run_st = calculation.run_st_pn
		interweave_results = calculation.interweave_results_pn
		
		optimization_type = phaenotyp.optimization_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		run_st = calculation.run_st_fd
		interweave_results = calculation.interweave_results_fd
		
		optimization_type = phaenotyp.optimization_fd

	# calculate frame
	geometry.update_members_pre()
	truss = prepare_fea()
	fea = run_st(truss, frame)
	interweave_results(fea, members)
	geometry.update_members_post()

	# optimization
	if optimization_type != "none":
		progress.http.reset_o(phaenotyp.optimization_amount)
		for i in range(phaenotyp.optimization_amount):
			calculation.sectional_optimization(frame, frame+1)
			progress.http.update_o()

	# get fitness
	calculation.calculate_fitness(frame, frame+1)
	individuals["0"]["fitness"]["weighted"] = 1

def make_step(chromosome, frame):
	'''
	Make a step with the adapted chromosome.
	:paramm chromosome: List of floats from 0 to 10.
	:frame: Frame to save this individual to.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	members = data["members"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]

	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()

	# apply shape keys
	for id, key in enumerate(shape_keys):
		if id > 0: # to exlude basis
			key.value = chromosome[id-1]*0.1

	# create indivual
	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome
	individual["fitness"] = {}

	individuals[str(frame)] = individual

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		run_st = calculation.run_st_pn
		interweave_results = calculation.interweave_results_pn
		
		optimization_type = phaenotyp.optimization_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		run_st = calculation.run_st_fd
		interweave_results = calculation.interweave_results_fd
		
		optimization_type = phaenotyp.optimization_fd

	# calculate frame
	geometry.update_members_pre()
	truss = prepare_fea()
	fea = run_st(truss, frame)
	interweave_results(fea, members)
	geometry.update_members_post()

	# optimization
	if optimization_type != "none":
		progress.http.reset_o(phaenotyp.optimization_amount)
		for i in range(phaenotyp.optimization_amount):
			calculation.sectional_optimization(frame, frame+1)
			progress.http.update_o()

	# calculate fitness
	calculation.calculate_fitness(frame, frame+1)

	# get data from individual
	gd = individuals[str(frame)]
	fitness = gd["fitness"]["weighted"]

	text = "Step " + gd["name"] + " with fitness: " + str(fitness) + "\n"
	print_data(text)

	return gd, fitness

def start():
	'''
	Main function to run gradient descent.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	members = data["members"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]

	# get data from gui
	delta = phaenotyp.gd_delta
	learning_rate = phaenotyp.gd_learning_rate
	abort = phaenotyp.gd_abort
	maxiteration = phaenotyp.gd_max_iteration

	progress.http.reset_pci(phaenotyp.gd_max_iteration+1)
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none":
		progress.http.reset_o(phaenotyp.optimization_amount)
	
	# generate_basis for fitness
	generate_basis()

	# set frame to 0
	frame = 0

	# starting point with all genes set to 0.5
	# for three shape keys this is [0.5, 0.5, 0.5]
	# (unlike the basis for fitness with all genes 0)
	chromosome_start = []
	slope = [0]
	for i in range(len(shape_keys)-1):
		chromosome_start.append(0.5)
		slope.append(0)

	text = "Starting at: " + str(chromosome_start) + "\n"
	print_data(text)
	chromosome_current = chromosome_start

	iteration = 0
	while iteration < maxiteration:
		# update frame
		frame += 1

		# make step
		gd, fitness = make_step(chromosome_current, frame)

		# pass old fitness
		fitness_old = fitness

		# copy current chromosome
		chromosome = chromosome_current.copy()

		# create variations of keys
		for key_id in range(len(shape_keys)-1):
			# update frame
			frame += 1

			# update chromosome
			chromosome[key_id] += delta

			# make next step
			gd, fitness = make_step(chromosome, frame)

			# calculate slope
			slope[key_id] = (fitness - fitness_old) / delta
			text = "Slope of key " + str(key_id) + str(slope[key_id])
			print_data(text)

			# new direction
			chromosome_current[key_id] = chromosome_current[key_id] - slope[key_id] * learning_rate
			if chromosome_current[key_id] < 0:
				chromosome_current[key_id] = 0
				slope[key_id] = 0

			if chromosome_current[key_id] > 1:
				chromosome_current[key_id] = 1
				slope[key_id] = 0

		text = "New step: " + str(chromosome_current)
		print_data(text)

		vector = (np.linalg.norm(slope))*learning_rate
		text = "Vector: " + str(vector)
		print_data(text)

		iteration += 1

		if vector < abort:
			break
