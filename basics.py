import bpy

# this function is sorting the keys of the dict
# (to avoid iterating like 0,10,2,3 ...)
def sorted_keys(dict):
    keys_int = list(map(int, dict))
    sorted_int_keys = sorted(keys_int)
    return sorted_int_keys

# to avoid division by zero if a force is 0
def avoid_div_zero(a,b):
    if b == 0:
        return 0
    else:
        return a/b

# function to return the smallest_minus or biggest_plus in a list
def return_max_diff_to_zero(list):
    list_copy = list.copy()
    list_copy.sort()

    smallest_minus = list_copy[0]
    biggest_plus = list_copy[len(list_copy)-1]

    if abs(smallest_minus) > abs(biggest_plus):
        return smallest_minus
    else:
        return biggest_plus

# functions to handle objects
def delete_obj_if_existing(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)

def delete_mesh_if_existing(name):
    mesh = bpy.data.meshes.get(name)
    if mesh:
        bpy.data.meshes.remove(mesh, do_unlink=True)

def delete_col_if_existing(name):
    col = bpy.data.collections.get(name)
    if col:
        bpy.data.collections.remove(col, do_unlink=True)

def delete_obj_if_name_contains(text):
    for obj in bpy.data.objects:
        if text in obj.name_full:
            bpy.data.objects.remove(obj, do_unlink=True)

# change view to show vertex-colors
def view_vertex_colors():
    # change viewport to material
    # based on approach from Hotox:
    # https://devtalk.blender.org/t/how-to-change-view3dshading-type-in-2-8/3462
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.light = 'FLAT'
                    space.shading.color_type = 'VERTEX'
