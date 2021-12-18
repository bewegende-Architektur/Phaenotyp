bl_info = {
    "name": "Phänotyp",
    "description": "Genetic optimization of architectural structures",
    "author": "bewegende Architektur e.U. and Karl Deix",
    "version": (0, 0, 1),
    "blender": (3, 0, 0),
    "location": "3D View > Tools",
}

# With Support from Karl Deix
# Analysis with: https://github.com/JWock82/PyNite
# GA based on: https://www.geeksforgeeks.org/genetic-algorithms/

# Material properties:
# https://www.johannes-strommer.com/formeln/flaechentraegheitsmoment-widerstandsmoment/
# https://www.maschinenbau-wissen.de/skript3/mechanik/festigkeitslehre/134-knicken-euler

import math

class data:
    # dependencies
    scipy_loaded = False
    pynite_loaded = False

    # steel pipe with 60/50 mm as example
    Do =   60 # mm (diameter outside)
    Di =   50 # mm (diameter inside)
    E  =  210 # kN/mm2 modulus of elasticity for steel
    v  = 0.29 # Poisson's ratio of steel
    d  = 7.85 # g/cm3 density of steel

    # calculated in data.update()
    G  = None
    Iy = None
    Iz = None
    J  = None
    A  = None
    kg = None

    # store geoemtry
    obj = None
    mesh = None
    vertices = None
    edges = None
    support_ids = []

    # results for each frame
    result_max_axial = {}
    result_max_moment_y = {}
    result_max_moment_z = {}
    force_type_viz = "max_axial"

    # visualization
    scale_max_axial = 0.15
    scale_max_moment_y = 0.15
    scale_max_moment_z = 0.15
    
    curves = []
    materials = []

    # triggers
    calculate_update_post = False
    genetetic_mutation_update_post = False
    done = False

    # genetic algorithm
    shape_keys = []

    population = []
    new_generation = []
    generation_id = 1

    population_size = 20
    elitism = 2
    new_generation_size = population_size - elitism

    genes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    ga_state = "create initial population"

    chromosome = {}
    
    @staticmethod
    def update():
        # shear modulus, 81.4 GPa
        data.G  = data.E * data.v

        # moment of inertia, 329376 mm⁴
        data.Iy = math.pi * (data.Do**4 - data.Di**4)/64
        data.Iz = data.Iy

        # torsional constant, 10979 mm³
        data.J  = math.pi * (data.Do**4 - data.Di**4)/(32*data.Do)

        # cross-sectional area, 864 mm²
        data.A  = (math.pi * (data.Do*0.5)**2) - (math.pi * (data.Di*0.5)**2)

        # weight of profile, 6.79 kg/m
        data.kg =  data.A*data.d * 0.001


# handle dependencies
try:
    import scipy
    data.scipy_loaded = True
except:
    data.scipy_loaded = False

try:
    from PyNite import FEModel3D
    data.pynite_loaded = True
except:
    data.pynite_loaded = False

from threading import Thread
import random

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from bpy.props import (IntProperty, FloatProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)


class CustomProperties(PropertyGroup):
    Do: FloatProperty(
        name = "Do",
        description = "Diameter of pipe outside",
        default = 60,
        min = 5,
        max = 500
        )

    Di: FloatProperty(
        name = "Di",
        description = "Diameter of pipe inside. Needs to be smaller than Diameter outside",
        default = 50,
        min = 5,
        max = 500
        )

    E: FloatProperty(
        name = "E",
        description = "modulus of elasticity",
        default = 210,
        min = 50,
        max = 500
        )

    v: FloatProperty(
        name = "v",
        description = "Poisson's ratio",
        default = 0.29,
        min = 0.01,
        max = 1
        )

    d: FloatProperty(
        name = "d",
        description = "Density",
        default = 7.85,
        min = 0.01,
        max = 30.0
        )

    population_size: IntProperty(
        name = "population_size",
        description="Size of population for GA",
        default = 20,
        min = 10,
        max = 1000
        )

    elitism: IntProperty(
        name = "elitism",
        description="Size of elitism for GA",
        default = 2,
        min = 1,
        max = 100
        )
        
    forces: EnumProperty(
        name="forces:",
        description="Force types",
        items=[
                ("max_axial", "Max axial", ""),
                ("max_moment_y", "Max moment Y", ""),
                ("max_moment_z", "Max moment Z", "")
               ]
        )


def update_mesh():
    frame = bpy.context.scene.frame_current

    # apply chromosome if available
    try:
        for id, key in enumerate(data.shape_keys):
            v = data.chromosome[frame][id]
            key.value = v
    except:
        pass

    # get absolute position of vertex (when using shape-keys, animation et cetera)
    dg = bpy.context.evaluated_depsgraph_get()
    obj = data.obj.evaluated_get(dg)

    data.mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
    data.vertices = data.mesh.vertices
    data.edges =data.mesh.edges


def transfer_analyze():
    truss = FEModel3D()

    update_mesh()

    # add nodes from vertices
    for vertex_id, vertex in enumerate(data.vertices):
        name = "node_" + str(vertex_id)
        x = vertex.co[0]
        y = vertex.co[1]
        z = vertex.co[2]

        truss.add_node(name, x,y,z)

    # define support
    for support_id in data.support_ids:
        name = "node_" + str(support_id)

        # first node is fixed
        if data.support_ids.index(support_id) == 0:
            truss.def_support(name, True, True, True, False, False, False)

        # all other nodes are only fixed in loc z-direction
        else:
            truss.def_support(name, False, False, True, False, False, False)

    # create members
    members = []

    for edge_id, edge in enumerate(data.edges):
        name = "edge_" + str(edge_id)
        vertex_0_id = edge.vertices[0]
        vertex_1_id = edge.vertices[1]

        node_0 = str("node_") + str(vertex_0_id)
        node_1 = str("node_") + str(vertex_1_id)

        truss.add_member(name, node_0, node_1, data.E, data.G, data.Iy, data.Iz, data.J, data.A)

        members.append(name)

        # add gravity
        vertex_0 = data.vertices[vertex_0_id]
        vertex_1 = data.vertices[vertex_1_id]

        dist_vector = vertex_1.co - vertex_0.co
        length = dist_vector.length

        kN = data.kg * -0.0098

        load = kN * length * 0.5
        truss.add_node_load(node_0, "FZ", load)
        truss.add_node_load(node_1, "FZ", load)

    # analyze the model
    truss.analyze(check_statics=False, sparse=False)

    # append result_max_axials
    max_axial = []
    max_moment_y = []
    max_moment_z = []

    for member in members:
        max_axial.append(truss.Members[member].max_axial())
        max_moment_y.append(truss.Members[member].max_moment("My"))
        max_moment_z.append(truss.Members[member].max_moment("Mz"))

        """
        deflection("dx", x=0)
        deflection("dy", x=0)
        deflection("dz", x=0)
        """

    # save as current frame
    frame = bpy.context.scene.frame_current
    data.result_max_axial[frame] = max_axial
    data.result_max_moment_y[frame] = max_moment_y
    data.result_max_moment_z[frame] = max_moment_z


# genetic algorithm
class individual(object):
    def __init__(self, chromosome):
        self.chromosome = chromosome
        self.fitness = self.cal_fitness()

    @classmethod
    def mutated_genes(self):
        gene = random.choice(data.genes)
        return gene

    @classmethod
    def create_gnome(self):
        # create gnome from available shape keys
        gnome_len = len(data.shape_keys)-1 # to exlude basis
        chromosome = [self.mutated_genes() for _ in range(gnome_len)]

        # apply shape keys
        for id, key in enumerate(data.shape_keys):
            if id > 0: # to exlude basis
                key.value = chromosome[0]*0.1

        return chromosome

    def mate(self, par2):
        # chromosome for offspring
        child_chromosome = []
        for gp1, gp2 in zip(self.chromosome, par2.chromosome):

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
                child_chromosome.append(self.mutated_genes())

        # apply shape keys
        for id, key in enumerate(data.shape_keys):
            if id > 0: # to exlude basis
                key.value = child_chromosome[0]*0.1

        return individual(child_chromosome)

    def cal_fitness(self):
        transfer_analyze()
        frame = bpy.context.scene.frame_current

        # get forcetyp and force
        if data.force_type_viz == "max_axial":
            result = data.result_max_axial
    
        elif data.force_type_viz == "max_moment_y":
            result = data.result_max_moment_y
            
        elif data.force_type_viz == "max_moment_z":
            result = data.result_max_moment_z
            
        else:
            pass
        
        # get fitness
        fitness = max(result[frame])
        return fitness


def genetic_mutation():
    frame = bpy.context.scene.frame_current

    if data.ga_state == "create initial population":
        if len(data.population) < data.population_size:
            # create chromosome with set of shapekeys
            chromosome = individual.create_gnome()
            data.population.append(individual(chromosome))
            data.chromosome[frame] = chromosome
            print("initial population append:", chromosome)

        else:
            data.ga_state = "create new generation"


    if data.ga_state == "create new generation":
        # sort previous population according to fitness
        data.population = sorted(data.population, key = lambda x:x.fitness)

        # print previous population to terminal
        for id, gnome in enumerate(data.population):
            print(gnome.chromosome, "with fitness:", gnome.fitness)

        # create empty list of a new generation
        new_generation = []
        print("generation", str(data.generation_id) + ":")

        # copy fittest ten percent
        for i in range(data.elitism):
            data.new_generation.append(data.population[i])

        data.ga_state = "populate new generation"


    if data.ga_state == "populate new generation":
        if len(data.new_generation) < data.new_generation_size:
            # pair best 50 % of the previous population
            parent_1 = random.choice(data.population[:50])
            parent_2 = random.choice(data.population[:50])
            child = parent_1.mate(parent_2)
            data.new_generation.append(child)

            # print child to terminal
            print ("child:", child.chromosome, "fitness", child.fitness)

        if len(data.new_generation) == data.new_generation_size:
            data.population = data.new_generation

            data.new_generation = []
            data.generation_id += 1

            # start new generation
            data.ga_state = "create new generation"


def create_curves():
    reset_collection_geometry_material()

    frame = bpy.context.scene.frame_current

    # draw curves
    for member_id, max_axial in enumerate(data.result_max_axial[frame]):
        # set color
        if max_axial > 0:
            r,g,b = 1,0,0
        else:
            r,g,b = 0,0,1

        # map value for geometry
        curve_radius = max_axial * data.scale_max_axial

        vertex_0_id = data.edges[member_id].vertices[0]
        vertex_1_id = data.edges[member_id].vertices[1]

        vertex_0 = data.vertices[vertex_0_id]
        vertex_1 = data.vertices[vertex_1_id]

        name = "<pynite>member_" + str(member_id)

        # create the Curve Datablock
        curve = bpy.data.curves.new(name, type="CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2

        # add points
        polyline = curve.splines.new("POLY")
        polyline.points.add(1)

        # first point
        x = vertex_0.co[0]
        y = vertex_0.co[1]
        z = vertex_0.co[2]
        polyline.points[0].co = (x,y,z, 1)

        # second point
        x = vertex_1.co[0]
        y = vertex_1.co[1]
        z = vertex_1.co[2]
        polyline.points[1].co = (x,y,z, 1)

        # create Object
        obj = bpy.data.objects.new(name, curve)
        curve.bevel_depth = curve_radius

        # link object to collection
        bpy.data.collections["<pynite>"].objects.link(obj)

        # new material
        name = "<pynite>member_" + str(member_id)
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (r,g,b,1)
        obj.data.materials.append(mat)
        obj.active_material_index = len(obj.data.materials) - 1

        # save to data
        data.curves.append(obj)
        data.materials.append(mat)


    # deselect, because last curve would be selected
    bpy.ops.object.select_all(action="DESELECT")

    data.done = True


def update_curves():
    frame = bpy.context.scene.frame_current

    for id, obj in enumerate(data.curves):
        # get forcetyp and force
        if data.force_type_viz == "max_axial":
            result = data.result_max_axial
            scale = data.scale_max_axial
    
        elif data.force_type_viz == "max_moment_y":
            result = data.result_max_moment_y
            scale = data.scale_max_moment_y
            
        elif data.force_type_viz == "max_moment_z":
            result = data.result_max_moment_z
            scale = data.scale_max_moment_z
            
        else:
            pass

        force = result[frame][id]

        # get curve from curve-obj
        curve_name = obj.data.name
        curve = bpy.data.curves[curve_name]

        # set color
        if force > 0:
            r,g,b = 1,0,0
        else:
            r,g,b = 0,0,1

        mat = data.materials[id]
        mat.diffuse_color = (r,g,b,1)

        # change curve bevel
        curve_radius = force * scale
        curve.bevel_depth = curve_radius

        # change location
        vertex_0_id = data.edges[id].vertices[0]
        vertex_1_id = data.edges[id].vertices[1]

        vertex_0 = data.vertices[vertex_0_id]
        vertex_1 = data.vertices[vertex_1_id]

        curve.splines[0].points[0].co = [vertex_0.co[0], vertex_0.co[1], vertex_0.co[2], 1]
        curve.splines[0].points[1].co = [vertex_1.co[0], vertex_1.co[1], vertex_1.co[2], 1]


def reset_data():
    data.curves = []
    data.materials = []

    data.shape_keys = []
    data.population = []
    data.new_generation = []
    data.generation_id = 1
    data.chromosome = {}
    data.ga_state = "create initial population"

def reset_collection_geometry_material():
    # reset scene

    for collection in bpy.data.collections:
        if "<pynite>" in collection.name_full:
            bpy.data.collections.remove(collection)

    for material in bpy.data.materials:
        if "<pynite>" in material.name_full:
            bpy.data.materials.remove(material)

    for obj in bpy.data.objects:
        if "<pynite>" in obj.name_full:
            bpy.data.objects.remove(obj)

    for curve in bpy.data.curves:
        if "<pynite>" in obj.name_full:
            bpy.data.curves.remove(curve)

    collection = bpy.data.collections.new("<pynite>")
    bpy.context.scene.collection.children.link(collection)


class WM_OT_install_dep(Operator):
    bl_label = "install_dep"
    bl_idname = "wm.install_dep"
    bl_description = "Please restart as Admin to install dependencies"

    def execute(self, context):
        import subprocess
        import sys

        py_exec = str(sys.executable)
        subprocess.call([py_exec, "-m", "ensurepip", "--user" ])
        subprocess.call([py_exec, "-m", "pip", "install", "--upgrade", "pip" ])

        if data.scipy_loaded == False:
            subprocess.call([py_exec,"-m", "pip", "install", f"--target={py_exec[:-14]}" + "lib", "SciPy"])

        if data.pynite_loaded == False:
            subprocess.call([py_exec,"-m", "pip", "install", "--upgrade", "PyNiteFEA"])

        # try to load them again
        try:
            import scipy
            data.scipy_loaded = True
        except:
            data.scipy_loaded = False

        try:
            from PyNite import FEModel3D
            data.pynite_loaded = True
        except:
            data.pynite_loaded = False

        return {"FINISHED"}


class WM_OT_set_structure(Operator):
    bl_label = "set_obj"
    bl_idname = "wm.set_structure"
    bl_description = "Please select a mesh in Object Mode and press set, to define a structure"

    def execute(self, context):
        data.obj = bpy.context.active_object
        data.mesh = bpy.data.meshes[data.obj.data.name]
        data.vertices = data.obj.data.vertices
        data.edges =data.mesh.edges

        bpy.ops.object.mode_set(mode="EDIT")
        return {"FINISHED"}


class WM_OT_set_support(Operator):
    bl_label = "set_support"
    bl_idname = "wm.set_support"
    bl_description = "Please select vertices and press set, to define them as support (Be sure, that you are in Edit Mode of the Structure)"

    def execute(self, context):
        if context.active_object.mode == "EDIT":
            # get selected vertices
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.mode_set(mode="EDIT")
            data.support_ids = [i.index for i in bpy.context.active_object.data.vertices if i.select]
            bpy.ops.object.mode_set(mode="OBJECT")

        return {"FINISHED"}


class WM_OT_calculate_single_frame(Operator):
    bl_label = "calculate_single_frame"
    bl_idname = "wm.calculate_single_frame"
    bl_description = "Calulate single frame"

    def execute(self, context):
        reset_data()
        reset_collection_geometry_material()

        transfer_analyze()
        create_curves()

        return {"FINISHED"}


class WM_OT_calculate_animation(Operator):
    bl_label = "calculate_animation"
    bl_idname = "wm.calculate_animation"
    bl_description = "Calulate animation"

    def execute(self, context):
        reset_data()
        reset_collection_geometry_material()

        transfer_analyze()
        create_curves()

        # activate calculation in update_post
        data.calculate_update_post = True

        # set animation to first frame and start
        start = bpy.context.scene.frame_start
        bpy.context.scene.frame_current = start
        bpy.ops.screen.animation_play()

        return {"FINISHED"}


class WM_OT_genetic_mutation(Operator):
    bl_label = "genetic_mutation"
    bl_idname = "wm.genetic_mutation"
    bl_description = "start genetic muation over selected shape keys"

    def execute(self, context):
        # reset
        reset_data()
        reset_collection_geometry_material()

        # shape keys
        shape_key = data.obj.data.shape_keys
        for keyblock in shape_key.key_blocks:
            data.shape_keys.append(keyblock)

        transfer_analyze()
        create_curves()

        # activate calculation in update_post
        data.genetetic_mutation_update_post = True

        # clear population
        data.population = []

        # set animation to first frame and start
        start = bpy.context.scene.frame_start
        bpy.context.scene.frame_current = start
        bpy.ops.screen.animation_play()

        return {"FINISHED"}


class WM_OT_viz_scale_up(Operator):
    bl_label = "viz_scale_up"
    bl_idname = "wm.viz_scale_up"

    def execute(self, context):
        # get forcetyp and force
        if data.force_type_viz == "max_axial":
            data.scale_max_axial = data.scale_max_axial * 1.25
    
        elif data.force_type_viz == "max_moment_y":
            data.scale_max_moment_y = data.scale_max_moment_y * 1.25
            
        elif data.force_type_viz == "max_moment_z":
            data.scale_max_moment_z = data.scale_max_moment_z * 1.25
            
        else:
            pass

        update_curves()

        return {"FINISHED"}


class WM_OT_viz_scale_down(Operator):
    bl_label = "viz_scale_down"
    bl_idname = "wm.viz_scale_down"

    def execute(self, context):
        # get forcetyp and force
        if data.force_type_viz == "max_axial":
            data.scale_max_axial = data.scale_max_axial * 0.75
    
        elif data.force_type_viz == "max_moment_y":
            data.scale_max_moment_y = data.scale_max_moment_y * 0.75
            
        elif data.force_type_viz == "max_moment_z":
            data.scale_max_moment_z = data.scale_max_moment_z * 0.75
            
        else:
            pass

        update_curves()

        return {"FINISHED"}


class WM_OT_viz_update(Operator):
    bl_label = "viz_update"
    bl_idname = "wm.viz_update"

    def execute(self, context):
        update_curves()

        return {"FINISHED"}


class WM_OT_reset(Operator):
    bl_label = "reset"
    bl_idname = "wm.reset"

    def execute(self, context):
        reset_collection_geometry_material()

        data.obj = None
        data.vertices = None
        data.edges = None
        data.done = None
        data.support_ids = []

        return {"FINISHED"}


class OBJECT_PT_CustomPanel(Panel):
    bl_label = "Phänotyp"
    bl_idname = "OBJECT_PT_custom_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Phänotyp"

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        phaenotyp = scene.phaenotyp

        # install scipy and PyNite if necessary
        if data.scipy_loaded == False or data.pynite_loaded == False:
            # define active object
            box = layout.box()
            box.label(text="Installation:")
            box.operator("wm.install_dep", text="Install")
            box.label(text="Installation can take a few minutes")

        else:
            # define material and geometry
            box = layout.box()
            box.label(text="Setup:")
            
            box.prop(phaenotyp, "Do", text="Diameter outside")
            box.prop(phaenotyp, "Di", text="Diameter inside")
            box.prop(phaenotyp, "E", text="Modulus of elasticity")
            box.prop(phaenotyp, "v", text="Poisson's ratio")
            box.prop(phaenotyp, "d", text="Density")
            
            data.Do = phaenotyp.Do
            if phaenotyp.Di < phaenotyp.Do: # apply value only if smaller
                data.Di = phaenotyp.Di
            
            data.E = phaenotyp.E
            data.v = phaenotyp.v
            data.d = phaenotyp.d

            data.update() # calculate G, Iy, Iz, J, A, kg
            box.label(text="G = " + str(round(data.G,2)) + " GPa")
            box.label(text="Iy = " + str(int(data.Iy)) + " mm⁴")
            box.label(text="Iz = " + str(int(data.Iz)) + " mm⁴")
            box.label(text="J = " + str(int(data.J)) + " mm³")
            box.label(text="A = " + str(int(data.A)) + " mm²")
            box.label(text="kg = " + str(round(data.kg,2)) + " kg/m")
        
            # define active object
            box = layout.box()
            box.label(text="Structure:")
            box.operator("wm.set_structure", text="Set")

            if data.obj:
                box.label(text = data.obj.name_full + " is defined as structure")

                # define support
                box = layout.box()
                box.label(text="Support:")
                box.operator("wm.set_support", text="Set")
                if len(data.support_ids) > 0:
                    box.label(text = str(len(data.support_ids)) + " vertices defined as support")

                    # Analysis
                    box = layout.box()
                    box.label(text="Analysis:")
                    box.operator("wm.calculate_single_frame", text="Single Frame")
                    box.operator("wm.calculate_animation", text="Animation")

                    shape_key = data.obj.data.shape_keys
                    if shape_key:
                        # Genetic Mutation:
                        box = layout.box()
                        box.label(text="Genetic Mutation:")
                        box.prop(phaenotyp, "population_size", text="Size of population for GA")
                        box.prop(phaenotyp, "elitism", text="Size of elitism for GA")
                        box.prop(phaenotyp, "forces", text="Fitness")
                        data.force_type_viz = phaenotyp.forces
                        

                        for keyblock in shape_key.key_blocks:
                            name = keyblock.name
                            box.label(text=name)


                        box.operator("wm.genetic_mutation", text="Start")

                    # Visualization
                    if data.done:
                        box = layout.box()
                        box.label(text="Vizualisation:")
                        box.prop(phaenotyp, "forces", text="Force")
                        data.force_type_viz = phaenotyp.forces
                        box.operator("wm.viz_update", text="update")
                        
                        col = box.column_flow(columns=2, align=False)
                        col.operator("wm.viz_scale_up", text="Up")
                        col.operator("wm.viz_scale_down", text="Down")


            box = layout.box()
            box.operator("wm.reset", text="Reset")


classes = (
    CustomProperties,
    
    WM_OT_install_dep,
    WM_OT_set_structure,
    WM_OT_set_support,
    WM_OT_calculate_single_frame,
    WM_OT_calculate_animation,
    WM_OT_genetic_mutation,

    WM_OT_viz_scale_up,
    WM_OT_viz_scale_down,
    WM_OT_viz_update,

    WM_OT_reset,
    OBJECT_PT_CustomPanel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    bpy.types.Scene.phaenotyp = PointerProperty(type=CustomProperties)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    del bpy.types.Scene.phaenotyp


def draw():
    for support_id in data.support_ids:
        vertices = data.vertices

        x = vertices[support_id].co[0]
        y = vertices[support_id].co[1]
        z = vertices[support_id].co[2]
        scale = 0.1

        coords = [
                    [ 1,  1, -2], [ 0,  0,  0],
                    [ 1, -1, -2], [ 0,  0,  0],
                    [-1, -1, -2], [ 0,  0,  0],
                    [-1,  1, -2], [ 0,  0,  0],

                    [ 1,  1, -2], [ 1, -1, -2],
                    [ 1, -1, -2], [-1, -1, -2],
                    [-1, -1, -2], [-1,  1, -2],
                    [-1,  1, -2], [ 1,  1, -2]
                    ]

        for pos in coords:
            pos[0] = pos[0]*scale + x
            pos[1] = pos[1]*scale + y
            pos[2] = pos[2]*scale + z

        shader = gpu.shader.from_builtin("3D_UNIFORM_COLOR")
        batch = batch_for_shader(shader, "LINES", {"pos": coords})

        shader.bind()
        shader.uniform_float("color", (1, 1, 1, 1))
        batch.draw(shader)


draw_handler = bpy.types.SpaceView3D.draw_handler_add(draw, (), "WINDOW", "POST_VIEW")


def update_post(scene):
    update_mesh()
    # Analyze
    if data.calculate_update_post:
        transfer_analyze()

        # avoid to repeat at end
        if bpy.context.scene.frame_end == bpy.context.scene.frame_current:
            bpy.ops.screen.animation_cancel()
            data.calculate_update_post = False
            print("done")

    # Genetic Mutation (Analys in fitness function)
    if data.genetetic_mutation_update_post:
        genetic_mutation()

        # avoid to repeat at end
        if bpy.context.scene.frame_end == bpy.context.scene.frame_current:
            bpy.ops.screen.animation_cancel()
            data.genetetic_mutation_update_post = False
            print("done")

    update_curves()


bpy.app.handlers.frame_change_post.clear()
bpy.app.handlers.frame_change_post.append(update_post)

if __name__ == "__main__":
    register()

try:
    from PyNite import FEModel3D
except:
    pass

try:
    import scipy
except:
    pass
