import bpy
import bmesh
import random
from phaenotyp import basics, geometry, calculation, progress
import itertools

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
	
	# update frame
	bpy.context.scene.frame_start = 0
	bpy.context.scene.frame_current = 0
	bpy.context.view_layer.update()
	
	# create chromosome all set to 0
	chromosome = []
	for gnome_len in range(len(shape_keys)-1): # -1 to exlude basis
		gene = 0
		chromosome.append(gene)

	# update scene
	create_indivdual(chromosome, 0) # and change frame to shape key

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
	
	#progress.http.reset_pci(1)

def generate_others():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]

	data["environment"]["genes"] = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
	individuals = data["individuals"]
	
	# create others
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
	#progress.http.reset_pci(end-start)
	#progress.http.reset_o(optimization_amount)

	# pair with bruteforce
	#bruteforce(chromosomes)
	for i, chromosome in enumerate(chromosomes):
		# update scene
		frame = i+1  # exclude basis indivual
		create_indivdual(chromosome, frame) # and change frame to shape key
		
	basics.chromosomes = chromosomes

def calculate_others():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]

	data["environment"]["genes"] = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
	individuals = data["individuals"]
	
	# create start and end of calculation and create individuals
	start = 1 # basis indiviual is allready created and optimized
	end = len(basics.chromosomes)+1
	
	# if optimizaiton
	if phaenotyp.optimization_pn != "none" or phaenotyp.optimization_fd != "none" or phaenotyp.optimization_quads != "none":
		# calculate frames
		calculation.calculate_frames(start, end)
	
		for i in range(phaenotyp.optimization_amount):
			# optimize each frame
			for frame in range(start, end):
				basics.jobs.append([calculation.sectional_optimization, frame])
				
			# calculate frames again
			calculation.calculate_frames(start, end)
	
	# without optimization
	else:
		# calculate frames
		calculation.calculate_frames(start, end)
	
	# calculate fitness and set weight for basis
	for frame in range(start, end):
		basics.jobs.append([calculation.calculate_fitness, frame])
	
	basics.jobs.append([basics.print_data, "others calculated"])

def finish():
	# update view
	basics.jobs.append([basics.view_vertex_colors])
	
	# print done
	basics.jobs.append([basics.print_data, "done"])

	# calculate new visualization-mesh
	basics.jobs.append([geometry.update_geometry_post])

def start():
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]

	basics.print_data("Start bruteforce over selected shape keys")

	data["environment"]["genes"] = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
	data["individuals"] = {}
	individuals = data["individuals"]

	# create temp dictionaries
	basics.models = {}
	basics.feas = {}
	basics.chromosomes = []
	
	# start progress
	#progress.run()
	#progress.http.reset_pci(1)
	#progress.http.reset_o(optimization_amount)

	# generate an individual as basis at frame 0
	# this individual has choromosome with all genes equals 0
	# the fitness of this chromosome is the basis for all others
	generate_basis() # to be calculated later
	generate_others() # to be calculated later
	
	# calculate frames
	calculate_basis()
	calculate_others()
	
	# finish
	finish()
	
	# run jobs
	bpy.ops.wm.phaenotyp_jobs()
