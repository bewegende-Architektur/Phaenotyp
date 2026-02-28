import bpy
from phaenotyp import basics, operators, geometry, calculation
import numpy as np

# this module is only available if lab_usage is true in basics.py
# it allows to use bayesian optimization for shape key optimization
# however, it requires external libaries to be installed via pip
# this is suggested for experienced users only

def add_sitepackages():
	# Fügt sitepackages zu Python hinzu
	import sys
	import site
	user_site = site.getusersitepackages()
	if user_site not in sys.path:
		sys.path.insert(0, user_site)
	
	try:
		from bayes_opt import BayesianOptimization
		import matplotlib.pyplot as plt
		basics.external_libs_loaded = True
		
	except Exception:
		basics.external_libs_loaded = False
		basics.log_exception("bayesian libs import failed")

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
	subprocess.call([python_exe, "-m", "pip", "install", "matplot"])
	
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
	
	chromosome = []
	for i in range(len(basics.chromosome_current)):
		v = next_point_to_probe[str(i)]
		chromosome.append(v)

	basics.chromosome_current = chromosome
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

def draw_line_png(optimizer):
	import matplotlib.pyplot as plt
	import os
	import numpy as np
	import bpy

	frame = bpy.context.scene.frame_current
	frame_str = f"{frame:03d}"
	base_dir = bpy.path.abspath("//")
	frames_dir = os.path.join(base_dir, "bm_frames")
	os.makedirs(frames_dir, exist_ok=True)
	out_path = os.path.join(frames_dir, f"line_{frame_str}.png")

	n_px = 400
	dim_x = 0
	fixed_value = 0.5

	# Unsicherheitsband, ca. 95% bei Normalverteilung
	sigma_factor = 1.96

	# params als Array holen
	params = optimizer.space.params
	first = params[0]

	if isinstance(first, dict):
		keys = list(getattr(optimizer.space, "keys", [])) or list(first.keys())
		X = np.array([[p[k] for k in keys] for p in params], dtype=float)
	else:
		X = np.array(params, dtype=float)

	y = np.array(optimizer.space.target, dtype=float)

	# GP fitten
	optimizer._gp.fit(X, y)
	n_dims = optimizer._gp.n_features_in_

	# 1D Grid aufbauen
	x_lin = np.linspace(0.0, 1.0, n_px)

	# Query-Matrix in richtiger Dimensionalität
	Xq = np.full((n_px, n_dims), float(fixed_value), dtype=float)
	Xq[:, dim_x] = x_lin

	# Predict: mean + std
	mu, sigma = optimizer._gp.predict(Xq, return_std=True)

	# Plot
	dpi = 100
	fig = plt.figure(figsize=(n_px / dpi, n_px / dpi), dpi=dpi)
	ax = fig.add_axes([0.15, 0.15, 0.80, 0.80])

	# Unsicherheitsband
	ax.fill_between(
		x_lin,
		mu - sigma_factor * sigma,
		mu + sigma_factor * sigma,
		alpha=0.25,
		label=f"mu ± {sigma_factor:.2f}·sigma"
	)

	# Mean-Linie
	ax.plot(
		x_lin,
		mu,
		linewidth=2.0,
		label="mu"
	)

	# Samples als Punkte (projiziert auf dim_x)
	ax.scatter(
		X[:, dim_x],
		y,
		s=30,
		c="black",
		edgecolors="black",
		linewidths=0.8,
		label="Samples"
	)

	# aktueller (letzter) Punkt
	ax.scatter(
		X[-1, dim_x],
		y[-1],
		s=120,
		c="white",
		edgecolors="black",
		linewidths=2.0,
		zorder=10,
		label="aktueller Punkt"
	)

	ax.set_xlim(0.0, 1.0)

	ax.set_axis_on()
	ax.set_xlabel("shapekey 1")
	ax.set_ylabel("fitness")
	ax.tick_params(axis="both", labelsize=6)
	ax.grid(True, linewidth=0.3, alpha=0.7)
	ax.legend(loc="best", fontsize=6, framealpha=0.9)

	fig.savefig(out_path, dpi=dpi)
	plt.close(fig)

def draw_field_png(optimizer):
	import matplotlib.pyplot as plt
	import os

	frame = bpy.context.scene.frame_current
	frame_str = f"{frame:03d}"
	base_dir = bpy.path.abspath("//")
	frames_dir = os.path.join(base_dir, "bm_frames")
	os.makedirs(frames_dir, exist_ok=True)
	out_path = os.path.join(frames_dir, f"field_{frame_str}.png")
	n_px = 400
	dim_x = 0
	dim_y = 1
	fixed_value = 0.5

	# params als Array holen
	params = optimizer.space.params
	first = params[0]

	if isinstance(first, dict):
		# falls dict: feste Reihenfolge über optimizer.space.keys (wenn vorhanden)
		keys = list(getattr(optimizer.space, "keys", [])) or list(first.keys())
		X = np.array([[p[k] for k in keys] for p in params], dtype=float)
	else:
		X = np.array(params, dtype=float)

	y = np.array(optimizer.space.target, dtype=float)

	# GP fitten
	optimizer._gp.fit(X, y)

	# Dimensionen wie vom GP erwartet
	n_dims = optimizer._gp.n_features_in_

	# Grid aufbauen
	x_lin = np.linspace(0.0, 1.0, n_px)
	y_lin = np.linspace(0.0, 1.0, n_px)
	Xg, Yg = np.meshgrid(x_lin, y_lin, indexing="xy")

	# Query-Matrix in richtiger Dimensionalität
	Xq = np.full((n_px * n_px, n_dims), float(fixed_value), dtype=float)
	Xq[:, dim_x] = Xg.ravel()
	Xq[:, dim_y] = Yg.ravel()

	# Predict: nur Erwartungswert
	mu = optimizer._gp.predict(Xq, return_std=False)
	mu = mu.reshape(n_px, n_px)

	# Render exakt n_px x n_px
	dpi = 100
	fig = plt.figure(figsize=(n_px / dpi, n_px / dpi), dpi=dpi)
	#ax = fig.add_axes([0, 0, 1, 1])
	ax = fig.add_axes([0.15, 0.15, 0.80, 0.80])

	ax.imshow(
		mu,
		origin="lower",
		extent=(0.0, 1.0, 0.0, 1.0),
		cmap="coolwarm",
		interpolation="nearest"
	)

	# alle vorhandenen Punkte einzeichnen (2D-Projektion)
	ax.scatter(X[:, dim_x], X[:, dim_y], s=30, 	c="black", edgecolors="black", linewidths=0.8)
	
	# aktueller (letzter) Punkt
	ax.scatter(X[-1, dim_x], X[-1, dim_y], s=120, c="white", edgecolors="black", linewidths=2.0, zorder=10)

	ax.set_xlim(0.0, 1.0)
	ax.set_ylim(0.0, 1.0)
	
	ax.set_axis_on()
	ax.set_xlabel("shapekey 1")
	ax.set_ylabel("shapekey 2")
	ax.tick_params(axis="both", labelsize=6)
	ax.grid(True, linewidth=0.3, alpha=0.7)
	
	fig.savefig(out_path, dpi=dpi)
	plt.close(fig)

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
	
	add_sitepackages()

	# kappa als Parameter in Phänotyp
	from bayes_opt import acquisition
	from bayes_opt import BayesianOptimization
	
	iterations = phaenotyp.bm_iterations
	factor = phaenotyp.bm_factor
	kappa = 0.5 + 9.5 * (factor / 100.0) ** 2
	xi = 0.1 * 2 * (factor/100)**2   
	
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
	
	# pbouds erstellen
	pbounds = {}
	chromosome = []
	for i in range(len(shape_keys)):
		pbounds[str(i)] = (0,1)
		chromosome.append(0)
		
	# Bounds sind immer von 0 bis 1
	# verbose und random_state als Paramter in Phäntoyp
	optimizer = BayesianOptimization(
	    f=None,
	    acquisition_function=acq,
		pbounds=pbounds,
	    verbose=2,
	    random_state=1,
	)

	# erster Frame
	frame = 0
	basics.models = {}
	basics.feas = {}
	basics.target = None
	basics.fitness = None
	basics.chromosome_current = chromosome
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
	for i in range(iterations):
		# nächsten Frames
		frame = frame + 1

		basics.jobs.append([suggest_next, optimizer])
		basics.jobs.append([create_from_current, frame])
		basics.jobs.append([make_step_st, frame])
		calculate_step_st(frame)
		basics.jobs.append([get_target_st, frame])
		basics.jobs.append([register_target, optimizer])
		
		# Zeichnet Liniendiagramm, für einen Shapekey + Basis
		if len(shape_keys) == 2:
			basics.jobs.append([draw_line_png, optimizer])
			
		# Zeichnet Feld, bei zwei Shapekeys + Basis
		if len(shape_keys) == 3:
			basics.jobs.append([draw_field_png, optimizer])

	basics.jobs.append([print_result, optimizer])
	
	bpy.context.scene.frame_end = frame
	
	# geometry post and viz
	basics.jobs.append([finish])

	# run jobs
	bpy.ops.wm.phaenotyp_jobs()
