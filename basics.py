import bpy
import bmesh
from phaenotyp import geometry
from queue import Queue
from time import time
from datetime import timedelta

blender_version = (4,0,2)
phaenotyp_version = (0,3,0)
phaenotyp_name = (
	"Phänotyp " 
	+ str(phaenotyp_version[0]) + "."
	+ str(phaenotyp_version[1]) + "."
	+ str(phaenotyp_version[2])
	)

def print_data(text):
	"""
	Print data for debugging
	:param text: Needs a text as string (Do not pass as list)
	"""
	print("Phaenotyp |", text)

class timer:
	"""
	Class to handle the timer
	"""
	start_time = None
	
	@staticmethod
	def start():
		"""
		Start the timer
		"""
		timer.start_time = time()
	
	@staticmethod
	def stop():
		"""
		Return the elapsed time
		:return: Formated time in seconds as string
		"""
		elapsed = time() - timer.start_time        
		return " | " + str(timedelta(seconds=elapsed))
		
def create_data():
	"""
	Create scene[<Phaenotyp>] and build all basics to store data.
	All data that should be saved with the blend-file is stored here.
	Data that does not need to be available after restart is generated,
	handeled and stored by the specific function or class.
	"""
	data = bpy.context.scene["<Phaenotyp>"] = {
		"structure": None,
		"supports": {},
		"nodes": {},
		"members": {},
		"quads": {},
		"frames": {},
		"loads_v": {},
		"loads_e": {},
		"loads_f": {},
		"process": {
			"scipy_available": False,
			"version": phaenotyp_version
			},
		"done": {},
		"environment": {},
		"individuals": {},
		"panel_state": {
			"structure": False,
			"calculation_type": False,
			"supports": False,
			"members": False,
			"quads": False,
			"file": False
			},
		"panel_grayed": {
			"scipy": False,
			"calculation_type": False,
			"supports": False,
			"members": False,
			"quads": False,
			"loads": False
			},
		"texts": {},
		"precast": {}
	}

def sorted_keys(dict):
	'''
	Is sorting the keys of the dict (to avoid iterating like 0,10,2,3 ...)
	:param dict dict: Dictionary with keys as string
	:return: Sorted keys as integer
	'''
	keys_int = list(map(int, dict))
	sorted_int_keys = sorted(keys_int)
	return sorted_int_keys

def avoid_div_zero(a,b):
	'''
	To avoid division by zero if a force is 0.
	:param a: Can be integer or float
	:param b: Can be integer or float
	:return: Returns the result or 0 in case of division by zero.
	'''
	if b == 0:
		return 0
	else:
		return a/b

def return_max_diff_to_zero(list):
	'''
	Return the value with the highest difference to zero (for plus or minus)
	:param list: List of integers or floats
	:return: List item of given list
	'''
	list_copy = list.copy()
	list_copy.sort()

	smallest_minus = list_copy[0]
	biggest_plus = list_copy[len(list_copy)-1]

	if abs(smallest_minus) > abs(biggest_plus):
		return smallest_minus
	else:
		return biggest_plus

def delete_obj_if_existing(name):
	'''
	Delete object with given name if existing
	:param name: Name as string
	'''
	obj = bpy.data.objects.get(name)
	if obj:
		bpy.data.objects.remove(obj, do_unlink=True)

def delete_mesh_if_existing(name):
	'''
	Delete mesh with given name if existing
	:param name: Name as string
	'''
	mesh = bpy.data.meshes.get(name)
	if mesh:
		bpy.data.meshes.remove(mesh, do_unlink=True)

def delete_col_if_existing(name):
	'''
	Delete collection with given name if existing
	:param name: Name as string
	'''
	col = bpy.data.collections.get(name)
	if col:
		bpy.data.collections.remove(col, do_unlink=True)

def delete_obj_if_name_contains(text):
	'''
	Delete objectif name contains the given string.
	:param name: Name as string
	'''
	for obj in bpy.data.objects:
		if text in obj.name_full:
			bpy.data.objects.remove(obj, do_unlink=True)

def view_vertex_colors():
	'''
	Change view to show colored material and hide structure.
	'''
	bpy.context.space_data.shading.type = 'MATERIAL'

	# hide structure
	try:
		data = bpy.context.scene["<Phaenotyp>"]
		obj = data["structure"]
		obj.hide_set(True)
		
		# go to object-mode to avoid confusion
		bpy.ops.object.mode_set(mode="OBJECT")
	except:
		pass

def revert_vertex_colors():
	'''
	Change view to solid.
	'''
	bpy.context.space_data.shading.type = 'SOLID'
	
	# data is no longer available after reset
	# therefore the obj is made visible again allready in reset
	
	# try, if the user has deleted the object
	try:
		# go to object-mode to avoid confusion
		bpy.ops.object.mode_set(mode="OBJECT")
	except:
		pass
	
def popup(title = "Phaenotyp", lines=""):
	'''
	Create popup to inform user. The function is based on the answer from ChameleonScales at:
	https://blender.stackexchange.com/questions/169844/multi-line-text-box-with-popup-menu
	:param lines: List of strings to be written.
	'''
	def draw(self, context):
		for line in lines:
			self.layout.label(text=line)
	bpy.context.window_manager.popup_menu(draw, title = title)

def popup_operator(title = "Phaenotyp", lines="", operator=None, text=""):
	'''
	Create popup to inform user and to run an operator. Based on the answer from ChameleonScales at:
	https://blender.stackexchange.com/questions/169844/multi-line-text-box-with-popup-menu
	:param lines: List of strings to be written.
	:param operator: Operator to start.
	:param text: Name of the operator.
	'''
	def draw(self, context):
		for line in lines:
			self.layout.label(text=line)
		self.layout.separator()
		self.layout.operator(operator, text=text)
	bpy.context.window_manager.popup_menu(draw, title = title)

def force_distribution_info(self, context):
	'''
	Create a popup to inform user about force disbribution.
	'''
	# inform user when using force_distribution
	if bpy.context.scene.phaenotyp.calculation_type == "force_distribution":
		# triangulation
		if geometry.triangulation() == False:
			text = ["The selection needs to be triangulated for force distribution.",
				"Should Phaenotyp try to triangulate the selection?"]
			popup_operator(lines=text, operator="wm.fix_structure", text="Triangulate")
			geometry.to_be_fixed = "triangulate"

		else:
			text = [
				"Force distribution is a solver for advance users.",
				"Please make sure, that your structure meets this conditions:",
				"- the mesh is triangulated",
				"- the structure is stable (not flat)",
				"- exactly three vertices are defined as support",
				"- the supports are not connected with egdes",
				"- at least one load is defined"
				]
			popup(lines = text)


# check modifieres in modify or deform
# modifieres working with Phänotyp:
modifiers = {}
modifiers["ARMATURE"] = True
modifiers["CAST"] = True
modifiers["CLOTH"] = True
modifiers["COLLISION"] = True
modifiers["CURVE"] = True
modifiers["DATA_TRANSFER"] = True
modifiers["DYNAMIC_PAINT"] = True
modifiers["DISPLACE"] = True
modifiers["HOOK"] = True
modifiers["LAPLACIANDEFORM"] = True
modifiers["LATTICE"] = True
modifiers["MESH_CACHE"] = True
modifiers["MESH_DEFORM"] = True
modifiers["MESH_SEQUENCE_CACHE"] = True
modifiers["NORMAL_EDIT"] = True
modifiers["NODES"] = True
modifiers["SHRINKWRAP"] = True
modifiers["SIMPLE_DEFORM"] = True
modifiers["SMOOTH"] = True
modifiers["CORRECTIVE_SMOOTH"] = True
modifiers["LAPLACIANSMOOTH"] = True
modifiers["OCEAN"] = True
modifiers["PARTICLE_INSTANCE"] = True
modifiers["PARTICLE_SYSTEM"] = True
modifiers["SOFT_BODY"] = True
modifiers["SURFACE"] = True
modifiers["SURFACE_DEFORM"] = True
modifiers["WARP"] = True
modifiers["WAVE"] = True
modifiers["WEIGHTED_NORMAL"] = True
modifiers["UV_PROJECT"] = True
modifiers["UV_WARP"] = True
modifiers["VERTEX_WEIGHT_EDIT"] = True
modifiers["VERTEX_WEIGHT_MIX"] = True
modifiers["VERTEX_WEIGHT_PROXIMITY"] = True

# not working:
modifiers["ARRAY"] = False
modifiers["BEVEL"] = False
modifiers["BOOLEAN"] = False
modifiers["BUILD"] = False
modifiers["DECIMATE"] = False
modifiers["EDGE_SPLIT"] = False
modifiers["EXPLODE"] = False
modifiers["FLUID"] = False
modifiers["MASK"] = False
modifiers["MIRROR"] = False
modifiers["MESH_TO_VOLUME"] = False
modifiers["MULTIRES"] = False
modifiers["REMESH"] = False
modifiers["SCREW"] = False
modifiers["SKIN"] = False
modifiers["SOLIDIFY"] = False
modifiers["SUBSURF"] = False
modifiers["TRIANGULATE"] = False
modifiers["VOLUME_TO_MESH"] = False
modifiers["WELD"] = False
modifiers["WIREFRAME"] = False
modifiers["VOLUME_DISPLACE"] = False


def check_modifiers():
	'''
	Check the available modifiers of the object an give feedback.
	A popup is opened if a modifier is available that could create weird results.
	'''
	obj = bpy.context.object
	for modifiere in obj.modifiers:
		name = modifiere.type

		if name == "NODES":
			text = ["Geometry Nodes can be used but make sure that no geometry is added",
			   "or deleted during execution of Phaenotyp to avoid weird results"]
			popup(lines = text)

		elif name in modifiers:
			working = modifiers[name]
			if working == False:
				text = [
						"Modifiere with type " + str(name) + " can cause weird results.",
						"",
						"You can use this modifiers:",
						"ARMATURE, CAST, CLOTH, COLLISION, CURVE, DATA_TRANSFER,",
						"DYNAMIC_PAINT, DISPLACE, HOOK, LAPLACIANDEFORM, LATTICE,",
						"MESH_CACHE, MESH_DEFORM, MESH_SEQUENCE_CACHE, NORMAL_EDIT,",
						"NODES, SHRINKWRAP, SIMPLE_DEFORM, SMOOTH, CORRECTIVE_SMOOTH,",
						"LAPLACIANSMOOTH, OCEAN, PARTICLE_INSTANCE, PARTICLE_SYSTEM,",
						"SOFT_BODY, SURFACE, SURFACE_DEFORM, WARP, WAVE, WEIGHTED_NORMAL,",
						"UV_PROJECT, UV_WARP, VERTEX_WEIGHT_EDIT, VERTEX_WEIGHT_MIX,",
						"VERTEX_WEIGHT_PROXIMITY."
						]
				popup(lines = text)

def set_selection_for_load(self, context):
	'''
	Switch type of selection according to type of load (VERT, EDGE, FACE)
	'''
	scene = context.scene
	phaenotyp = scene.phaenotyp
	
	# switch selection mode
	if phaenotyp.load_type == "vertices":
		bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
	if phaenotyp.load_type == "edges":
		bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
	if phaenotyp.load_type == "faces":
		bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
