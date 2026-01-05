import bpy
from phaenotyp import basics, operators, geometry, calculation
import numpy as np

def add_sitepackages():
	# Fügt sitepackages zu Python hinzu
	import sys
	import site
	user_site = site.getusersitepackages()
	if user_site not in sys.path:
		sys.path.insert(0, user_site)
	
	try:
		from bayes_opt import BayesianOptimization
		basics.external_libs_loaded = True
		
	except:
		basics.external_libs_loaded = False
	
add_sitepackages()

def install_bayes():
	# like suggested from Harry McKenzie here:
	# https://blender.stackexchange.com/questions/56011/how-to-install-pip-for-blenders-bundled-python-and-use-it-to-install-packages

	import subprocess
	import sys
	import os

	# path to python
	python_exe = sys.executable

	# upgrade pip
	subprocess.call([python_exe, "-m", "ensurepip"])
	subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])

	# install required packages
	subprocess.call([python_exe, "-m", "pip", "install", "bayesian-optimization"])
	
	add_sitepackages()

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

def get_target_st(frame):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]

	# get data from individual
	target = individuals[str(frame)]
	fitness = target["fitness"]["weighted"]

	text = "Target " + target["name"] + " with fitness: " + str(round(fitness, 3))
	basics.print_data(text)

	basics.target = target
	basics.fitness = fitness

def create_from_current(frame):
	create_indivdual(basics.chromosome_current, frame)

def suggest_next(optimizer):
	# Wird ersten Punkt random wählen
	# Sollte das später calculate_basis sein?
	next_point_to_probe = optimizer.suggest()
	print("Next point to probe is:", next_point_to_probe)

	#target = black_box_function(**next_point_to_probe)
	a = next_point_to_probe["a"]
	b = next_point_to_probe["b"]
	c = next_point_to_probe["c"]

	basics.chromosome_current = [a,b,c]
	basics.next_point_to_probe = next_point_to_probe

	chromosome = basics.chromosome_current

def register_target(optimizer):
	target = basics.target
	fitness = basics.fitness*(-1) # Invertieren, um zu optimieren
	next_point_to_probe = basics.next_point_to_probe

	print("Found the target", target, "with fitness", fitness)

	optimizer.register(
		params=next_point_to_probe,
		target=fitness,
	)

def print_result(optimizer):
	print("result:")
	for i, res in enumerate(optimizer.res):
		print("Iteration {}: \n\t{}".format(i, res))

	print("best:")
	print(optimizer.max)

def finish():
	# update view
	basics.jobs.append([basics.view_vertex_colors])

	# print done
	basics.jobs.append([basics.print_data, "done"])

def start():
	'''
	Main function to run bayesian modeling.
	'''
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	phaenotyp = scene.phaenotyp

	environment = data["environment"]
	individuals = data["individuals"]

	# Variablen erstellen
	"""
	amount = Anzahl der Iterationen
	function = Vorbereitete Funktionen
	"""

	# todo
	"""
	Variablen einfügen, ok
	Installer für pip bauen -> Variablen, ok
	abc -> automatisch
	Frames anpassen nach Ende
	Diagramm lösen -> D klein d bei Materialname
	Version 4 -> Weil zu viel neue Variablen
	mathplot installieren -> Bilder erzeugen
	was war Konflikt mit numpy?
	"""
	
	add_sitepackages()

	# kappa als Parameter in Phänotyp
	from bayes_opt import acquisition
	from bayes_opt import BayesianOptimization
	
	factor = phaenotyp.bm_factor	
	kappa = 0.5 + 9.5 * (factor / 100.0) ** 2
	xi = xi = 0.01 * (factor / 100.0) ** 2
	
	acq_type = phaenotyp.bm_acq
	
	if acq_type == "UpperConfidenceBound":
		acq = acquisition.UpperConfidenceBound(kappa=kappa)
	
	if acq_type == "ProbabilityOfImprovement":
		acq = acquisition.ProbabilityOfImprovement(xi=xi)
	
	if acq_type == "ExpectedImprovement":
		acq = acquisition.ExpectedImprovement(xi=xi)
	
	if acq_type == "ConstantLiar":
		acq = acquisition.ConstantLiar(
			base_acquisition=acquisition.ExpectedImprovement(xi=xi),
			strategy="mean"
		)

	# Bounds sind immer von 0 bis 1
	# verbose und random_state als Paramter in Phäntyp
	optimizer = BayesianOptimization(
	    f=None,
	    acquisition_function=acq,
		pbounds={'a': (0, 1), 'b': (0, 1), 'c': (0, 1)},
	    verbose=2,
	    random_state=1,
	)

	# erster Frame
	frame = 0
	basics.models = {}
	basics.feas = {}
	basics.target = None
	basics.fitness = None
	basics.chromosome_current = [0,0,0]
	basics.next_point_to_probe = None

	# generate_basis for fitness
	generate_basis()
	calculate_basis()

	# zweiter Frame
	frame = 1

	basics.jobs.append([suggest_next, optimizer])
	basics.jobs.append([create_from_current, frame])
	basics.jobs.append([make_step_st, frame])
	calculate_step_st(frame)
	basics.jobs.append([get_target_st, frame])
	basics.jobs.append([register_target, optimizer])

	# ist loop von jobs
	for _ in range(5):
		# nächsten Frames
		frame = frame + 1

		basics.jobs.append([suggest_next, optimizer])
		basics.jobs.append([create_from_current, frame])
		basics.jobs.append([make_step_st, frame])
		calculate_step_st(frame)
		basics.jobs.append([get_target_st, frame])
		basics.jobs.append([register_target, optimizer])

	basics.jobs.append([print_result, optimizer])

	# geometry post and viz
	basics.jobs.append([finish])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()
