import bpy
from phaenotyp import operators, geometry, calculation, progress
import numpy as np

def print_data(text):
	"""
	Print data for debugging
	:param text: Needs a text as string (Do not pass as list)
	"""
	print("Phaenotyp |", text)

def generate_basis(chromosome):
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
		interweave_results = calculation.interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		interweave_results = calculation.interweave_results_fd

	# update scene
	frame = 0
	bpy.context.scene.frame_start = frame
	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()

	# apply shape keys
	geometry.set_shape_keys(shape_keys, chromosome)

	# create indiviual
	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome
	individual["fitness"] = {}

	individuals[str(frame)] = individual

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		interweave_results = calculation.interweave_results_pn
		
		optimization_type = phaenotyp.optimization_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		interweave_results = calculation.interweave_results_fd
		
		optimization_type = phaenotyp.optimization_fd
	
	# calculate frame
	geometry.update_geometry_pre()
	
	trusses = {}
	trusses[str(frame)] = prepare_fea()

	# run singlethread and get results
	feas = calculation.run_mp(trusses)
	
	interweave_results(fea, members)
	geometry.update_geometry_post()

	# optimization
	if optimization_type != "none":
		progress.http.reset_o(phaenotyp.optimization_amount)
		for i in range(phaenotyp.optimization_amount):
			calculation.sectional_optimization(frame, frame+1)
			progress.http.update_o()

	# get fitness
	calculation.calculate_fitness(frame, frame+1)
	individuals["0"]["fitness"]["weighted"] = 1

def make_step_st(chromosome, frame):
	'''
	Make a step with the adapted chromosome.
	:paramm chromosome: List of floats from 0 to 1.
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

	# update frame
	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()
	
	# apply shape keys
	geometry.set_shape_keys(shape_keys, chromosome)
	
	# create indivual
	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome
	individual["fitness"] = {}

	individuals[str(frame)] = individual

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		interweave_results = calculation.interweave_results_pn
		
		optimization_type = phaenotyp.optimization_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		interweave_results = calculation.interweave_results_fd
		
		optimization_type = phaenotyp.optimization_fd
	
	# calculate frame
	geometry.update_geometry_pre()
	
	# created a truss object
	trusses = {}
	trusses[str(frame)] = prepare_fea()

	# run singlethread and get results
	feas = calculation.run_mp(trusses)
	
	interweave_results(fea, members)
	geometry.update_geometry_post()

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

	text = "Step " + gd["name"] + " with fitness: " + str(round(fitness, 3))
	print_data(text)

	return gd, fitness

def make_step_mp(chromosome, frame):
	'''
	Make a step with the adapted chromosome.
	:paramm chromosome: List of floats from 0 to 1.
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

	# update frame
	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()
	
	# apply shape keys
	geometry.set_shape_keys(shape_keys, chromosome)
	
	# create indivual
	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome
	individual["fitness"] = {}

	individuals[str(frame)] = individual

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
	
	# calculate frame
	geometry.update_geometry_pre()
	truss = prepare_fea()
	
	return truss

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

	progress.http.reset_pci(maxiteration * (len(shape_keys)-1) + 1 + maxiteration)
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none":
		progress.http.reset_o(phaenotyp.optimization_amount)
	
	# set frame to 0
	frame = 0

	# starting point the current set of values
	chromosome_start = []
	slope = []
	for id, key in enumerate(shape_keys):
		if id > 0:
			v = key.value
			chromosome_start.append(v)
			slope.append(0)

	# generate_basis for fitness
	generate_basis(chromosome_start)
	
	rounded_chromosome = [round(num, 3) for num in chromosome_start]
	text = "Starting at: " + str(rounded_chromosome) + "\n"
	print_data(text)
	chromosome_current = chromosome_start

	iteration = 0

	# for PyNite
	if phaenotyp.calculation_type != "force_distribution":
		prepare_fea = calculation.prepare_fea_pn
		interweave_results = calculation.interweave_results_pn

	# for force distribuion
	else:
		prepare_fea = calculation.prepare_fea_fd
		interweave_results = calculation.interweave_results_fd
	
	# optimization
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

	progress.http.reset_o(optimization_amount)
		
	while iteration < maxiteration:
		# update frame
		frame += 1

		# make step and optimize afterwards
		gd, fitness = make_step_st(chromosome_current, frame)

		# pass old fitness
		fitness_old = fitness

		# copy current chromosome
		chromosome = chromosome_current.copy()

		# create list of trusses
		trusses = {}

		# create variations of keys and calculate with mp
		calculated_frames = [] # to access them later

		for key_id in range(len(shape_keys)-1):
			# update frame
			frame += 1
			
			# append frame as int
			calculated_frames.append(frame)

			# update chromosome
			chromosome[key_id] += delta

			# with  multiprocessing
			truss = make_step_mp(chromosome, frame)

			# update scene
			bpy.context.scene.frame_current = frame
			bpy.context.view_layer.update()

			# calculate new properties for each member
			geometry.update_geometry_pre()

			# created a truss object of PyNite and add to dict
			trusses[str(frame)] = truss

		if phaenotyp.calculation_type != "geometrical":
			# run mp and get results
			feas = calculation.run_mp(trusses)

			# wait for it and interweave results to data
			interweave_results(feas, members)
		
		# optimization
		print_data("start optimization:")
		for i in range(optimization_amount):
			start_opt = calculated_frames[0]
			end_opt = calculated_frames[len(calculated_frames)-1]
			calculation.sectional_optimization(start_opt, end_opt)
			
			# to avoid wrong counting
			progress.http.p[0] -= optimization_amount
			progress.http.c[0] -= optimization_amount
			progress.http.i[0] -= optimization_amount
			
		print_data("optimization done")
		
		# create variations of keys
		for key_id, frame in enumerate(calculated_frames):
			# calculate fitness
			calculation.calculate_fitness(frame, frame+1)

			# get data from individual
			gd = individuals[str(frame)]
			fitness = gd["fitness"]["weighted"]

			text = "Step " + gd["name"] + " with fitness: " + str(round(fitness, 3))
			print_data(text)
			
			# calculate slope
			# (in new loop with multiprocessing)
			slope[key_id] = (fitness - fitness_old) / delta
			text = "Slope of key " + str(key_id) + " = " + str(round(slope[key_id], 3))
			print_data(text)

			# new direction
			chromosome_current[key_id] = chromosome_current[key_id] - slope[key_id] * learning_rate
			if chromosome_current[key_id] < 0:
				chromosome_current[key_id] = 0
				slope[key_id] = 0

			if chromosome_current[key_id] > 1:
				chromosome_current[key_id] = 1
				slope[key_id] = 0
		
		text = "Iteration: " + str(iteration) + "|"+  str(maxiteration)
		print_data(text)
		
		rounded_chromosome = [round(num, 3) for num in chromosome_current]
		text = "New step: " + str(rounded_chromosome)
		print_data(text)

		vector = (np.linalg.norm(slope))*learning_rate
		text = "Vector: " + str(round(vector, 3)) + "\n"
		print_data(text)
		
		iteration += 1

		if vector < abort:
			text = "Goal reached"
			print_data(text)
			break
		
	bpy.context.scene.frame_end = frame
