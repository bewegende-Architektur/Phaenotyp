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
	
	basics.check_external_libs()

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
	subprocess.call([python_exe, "-m", "pip", "install", "matplotlib"])
	
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
	params = {}
	slope = []
	for i, key in enumerate(shape_keys[1:]):
		v = key.value
		chromosome.append(v)
		params[str(i)] = v
		slope.append(0)

	# create indiviual
	create_indivdual(chromosome, 0)

	rounded_chromosome = [round(num, 3) for num in chromosome]
	text = "Starting at: " + str(rounded_chromosome) + "\n"
	basics.print_data(text)

	# store in basics for later
	basics.chromosome_current = chromosome
	basics.slope = slope
	return params

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
	if len(optimizer.space.target) == 0:
		scene = bpy.context.scene
		data = scene["<Phaenotyp>"]
		individuals = data["individuals"]
		basis = individuals["0"]
		basis_params = {str(i): value for i, value in enumerate(basis["chromosome"])}
		basis_fitness = basis["fitness"]["weighted"] * (-1)
		optimizer.register(
			params=basis_params,
			target=basis_fitness,
		)

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

	if next_point_to_probe is None:
		return

	next_point_to_probe = {str(key): value for key, value in next_point_to_probe.items()}

	keys = list(next_point_to_probe.keys())
	for params in optimizer.space.params:
		if isinstance(params, dict):
			is_duplicate = all(np.isclose(params[key], next_point_to_probe[key]) for key in keys)
		else:
			is_duplicate = all(np.isclose(params[i], next_point_to_probe[str(i)]) for i in range(len(keys)))

		if is_duplicate:
			return

	print("Found the target", target, "with fitness", fitness)

	optimizer.register(
		params=next_point_to_probe,
		target=fitness,
	)

def get_bm_frames_dir():
	import os

	base_dir = bpy.path.abspath("//")
	frames_dir = os.path.join(base_dir, "bm_frames")
	os.makedirs(frames_dir, exist_ok=True)
	return frames_dir

def get_optimizer_samples(optimizer):
	params = list(optimizer.space.params)
	y_raw = np.array(optimizer.space.target, dtype=float)

	if len(params) == 0:
		return {
			"keys": [],
			"X_raw": np.empty((0, 0), dtype=float),
			"y_raw": y_raw,
			"X": np.empty((0, 0), dtype=float),
			"y": y_raw,
			"diagnostics": {
				"sample_count": 0,
				"unique_sample_count": 0,
				"duplicate_count": 0,
				"target_min": None,
				"target_max": None,
				"target_std": None,
				"targets_nearly_constant": False,
				"minimum_samples": 2,
			},
		}

	first = params[0]

	if isinstance(first, dict):
		keys = list(getattr(optimizer.space, "keys", [])) or list(first.keys())
		X_raw = np.array([[p[str(k)] for k in keys] for p in params], dtype=float)
	else:
		keys = [str(i) for i in range(len(first))]
		X_raw = np.array(params, dtype=float)

	if len(X_raw) > 0:
		X_rounded = np.round(X_raw, 8)
		_, unique_index, inverse = np.unique(
			X_rounded,
			axis=0,
			return_index=True,
			return_inverse=True,
		)
		unique_order = np.argsort(unique_index)
		X = np.array([X_raw[unique_index[i]] for i in unique_order], dtype=float)
		y = np.array([np.mean(y_raw[inverse == i]) for i in unique_order], dtype=float)
	else:
		X = X_raw
		y = y_raw

	target_min = float(np.min(y_raw)) if len(y_raw) > 0 else None
	target_max = float(np.max(y_raw)) if len(y_raw) > 0 else None
	target_std = float(np.std(y_raw)) if len(y_raw) > 0 else None
	target_span = float(np.ptp(y_raw)) if len(y_raw) > 0 else None
	minimum_samples = max(2, X.shape[1] + 1) if X.ndim == 2 and X.shape[1] > 0 else 2

	return {
		"keys": keys,
		"X_raw": X_raw,
		"y_raw": y_raw,
		"X": X,
		"y": y,
		"diagnostics": {
			"sample_count": int(len(y_raw)),
			"unique_sample_count": int(len(y)),
			"duplicate_count": int(len(y_raw) - len(y)),
			"target_min": target_min,
			"target_max": target_max,
			"target_std": target_std,
			"targets_nearly_constant": bool(
				len(y_raw) > 1 and target_span is not None and target_std is not None
				and target_span <= 1e-4 and target_std <= 1e-4
			),
			"minimum_samples": int(minimum_samples),
		},
	}

def get_visualization_gp(optimizer, X, y):
	import copy

	if len(y) == 0:
		return None, "No samples available."

	gp = copy.deepcopy(optimizer._gp)
	gp.optimizer = None

	alpha = getattr(gp, "alpha", 1e-6)
	if np.isscalar(alpha):
		gp.alpha = max(float(alpha), 1e-6)
	else:
		gp.alpha = np.maximum(np.asarray(alpha, dtype=float), 1e-6)

	try:
		gp.fit(X, y)
	except Exception as error:
		return None, str(error)

	return gp, None

def get_line_prediction(optimizer, n_px=400, dim_x=0, fixed_value=0.5):
	samples = get_optimizer_samples(optimizer)
	keys = samples["keys"]
	X = samples["X"]
	y = samples["y"]
	diagnostics = dict(samples["diagnostics"])
	X_raw = samples["X_raw"]
	y_raw = samples["y_raw"]

	result = {
		"ok": False,
		"message": "",
		"keys": keys,
		"X": X,
		"y": y,
		"X_raw": X_raw,
		"y_raw": y_raw,
		"x_lin": None,
		"mu": None,
		"sigma": None,
		"opt_x": None,
		"opt_mu": None,
		"diagnostics": diagnostics,
	}

	if len(X.shape) != 2 or X.shape[1] == 0:
		result["message"] = "No optimizer dimensions available for line prediction."
		return result

	if dim_x >= X.shape[1]:
		result["message"] = "Requested line dimension is out of range."
		return result

	if diagnostics["unique_sample_count"] < diagnostics["minimum_samples"]:
		result["message"] = f"Need at least {diagnostics['minimum_samples']} unique samples for line prediction."
		return result

	gp, error = get_visualization_gp(optimizer, X, y)
	if error is not None:
		result["message"] = f"Visualization GP fit failed: {error}"
		return result

	n_dims = gp.n_features_in_

	x_lin = np.linspace(0.0, 1.0, n_px)
	Xq = np.full((n_px, n_dims), float(fixed_value), dtype=float)
	Xq[:, dim_x] = x_lin

	mu, sigma = gp.predict(Xq, return_std=True)
	opt_idx = int(np.argmax(mu))
	diagnostics["posterior_mu_std"] = float(np.std(mu))
	diagnostics["posterior_sigma_mean"] = float(np.mean(sigma))
	diagnostics["posterior_sigma_max"] = float(np.max(sigma))
	diagnostics["posterior_nearly_constant"] = bool(np.ptp(mu) <= 1e-4 and np.std(mu) <= 1e-4)

	result.update({
		"ok": True,
		"x_lin": x_lin,
		"mu": mu,
		"sigma": sigma,
		"opt_x": float(x_lin[opt_idx]),
		"opt_mu": float(mu[opt_idx]),
	})
	return result

def get_field_prediction(optimizer, n_px=400, dim_x=0, dim_y=1, fixed_value=0.5):
	samples = get_optimizer_samples(optimizer)
	keys = samples["keys"]
	X = samples["X"]
	y = samples["y"]
	diagnostics = dict(samples["diagnostics"])
	X_raw = samples["X_raw"]
	y_raw = samples["y_raw"]

	result = {
		"ok": False,
		"message": "",
		"keys": keys,
		"X": X,
		"y": y,
		"X_raw": X_raw,
		"y_raw": y_raw,
		"x_lin": None,
		"y_lin": None,
		"mu": None,
		"sigma": None,
		"opt_x": None,
		"opt_y": None,
		"opt_mu": None,
		"diagnostics": diagnostics,
	}

	if len(X.shape) != 2 or X.shape[1] < 2:
		result["message"] = "At least two optimizer dimensions are required for field prediction."
		return result

	if dim_x >= X.shape[1] or dim_y >= X.shape[1]:
		result["message"] = "Requested field dimensions are out of range."
		return result

	if diagnostics["unique_sample_count"] < diagnostics["minimum_samples"]:
		result["message"] = f"Need at least {diagnostics['minimum_samples']} unique samples for field prediction."
		return result

	gp, error = get_visualization_gp(optimizer, X, y)
	if error is not None:
		result["message"] = f"Visualization GP fit failed: {error}"
		return result

	n_dims = gp.n_features_in_

	x_lin = np.linspace(0.0, 1.0, n_px)
	y_lin = np.linspace(0.0, 1.0, n_px)
	Xg, Yg = np.meshgrid(x_lin, y_lin, indexing="xy")

	Xq = np.full((n_px * n_px, n_dims), float(fixed_value), dtype=float)
	Xq[:, dim_x] = Xg.ravel()
	Xq[:, dim_y] = Yg.ravel()

	mu, sigma = gp.predict(Xq, return_std=True)
	mu = mu.reshape(n_px, n_px)
	sigma = sigma.reshape(n_px, n_px)
	opt_idx = np.unravel_index(int(np.argmax(mu)), mu.shape)
	diagnostics["posterior_mu_std"] = float(np.std(mu))
	diagnostics["posterior_sigma_mean"] = float(np.mean(sigma))
	diagnostics["posterior_sigma_max"] = float(np.max(sigma))
	diagnostics["posterior_nearly_constant"] = bool(np.ptp(mu) <= 1e-4 and np.std(mu) <= 1e-4)

	result.update({
		"ok": True,
		"x_lin": x_lin,
		"y_lin": y_lin,
		"mu": mu,
		"sigma": sigma,
		"opt_x": float(Xg[opt_idx]),
		"opt_y": float(Yg[opt_idx]),
		"opt_mu": float(mu[opt_idx]),
	})
	return result

def write_step_txt(optimizer):
	import os

	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	individuals = data["individuals"]
	frame_data = data["frames"]
	frame = scene.frame_current
	frame_str = f"{frame:03d}"
	frames_dir = get_bm_frames_dir()
	out_path = os.path.join(frames_dir, f"step_{frame_str}.txt")

	individual = individuals.get(str(frame), {})
	chromosome = individual.get("chromosome", [])
	fitness = individual.get("fitness", {})
	geometry_values = frame_data.get(str(frame), {})
	best = optimizer.max or {}
	best_target = best.get("target")
	best_params = best.get("params", {})

	lines = []
	lines.append(f"frame: {frame}")
	lines.append(f"chromosome: {chromosome}")

	if "weighted" in fitness:
		lines.append(f"current_weighted_fitness: {fitness['weighted']}")
		lines.append(f"current_optimizer_target: {-fitness['weighted']}")

	if best_target is not None:
		lines.append(f"best_optimizer_target: {best_target}")
		lines.append(f"best_weighted_fitness: {-best_target}")
		lines.append(f"best_params: {best_params}")

	if fitness:
		lines.append("")
		lines.append("fitness:")
		for key, value in fitness.items():
			lines.append(f"{key}: {value}")

	if geometry_values:
		lines.append("")
		lines.append("frame_values:")
		for key, value in geometry_values.items():
			lines.append(f"{key}: {value}")

	if len(chromosome) == 1 and len(optimizer.space.target) > 0:
		line_prediction = get_line_prediction(optimizer)
		lines.append("")
		lines.append("plot_diagnostics:")
		diagnostics = line_prediction["diagnostics"]
		lines.append(f"samples: {diagnostics['sample_count']}")
		lines.append(f"unique_samples: {diagnostics['unique_sample_count']}")
		lines.append(f"duplicate_points: {diagnostics['duplicate_count']}")
		lines.append(f"target_min: {diagnostics['target_min']}")
		lines.append(f"target_max: {diagnostics['target_max']}")
		lines.append(f"target_std: {diagnostics['target_std']}")
		lines.append(f"targets_nearly_constant: {diagnostics['targets_nearly_constant']}")
		if line_prediction["ok"]:
			lines.append(f"posterior_nearly_constant: {diagnostics['posterior_nearly_constant']}")
			lines.append(f"posterior_sigma_mean: {diagnostics['posterior_sigma_mean']}")
			lines.append(f"posterior_sigma_max: {diagnostics['posterior_sigma_max']}")
			lines.append("")
			lines.append("predicted_optimum_on_plot:")
			lines.append(f"shapekey_1: {line_prediction['opt_x']}")
			lines.append(f"optimizer_target_mu: {line_prediction['opt_mu']}")
			lines.append(f"weighted_fitness_mu: {-line_prediction['opt_mu']}")
		else:
			lines.append(f"plot_message: {line_prediction['message']}")

	if len(chromosome) >= 2 and len(optimizer.space.target) > 0:
		field_prediction = get_field_prediction(optimizer)
		lines.append("")
		lines.append("plot_diagnostics:")
		diagnostics = field_prediction["diagnostics"]
		lines.append(f"samples: {diagnostics['sample_count']}")
		lines.append(f"unique_samples: {diagnostics['unique_sample_count']}")
		lines.append(f"duplicate_points: {diagnostics['duplicate_count']}")
		lines.append(f"target_min: {diagnostics['target_min']}")
		lines.append(f"target_max: {diagnostics['target_max']}")
		lines.append(f"target_std: {diagnostics['target_std']}")
		lines.append(f"targets_nearly_constant: {diagnostics['targets_nearly_constant']}")
		if field_prediction["ok"]:
			lines.append(f"posterior_nearly_constant: {diagnostics['posterior_nearly_constant']}")
			lines.append(f"posterior_sigma_mean: {diagnostics['posterior_sigma_mean']}")
			lines.append(f"posterior_sigma_max: {diagnostics['posterior_sigma_max']}")
			lines.append("")
			lines.append("predicted_optimum_on_plot:")
			lines.append(f"shapekey_1: {field_prediction['opt_x']}")
			lines.append(f"shapekey_2: {field_prediction['opt_y']}")
			lines.append(f"optimizer_target_mu: {field_prediction['opt_mu']}")
			lines.append(f"weighted_fitness_mu: {-field_prediction['opt_mu']}")
		else:
			lines.append(f"plot_message: {field_prediction['message']}")

	with open(out_path, "w", encoding="utf-8") as file:
		file.write("\n".join(lines) + "\n")

def append_steps_csv(optimizer):
	import csv
	import os

	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	individuals = data["individuals"]
	frame = scene.frame_current
	frames_dir = get_bm_frames_dir()
	out_path = os.path.join(frames_dir, "steps.csv")

	individual = individuals.get(str(frame), {})
	chromosome = individual.get("chromosome", [])
	fitness = individual.get("fitness", {})
	best = optimizer.max or {}
	best_target = best.get("target")
	best_params = best.get("params", {})

	header = ["frame"]
	for i in range(len(chromosome)):
		header.append(f"shape_key_{i+1}")
	header.extend([
		"weighted_fitness",
		"optimizer_target",
		"best_optimizer_target",
		"best_weighted_fitness",
	])
	for i in range(len(chromosome)):
		header.append(f"best_shape_key_{i+1}")

	row = [frame]
	row.extend(chromosome)
	weighted_fitness = fitness.get("weighted")
	row.append(weighted_fitness)
	row.append(None if weighted_fitness is None else -weighted_fitness)
	row.append(best_target)
	row.append(None if best_target is None else -best_target)
	for i in range(len(chromosome)):
		row.append(best_params.get(str(i)))

	write_header = (frame == 1) or (not os.path.exists(out_path))
	mode = "w" if write_header else "a"

	with open(out_path, mode, newline="", encoding="utf-8") as file:
		writer = csv.writer(file)
		if write_header:
			writer.writerow(header)
		writer.writerow(row)

def draw_line_png(optimizer):
	import matplotlib.pyplot as plt
	import os
	import bpy

	frame = bpy.context.scene.frame_current
	frame_str = f"{frame:03d}"
	frames_dir = get_bm_frames_dir()
	out_path = os.path.join(frames_dir, f"line_{frame_str}.png")

	n_px = 400
	dim_x = 0
	fixed_value = 0.5

	# Unsicherheitsband, ca. 95% bei Normalverteilung
	sigma_factor = 1.96

	prediction = get_line_prediction(optimizer, n_px=n_px, dim_x=dim_x, fixed_value=fixed_value)
	X = prediction["X_raw"]
	y = prediction["y_raw"]
	x_lin = prediction["x_lin"]
	mu = prediction["mu"]
	sigma = prediction["sigma"]
	opt_x = prediction["opt_x"]
	opt_mu = prediction["opt_mu"]
	diagnostics = prediction["diagnostics"]

	# Plot
	dpi = 100
	fig = plt.figure(figsize=(n_px / dpi, n_px / dpi), dpi=dpi)
	ax = fig.add_axes([0.15, 0.15, 0.80, 0.80])

	if prediction["ok"]:
		ax.fill_between(
			x_lin,
			mu - sigma_factor * sigma,
			mu + sigma_factor * sigma,
			alpha=0.25,
			label=f"mu ± {sigma_factor:.2f}·sigma"
		)

		ax.plot(
			x_lin,
			mu,
			linewidth=2.0,
			label="mu"
		)
	else:
		ax.text(
			0.5,
			0.95,
			prediction["message"],
			ha="center",
			va="top",
			transform=ax.transAxes,
			fontsize=7,
			bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
		)

	# Samples als Punkte (projiziert auf dim_x)
	if len(X) > 0:
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
	if len(X) > 0:
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

	if prediction["ok"]:
		ax.scatter(
			opt_x,
			opt_mu,
			s=80,
			c="red",
			edgecolors="white",
			linewidths=0.8,
			zorder=11,
			label="Optimum mu"
		)

	ax.set_xlim(0.0, 1.0)

	ax.set_axis_on()
	ax.set_xlabel("shapekey 1")
	ax.set_ylabel("optimizer target")
	ax.tick_params(axis="both", labelsize=6)
	ax.grid(True, linewidth=0.3, alpha=0.7)
	title = f"n={diagnostics['sample_count']} unique={diagnostics['unique_sample_count']} dup={diagnostics['duplicate_count']}"
	if diagnostics["target_std"] is not None:
		title += f" y_std={diagnostics['target_std']:.3g}"
	if diagnostics["targets_nearly_constant"]:
		title += " targets~const"
	if diagnostics.get("posterior_nearly_constant"):
		title += " mu~const"
	ax.set_title(title, fontsize=7)
	if len(ax.get_legend_handles_labels()[0]) > 0:
		ax.legend(loc="best", fontsize=6, framealpha=0.9)

	fig.savefig(out_path, dpi=dpi)
	plt.close(fig)

def draw_field_png(optimizer):
	import matplotlib.pyplot as plt
	import os

	frame = bpy.context.scene.frame_current
	frame_str = f"{frame:03d}"
	frames_dir = get_bm_frames_dir()
	out_path = os.path.join(frames_dir, f"field_{frame_str}.png")
	n_px = 400
	dim_x = 0
	dim_y = 1
	fixed_value = 0.5

	prediction = get_field_prediction(optimizer, n_px=n_px, dim_x=dim_x, dim_y=dim_y, fixed_value=fixed_value)
	X = prediction["X_raw"]
	mu = prediction["mu"]
	sigma = prediction["sigma"]
	x_lin = prediction["x_lin"]
	y_lin = prediction["y_lin"]
	opt_x = prediction["opt_x"]
	opt_y = prediction["opt_y"]
	diagnostics = prediction["diagnostics"]

	# Render exakt n_px x n_px
	dpi = 100
	fig = plt.figure(figsize=(n_px / dpi, n_px / dpi), dpi=dpi)
	ax = fig.add_axes([0.15, 0.15, 0.68, 0.80])
	cax = fig.add_axes([0.86, 0.15, 0.035, 0.80])

	if prediction["ok"]:
		image = ax.imshow(
			mu,
			origin="lower",
			extent=(0.0, 1.0, 0.0, 1.0),
			cmap="coolwarm",
			interpolation="nearest"
		)
		colorbar = fig.colorbar(image, cax=cax)
		colorbar.ax.tick_params(labelsize=6)
		colorbar.set_label("optimizer target mu", fontsize=6)

		if sigma is not None:
			ax.contour(
				x_lin,
				y_lin,
				sigma,
				levels=6,
				colors="white",
				linewidths=0.5,
				alpha=0.7,
			)
	else:
		cax.set_axis_off()
		ax.text(
			0.5,
			0.95,
			prediction["message"],
			ha="center",
			va="top",
			transform=ax.transAxes,
			fontsize=7,
			bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
		)

	# alle vorhandenen Punkte einzeichnen (2D-Projektion)
	if len(X) > 0:
		ax.scatter(X[:, dim_x], X[:, dim_y], s=30, c="black", edgecolors="black", linewidths=0.8)

	# aktueller (letzter) Punkt
	if len(X) > 0:
		ax.scatter(X[-1, dim_x], X[-1, dim_y], s=120, c="white", edgecolors="black", linewidths=2.0, zorder=10)
	if prediction["ok"]:
		ax.scatter(opt_x, opt_y, s=80, c="red", edgecolors="white", linewidths=0.8, zorder=11)

	ax.set_xlim(0.0, 1.0)
	ax.set_ylim(0.0, 1.0)
	
	ax.set_axis_on()
	ax.set_xlabel("shapekey 1")
	ax.set_ylabel("shapekey 2")
	ax.tick_params(axis="both", labelsize=6)
	ax.grid(True, linewidth=0.3, alpha=0.7)
	title = f"n={diagnostics['sample_count']} unique={diagnostics['unique_sample_count']} dup={diagnostics['duplicate_count']}"
	if diagnostics["target_std"] is not None:
		title += f" y_std={diagnostics['target_std']:.3g}"
	if diagnostics["targets_nearly_constant"]:
		title += " targets~const"
	if diagnostics.get("posterior_nearly_constant"):
		title += " mu~const"
	ax.set_title(title, fontsize=7)
	
	fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.05)
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
			base_acquisition=acquisition.ConstantLiar(xi=xi),
			strategy="mean"
		)
	
	# pbouds erstellen
	pbounds = {}
	chromosome = []
	for i in range(len(shape_keys) - 1):
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
	basics.jobs.append([write_step_txt, optimizer])
	basics.jobs.append([append_steps_csv, optimizer])

	if len(shape_keys) == 2:
		basics.jobs.append([draw_line_png, optimizer])

	if len(shape_keys) == 3:
		basics.jobs.append([draw_field_png, optimizer])

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
		basics.jobs.append([write_step_txt, optimizer])
		basics.jobs.append([append_steps_csv, optimizer])
		
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
