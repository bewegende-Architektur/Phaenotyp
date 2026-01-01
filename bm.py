import bpy
from phaenotyp import basics, operators, geometry, calculation
import numpy as np

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
	
	'''
	Part von Karl einfügen
	'''
	
	# geometry post and viz
	basics.jobs.append([finish])
	
	# run jobs
	bpy.ops.wm.phaenotyp_jobs()
