import bpy
import bmesh
import random
from phaenotyp import basics, geometry, calculation

def create_indivdual(chromosome, parent_1, parent_2):
	"""
	Creates an individual for bruteforce mode.
	:param chromosome: The chromosome is a list of floats from 0 to 1.
	:parent_1: The first parent as class instance individual.
	:parent_2: The second parent as class instance individual.
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
	geometry.set_shape_keys(shape_keys, chromosome)

	individual = {}
	individual["name"] = str(frame) # individuals are identified by frame
	individual["chromosome"] = chromosome

	individual["parent_1"] = str(parent_1)
	individual["parent_2"] = str(parent_2)
	individual["fitness"] = {}

	individuals[str(frame)] = individual

def generate_basis():
	"""
	Creates the basis individual for the genetic algorithm.
	This individual is used to calculate the weighted fitness of all others.
	"""
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]

	# create chromosome all set to 0
	chromosome = []
	for gnome_len in range(len(shape_keys)-1): # -1 to exlude basis
		gene = 0
		chromosome.append(gene)

	# update scene
	bpy.context.scene.frame_current = 0
	bpy.context.view_layer.update()

	create_indivdual(chromosome, None, None) # and change frame to shape key
	
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

def mate_chromosomes(chromosome_1, chromosome_2):
	'''
	Function to mate chromosomes.
	:param chromosom_1: First chromosome for mating as list of floats.
	:param chromosom_2: Second chromosome for mating as list of floats.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	environment = data["environment"]
	individuals = data["individuals"]

	if phaenotyp.mate_type == "direct":
		# chromosome for offspring
		child_chromosome = []
		for gp1, gp2 in zip(chromosome_1, chromosome_2):

			# random probability
			prob = random.random()

			# if prob is less than 0.45, insert gene from parent 1
			if prob < 0.45:
				child_chromosome.append(gp1)

			# if prob is between 0.45 and 0.90, insert gene from parent 2
			elif prob < 0.90:
				child_chromosome.append(gp2)

			# otherwise insert random gene(mutate) to maintain diversity
			else:
				child_chromosome.append(random.choice(environment["genes"]))

	if phaenotyp.mate_type == "morph":
		# chromosome for offspring
		child_chromosome = []
		for gp1, gp2 in zip(chromosome_1, chromosome_2):

			# random probability
			prob = random.random()

			# if prob is less than 0.9, morph genes from parents
			if prob < 0.90:
				morph = (gp1 + gp2)*0.5
				child_chromosome.append(morph)

			# otherwise insert random gene(mutate) to maintain diversity
			else:
				child_chromosome.append(random.choice(environment["genes"]))

	return child_chromosome

def create_initial_individuals(frames):
	'''
	Create random individuals of the first generation.
	Every frame is for one individual only.
	:param start: Frame to start at.
	:param end: Frame to end with.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]
	
	start, end = frames
	
	# calculate all frames
	for frame in range(start, end):
		# create chromosome with set of shapekeys (random for first generation)
		new_chromosome_found = False
		for i in range(100): # run for max 100 times, if no new chromosome is found
			# create new chromosome
			chromosome = []
			for gnome_len in range(len(shape_keys)-1): # -1 to exlude basis
				gene = random.choice(environment["genes"])
				chromosome.append(gene)
			
			# check if existing
			for id, individual in individuals.items():
				if individual["chromosome"].to_list() == chromosome:
					if i < 100:
						text = "chromosome" + str(chromosome) + " allready exists. I try again ..."
						basics.print_data(text)
					else:
						basics.print_data("No new chromosome after retrying for 100 times. Maybe you want to run bruteforce?")
						
					new_chromosome_found = False
					break
					
				else:
					new_chromosome_found = True
			
			# break if a new chromosome was found
			if new_chromosome_found == True:
				# exit, because a new key was found
				text = "new individual with chromosome" + str(chromosome)
				basics.print_data(text)
				break

		# update scene
		bpy.context.scene.frame_current = frame
		bpy.context.view_layer.update()

		create_indivdual(chromosome, None, None) # and change frame to shape key

def calculate_individuals(frames):
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

def populate_initial_generation():
	'''
	Populate the first generation.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]

	 # create initial generation
	environment["generations"]["0"] = {} # create dict
	initial_generation = environment["generations"]["0"]

	# copy to generation
	for name, individual in individuals.items():
		# get data from individual
		chromosome = individual["chromosome"]
		fitness = individual["fitness"]
		parent_1 = individual["parent_1"]
		parent_2 = individual["parent_2"]

		# copy individual to next generation
		individual_copy = {}
		individual_copy["name"] = name
		individual_copy["chromosome"] = chromosome
		individual_copy["fitness"] = fitness
		individual_copy["parent_1"] = parent_1
		individual_copy["parent_2"] = parent_2

		initial_generation[name] = individual_copy

		# get text from chromosome for printing
		str_chromosome = "["
		for gene in individual["chromosome"]:
			str_chromosome += str(round(gene, 3))
			str_chromosome += ", "
		str_chromosome = str_chromosome[:-2]
		str_chromosome += "]"

		# print info
		text = "individual: " + str(individual["name"]) + " "
		text += str_chromosome + ", fitness: " + str(individual["fitness"]["weighted"])
		basics.print_data(text)

def do_elitism():
	'''
	Copy the best individuals to the next generation directly.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]
	generation_id = data["environment"]["generation_id"]

	# the current generation
	current_generation = environment["generations"][str(generation_id)]

	# sort current generation according to fitness
	list_result = []
	for name, individual in current_generation.items():
		list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

	sorted_list = sorted(list_result, key = lambda x: x[2])

	# the next generation
	generation_id = generation_id + 1 # increase id
	data["environment"]["generation_id"] = generation_id # += would not working

	environment["generations"][str(generation_id)] = {} # create dict
	next_generation = environment["generations"][str(generation_id)]

	# copy fittest ten percent directly
	for i in range(environment["elitism"]):
		# name of nth best individual
		name = sorted_list[i][0]

		# get individual
		individual = individuals[name]

		# get data from individual
		chromosome = individual["chromosome"]
		fitness = individual["fitness"]
		parent_1 = individual["parent_1"]
		parent_2 = individual["parent_2"]

		# copy individual to next generation
		individual_copy = {}
		individual_copy["name"] = name
		individual_copy["chromosome"] = chromosome
		individual_copy["fitness"] = fitness
		individual_copy["parent_1"] = parent_1
		individual_copy["parent_2"] = parent_2

		next_generation[name] = individual_copy

		# get text from chromosome for printing
		str_chromosome = "["
		for gene in individual["chromosome"]:
			str_chromosome += str(round(gene, 3))
			str_chromosome += ", "
		str_chromosome = str_chromosome[:-2]
		str_chromosome += "]"

		# print info
		text = "elitism: " + str(individual["name"]) + " "
		text += str_chromosome + ", fitness: " + str(individual["fitness"]["weighted"])
		basics.print_data(text)

def create_new_individuals(frames):
	'''
	Create new individuals for all generations except of generation 1.
	:param start: Frame to start at.
	:param end: Frame to end with.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]
		
	environment = data["environment"]
	individuals = data["individuals"]

	new_generation_size = environment["new_generation_size"]
	generation_id = environment["generation_id"]

	old_generation = environment["generations"][str(generation_id-1)]
	
	start, end = frames
	
	# sort current generation according to fitness
	list_result = []
	for name, individual in old_generation.items():
		list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

	sorted_list = sorted(list_result, key = lambda x: x[2])

	for frame in range(start, end):
		# create chromosome from two parents
		new_chromosome_found = False
		for i in range(100): # run for max 100 times, if no new chromosome is found
			# create new chromosome
			# pair best 50 % of the previous generation
			# sample is used to avoid same random numbers
			random_numbers = random.sample(range(int(new_generation_size*0.5)), 2)
			parent_1_name = sorted_list[random_numbers[0]][0]
			parent_2_name = sorted_list[random_numbers[1]][0]

			parent_1 = individuals[parent_1_name]
			parent_2 = individuals[parent_2_name]

			chromosome = mate_chromosomes(parent_1["chromosome"], parent_2["chromosome"])
			
			# check if existing
			for id, individual in individuals.items():
				if individual["chromosome"].to_list() == chromosome:
					if i < 100:
						text = "chromosome" + str(chromosome) + " allready exists. I try again ..."
						basics.print_data(text)
					else:
						basics.print_data("No new chromosome after retrying for 100 times. Maybe you want to run bruteforce?")
						
					new_chromosome_found = False
					break
					
				else:
					new_chromosome_found = True
			
			# break if a new chromosome was found
			if new_chromosome_found == True:
				# exit, because a new key was found
				text = "new individual with chromosome" + str(chromosome)
				basics.print_data(text)
				break
		
		# update scene
		bpy.context.scene.frame_current = frame
		bpy.context.view_layer.update()

		# and change frame to shape key - save name of parents for tree
		create_indivdual(chromosome, parent_1_name, parent_2_name)

def populate_new_generation(frames):
	'''
	Populate all generations that except of generation 1.
	'''
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]

	new_generation_size = environment["new_generation_size"]
	generation_id = environment["generation_id"]

	# the current generation, that was created in do_elitism
	generation = environment["generations"][str(generation_id)]
	
	start, end = frames
	
	# copy to generations
	for name, individual in individuals.items():
		for frame in range(start, end):
			# get from individuals
			if str(frame) == name:
				# get individual
				individual = individuals[name]

				# get data from individual
				chromosome = individual["chromosome"]
				fitness = individual["fitness"]
				parent_1 = individual["parent_1"]
				parent_2 = individual["parent_2"]

				# copy individual to next generation
				individual_copy = {}
				individual_copy["name"] = name
				individual_copy["chromosome"] = chromosome
				individual_copy["fitness"] = fitness
				individual_copy["parent_1"] = parent_1
				individual_copy["parent_2"] = parent_2

				generation[name] = individual_copy

				# get text from chromosome for printing
				str_chromosome = "["
				for gene in individual["chromosome"]:
					str_chromosome += str(round(gene, 3))
					str_chromosome += ", "
				str_chromosome = str_chromosome[:-2]
				str_chromosome += "]"

				# print info
				text = "child: " + str(individual["name"]) + " "
				text += str_chromosome + ", fitness: " + str(individual["fitness"]["weighted"])
				basics.print_data(text)

def finish():
	# update view
	basics.jobs.append([basics.view_vertex_colors])
	
	# print done
	basics.jobs.append([basics.print_data, "done"])
	
def start():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	
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

	# create temp dictionaries
	basics.models = {}
	basics.feas = {}

	# generate an individual as basis at frame 0
	# this individual has choromosome with all genes equals 0
	# the fitness of this chromosome is the basis for all others
	generate_basis()
	calculate_basis()
	
	start = 1
	end = generation_size
	
	# set frame_end to first size of inital generation
	bpy.context.scene.frame_end = end
	
	# create initial generation
	# the first generation contains 20 individuals (standard value is 20)
	# the indiviuals are created with random genes
	# there is no elitism possible, because there is no previous group
	basics.jobs.append([create_initial_individuals, [start, end]])
	calculate_individuals([start, end])
	basics.jobs.append([populate_initial_generation])

	# create all other generations
	# 2 indiviuals are taken from previous group (standard value is 10)
	# 10 indiviuals are paired (standard ist 50 %)
	for i in range(generation_amount):
		start = end
		end = start + new_generation_size

		# expand frame
		bpy.context.scene.frame_end = end

		# create new generation and copy fittest percent
		basics.jobs.append([do_elitism])
		
		basics.jobs.append([create_new_individuals, [start, end]])
		calculate_individuals([start, end])
		basics.jobs.append([populate_new_generation, [start, end]])
	
	# geometry post and viz
	basics.jobs.append([finish])
	
	# run jobs
	bpy.ops.wm.phaenotyp_jobs()
