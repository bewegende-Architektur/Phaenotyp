import bpy
from phaenotyp import basics, operators, geometry, calculation
import numpy as np

def create_indivdual(chromosome, frame):
	"""
	Creates an individual for bruteforce mode.
	:param chromosome: The chromosome is a list of floats from 0 to 1.
	"""
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks

	environment = data["environment"]
	individuals = data["individuals"]
	
	# apply shape keys
	geometry.set_shape_keys(shape_keys, chromosome)

	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome
	individual["fitness"] = {}

	individuals[str(frame)] = individual

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

	environment = data["environment"]
	individuals = data["individuals"]
	
	# update scene
	frame = 0

	bpy.context.scene.frame_start = frame
	bpy.context.scene.frame_current = frame
	bpy.context.view_layer.update()

	# starting point is the current set of values
	# in this way users can choose where to start from
	chromosome = []
	slope = []
	for id, key in enumerate(shape_keys):
		if id > 0:
			v = key.value
			chromosome.append(v)
			slope.append(0)
	
	# create indiviual
	create_indivdual(chromosome, 0)

	rounded_chromosome = [round(num, 3) for num in chromosome]
	text = "Starting at: " + str(rounded_chromosome) + "\n"
	basics.print_data(text)
	print(chromosome)
	
	# store in basics for later
	basics.chromosome_current = chromosome
	basics.slope = slope

def calculate_basis():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
		# calculate frames
		calculation.calculate_frames(0, 1)
	
		for i in range(phaenotyp.optimization_amount):
			# optimize each frame
			basics.jobs.append([calculation.sectional_optimization, 0])
				
			# calculate frames again
			calculation.calculate_frames(0, 1)
	
	# without optimization
	else:
		# calculate frames
		calculation.calculate_frames(0, 1)
	
	# calculate fitness and set weight for basis
	basics.jobs.append([calculation.calculate_fitness, 0])
	basics.jobs.append([calculation.set_basis_fitness])
	
def make_step_st(frame):
	'''
	Make a step with the adapted chromosome.
	:paramm chromosome: List of floats from 0 to 1.
	:frame: Frame to save this individual to.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]
	
	# get current chromosome
	chromosome = basics.chromosome_current
	
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

def calculate_step_st(frame):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
		# calculate frames
		calculation.calculate_frames(frame, frame+1)
	
		for i in range(phaenotyp.optimization_amount):
			# optimize each frame
			basics.jobs.append([calculation.sectional_optimization, frame])
				
			# calculate frames again
			calculation.calculate_frames(frame, frame+1)
	
	# without optimization
	else:
		# calculate frames
		calculation.calculate_frames(frame, frame+1)
	
	# calculate fitness
	basics.jobs.append([calculation.calculate_fitness, frame])

def get_step_st(frame):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]
	
	# get data from individual
	gd = individuals[str(frame)]
	fitness = gd["fitness"]["weighted"]

	text = "Step " + gd["name"] + " with fitness: " + str(round(fitness, 3))
	basics.print_data(text)
	
	basics.gd = gd
	basics.fitness = fitness

def create_variations(frame):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	# copy current chromosome
	chromosome = basics.chromosome_current.copy()
	
	# delta
	delta = basics.delta
	
	# create variations of keys and calculate with mp
	calculated_frames = [] # to access them later
	
	for key_id in range(len(shape_keys)-1):
		# update frame
		frame += 1

		# update chromosome
		chromosome[key_id] += delta
		
		# create individual
		create_indivdual(chromosome, frame)

def make_step_mp(frames):
	start, end = frames
	
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
		# calculate frames
		calculation.calculate_frames(start, end)
		
		for i in range(phaenotyp.optimization_amount):
			for frame in range(start, end):
				# optimize each frame
				basics.jobs.append([calculation.sectional_optimization, frame])
					
			# calculate frames again
			calculation.calculate_frames(start, end)
	
	# without optimization
	else:
		# calculate frames
		calculation.calculate_frames(start, end)
	
	# calculate fitness
	for frame in range(start, end):
		basics.jobs.append([calculation.calculate_fitness, frame])
	
def get_next_step(frames):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]
	
	fitness_old = basics.fitness
	slope = basics.slope
	chromosome_current = basics.chromosome_current
	
	delta = basics.delta
	learning_rate = basics.learning_rate
	iteration = basics.iteration
	max_iteration = basics.max_iteration
	abort = basics.abort
	
	for key_id, frame in enumerate(frames):
		# get data from individual
		gd = individuals[str(frame)]
		fitness = gd["fitness"]["weighted"]

		text = "Step " + gd["name"] + " with fitness: " + str(round(fitness, 3))
		basics.print_data(text)
		
		# calculate slope
		# (in new loop with multiprocessing)
		slope[key_id] = (fitness - fitness_old) / delta
		text = "Slope of key " + str(key_id) + " = " + str(round(slope[key_id], 3))
		basics.print_data(text)

		# new direction
		chromosome_current[key_id] = chromosome_current[key_id] - slope[key_id] * learning_rate
		if chromosome_current[key_id] < 0:
			chromosome_current[key_id] = 0
			slope[key_id] = 0

		if chromosome_current[key_id] > 1:
			chromosome_current[key_id] = 1
			slope[key_id] = 0
	
	text = "Iteration: " + str(iteration) + "|"+  str(max_iteration)
	basics.print_data(text)
	
	rounded_chromosome = [round(num, 3) for num in chromosome_current]
	text = "New step: " + str(rounded_chromosome)
	basics.print_data(text)

	vector = (np.linalg.norm(slope))*learning_rate
	text = "Vector: " + str(round(vector, 3)) + "\n"
	basics.print_data(text)

	basics.iteration += 1
	basics.fitness = fitness
	basics.slope = slope

	if vector < abort:
		text = "Goal reached"
		basics.print_data(text)
		
		# delete jobs
		basics.jobs = []
		
		# and append finish
		basics.jobs.append([finish])
		
		bpy.context.scene.frame_end = frame

def finish():
	# update view
	basics.jobs.append([basics.view_vertex_colors])
	
	# print done
	basics.jobs.append([basics.print_data, "done"])
	
def start():
	'''
	Main function to run gradient descent.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]

	# get data from gui
	delta = phaenotyp.gd_delta
	learning_rate = phaenotyp.gd_learning_rate
	abort = phaenotyp.gd_abort
	max_iteration = phaenotyp.gd_max_iteration

	# set frame and iteration
	frame = 0
	iteration = 0

	# create temp variables and dictionaries
	basics.models = {}
	basics.feas = {}
	
	basics.delta = delta
	basics.learning_rate = learning_rate
	basics.iteration = iteration
	basics.max_iteration = max_iteration
	basics.abort = abort
	
	# generate_basis for fitness
	generate_basis()
	calculate_basis()
	
	size = len(shape_keys)-1
	
	#while iteration < maxiteration:
	for i in range(max_iteration):
		# update frame
		frame += 1
		
		# be aware of list order from jobs!
		# if a function is adding jobs,
		# the jobs are added when the function is called
		# therefore a function added afterwards, but added
		# directly, will be executed before the jobs added
		# from the functions
		
		# make step
		basics.jobs.append([make_step_st, frame])
		calculate_step_st(frame)
		basics.jobs.append([get_step_st, frame])
		
		# create variations for next step
		basics.jobs.append([create_variations, frame])
		make_step_mp([frame+1, frame+size+1])
		basics.jobs.append([get_next_step, [frame, frame+size]])
		
		frame += size
	
	bpy.context.scene.frame_end = frame
	
	# geometry post and viz
	basics.jobs.append([finish])
	
	# run jobs
	bpy.ops.wm.phaenotyp_jobs()
