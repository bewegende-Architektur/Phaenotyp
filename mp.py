# coding-utf8
from multiprocessing import Manager, Value, cpu_count, Pool
from numpy import array, empty, append, poly1d, polyfit, linalg, zeros, intersect1d
from math import sqrt
from math import tanh

import sys
from time import time
from datetime import timedelta

# import python from parent directory like pointed out here:
# https://stackoverflow.com/questions/714063/importing-modules-from-parent-folder
import os
import sys
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from PyNite import FEModel3D

import pickle
import gc
gc.disable()

def print_data(text):
	"""
	Print data for debugging
	:param text: Needs a text as string (Do not pass as list)
	"""
	print("Phaenotyp |", text)

# get arguments
directory_blend = sys.argv[1]
path_import = directory_blend + "/Phaenotyp-export_mp.p"
scipy_available = sys.argv[2]
calculation_type = sys.argv[3]

# start timer
start_time = time()

def import_trusses():
	# get trusses stored as dict with frame as key
	file = open(path_import, 'rb')
	imported_trusses = pickle.load(file)
	file.close()

	return imported_trusses

# run one single fea and save result into feas (multiprocessing manager dict)
def run_fea_pn(scipy_available, calculation_type, feas, truss, frame):
	# the variables truss, and frame are passed to mp
	# this variables can not be returned with multiprocessing
	# instead of this a dict with multiprocessing.Manager is created
	# the dict feas stores one anlysis for each frame
	# the dict fea is created temporarily in run_fea and is wirrten to feas
	# analyze the model
	
	# start time
	start_time = time()
	
	if scipy_available == "True":
		if calculation_type == "first_order":
			truss.analyze(check_statics=False, sparse=True)

		elif calculation_type == "first_order_linear":
			truss.analyze_linear(check_statics=False, sparse=True)

		else:
			truss.analyze_PDelta(check_stability=False, sparse=True)

	if scipy_available == "False":
		if calculation_type == "first_order":
			truss.analyze(check_statics=False, sparse=False)

		elif calculation_type == "first_order_linear":
			truss.analyze_linear(check_statics=False, sparse=False)

		else:
			truss.analyze_PDelta(check_stability=False, sparse=False)

	feas[str(frame)] = truss

	# get duration
	elapsed = time() - start_time
	text = calculation_type + " calculation for frame " + str(frame) + " done"
	text +=  " | " + str(timedelta(seconds=elapsed))
	print_data(text)
	sys.stdout.flush()

def run_fea_fd(feas, truss, frame):
	# based on:
	# Oliver Natt
	# Physik mit Python
	# Simulationen, Visualisierungen und Animationen von Anfang an
	# 1. Auflage, Springer Spektrum, 2020
	# https://pyph.de/1/1/index.php?name=code&kap=5&pgm=4

	# start time
	start_time = time()

	# amount of dimensions
	dim = 3

	points_array = truss[0]
	supports_ids = truss[1]
	edges_array = truss[2]
	forces_array = truss[3]

	# amount of points, edges, supports, verts
	n_points_array = points_array.shape[0]
	n_edges_array = edges_array.shape[0]
	n_supports = len(supports_ids)
	n_verts = n_points_array - n_supports
	n_equation = n_verts * dim

	# create list of indicies
	verts_id = list(set(range(n_points_array)) - set(supports_ids))

	def vector(vertices, edge):
		v_0, v_1 = edges_array[edge]
		if vertices == v_0:
			vec = points_array[v_1] - points_array[v_0]
		else:
			vec = points_array[v_0] - points_array[v_1]
		return vec / linalg.norm(vec)


	# create equation
	truss = zeros((n_equation, n_equation))
	for id, edge in enumerate(edges_array):
		for k in intersect1d(edge, verts_id):
			n = verts_id.index(k)
			truss[n * dim:(n + 1) * dim, id] = vector(k, id)

	# Löse das Gleichungssystem A @ F = -forces_array nach den Kräften F.
	b = -forces_array[verts_id].reshape(-1)
	F = linalg.solve(truss, b)

	# Berechne die äußeren Kräfte.
	for id, edge in enumerate(edges_array):
		for k in intersect1d(edge, supports_ids):
			forces_array[k] -= F[id] * vector(k, id)

	feas[str(frame)] = F
	
	# get duration
	elapsed = time() - start_time
	text = calculation_type + " calculation for frame " + str(frame) + " done"
	text +=  " | " + str(timedelta(seconds=elapsed))
	print_data(text)
	sys.stdout.flush()

def mp_pool():
	global scipy_available

	manager = Manager() # needed for mp
	feas = manager.dict() # is saving all calculations by frame

	cores = cpu_count()
	'''
	text = "rendering with " + str(cores) + " cores."
	print_data(text)
	'''

	pool = Pool(processes=cores)

	# for PyNite
	if calculation_type != "force_distribution":
		for frame, truss in imported_trusses.items():
			pool.apply_async(run_fea_pn, args=(scipy_available, calculation_type, feas, truss, frame,))

	# for force distribution
	else:
		for frame, truss in imported_trusses.items():
			pool.apply_async(run_fea_fd, args=(feas, truss, frame,))

	pool.close()
	pool.join()

	return feas

def export_trusses():
	# export back to blender
	path_export = directory_blend + "/Phaenotyp-return_mp.p"
	file = open(path_export, 'wb')
	pickle.dump(dict(feas), file) # use dict() to convert mp_dict to dict
	file.close()

if __name__ == "__main__":
	imported_trusses = import_trusses()
	feas = mp_pool()
	export_trusses()
	# give feedback to user
	end_time = time()

	# print only frames to make progress.http work correctly
	'''
	elapsed_time = end_time - start_time
	text = "time elapsed: " + str(elapsed_time) + " s"
	print_data(text)
	'''

	# exit
	sys.exit()
