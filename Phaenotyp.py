
bl_info = {
    "name": "Phänotyp",
    "description": "Genetic optimization of architectural structures",
    "author": "bewegende Architektur e.U. and Karl Deix",
    "version": (0, 0, 3),
    "blender": (3, 0, 0),
    "location": "3D View > Tools",
}

# With Support from Karl Deix
# Analysis with: https://github.com/JWock82/PyNite
# GA based on: https://www.geeksforgeeks.org/genetic-algorithms/

# Material properties:
# https://www.johannes-strommer.com/formeln/flaechentraegheitsmoment-widerstandsmoment/
# https://www.maschinenbau-wissen.de/skript3/mechanik/festigkeitslehre/134-knicken-euler

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from bpy.props import (IntProperty, FloatProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)
from bpy.app.handlers import persistent

import math
from threading import Thread
import random

import sys
import os

from PyNite import FEModel3D

# wird vielleicht doch nicht gebraucht?
from numpy import array
from numpy import empty
from numpy import append

class data:
    # steel pipe with 60/50 mm as example
    Do =     60 # mm (diameter outside)
    Di =     50 # mm (diameter inside)
    E  =  21000 # kN/cm² modulus of elasticity for steel
    G  =   8100 # kN/cm² shear modulus
    d  =   7.85 # g/cm³ density of steel

    # calculated in data.update()
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
    result_axial = {}
    result_moment_y = {}
    result_moment_z = {}
    result_shear_y = {}
    result_shear_z = {}
    result_torque = {}
    result_sigma = {}
    result_deflection = {}

    force_type_viz = "sigma"

    # visualization
    scale_sigma = 0.0001
    scale_axial = 0.0001
    scale_moment_y = 0.0001
    scale_moment_z = 0.0001

    curves = []
    materials = []
    texts = []

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
        # moment of inertia, 32.9376 cm⁴
        data.Iy = math.pi * (data.Do**4 - data.Di**4)/64 * 0.0001
        data.Iz = data.Iy

        # torsional constant, 65.875 cm⁴
        data.J  = math.pi * (data.Do**4 - data.Di**4)/(32) * 0.0001

        # cross-sectional area, 8,64 cm²
        data.A  = ((math.pi * (data.Do*0.5)**2) - (math.pi * (data.Di*0.5)**2)) * 0.01

        # weight of profile, 6.79 kg/m
        data.kg =  data.A*data.d * 0.1


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


class CustomProperties(PropertyGroup):
    Do: FloatProperty(
        name = "Do",
        description = "Diameter of pipe outside in mm",
        default = 60.0,
        min = 1.0,
        max = 1000.0
        )

    Di: FloatProperty(
        name = "Di",
        description = "Diameter of pipe inside in mm. Needs to be smaller than Diameter outside",
        default = 50.0,
        min = 1.0,
        max = 1000.
        )

    E: FloatProperty(
        name = "E",
        description = "Elasticity modulus in kN/cm²",
        default = 21000,
        min = 15000,
        max = 50000
        )

    G: FloatProperty(
        name = "G",
        description = "Shear modulus kN/cm²",
        default = 8100,
        min = 10000,
        max = 30000
        )

    d: FloatProperty(
        name = "d",
        description = "Density in g/cm3",
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
                ("sigma", "Sigma", ""),
                ("axial", "Axial", ""),
                ("moment_y", "Moment Y", ""),
                ("moment_z", "Moment Z", "")
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
        x = vertex.co[0] * 100 # convert to cm for calculation
        y = vertex.co[1] * 100 # convert to cm for calculation
        z = vertex.co[2] * 100 # convert to cm for calculation

        truss.add_node(name, x,y,z)

    # define support
    for support_id in data.support_ids:
        name = "node_" + str(support_id)

        # first node is fixed
        if data.support_ids.index(support_id) == 0:
            truss.def_support(name, True, True, True, True, True, True)

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
        kN = data.kg * -0.00981

        # add distributed load
        truss.add_member_dist_load(name, "FZ", kN, kN)

    # analyze the model
    truss.analyze(check_statics=False, sparse=False)

    # append result_max_axials
    result_axial = []
    result_moment_y = []
    result_moment_z = []
    result_shear_y = []
    result_shear_z = []
    result_torque = []
    result_sigma = []

    result_deflection = []

    # get forces
    for member in members:
        L = truss.Members[member].L() # Member length
        T = truss.Members[member].T() # Member local transformation matrix

        axial_member = []
        for i in range(10): # get the forces at 9 positions and
            axial_member_pos = truss.Members[member].axial(x=L/9*i)
            axial_member.append(axial_member_pos)

        moment_y_member = []
        for i in range(10): # get the forces at 9 positions and
            moment_y_member_pos = truss.Members[member].moment("My", x=L/9*i)
            moment_y_member.append(moment_y_member_pos)

        moment_z_member = []
        for i in range(10): # get the forces at 9 positions and
            moment_z_member_pos = truss.Members[member].moment("Mz", x=L/9*i)
            moment_z_member.append(moment_z_member_pos)

        shear_y_member = []
        for i in range(10): # get the forces at 9 positions and
            shear_y_member_pos = truss.Members[member].shear("Fy", x=L/9*i)
            shear_y_member.append(shear_y_member_pos)

        shear_z_member = []
        for i in range(10): # get the forces at 9 positions and
            shear_z_member_pos = truss.Members[member].shear("Fz", x=L/9*i)
            shear_z_member.append(shear_z_member_pos)

        torque_member = []
        for i in range(10): # get the forces at 9 positions and
            torque_member_pos = truss.Members[member].torque(x=L/9*i)
            torque_member.append(torque_member_pos)

        result_axial.append(axial_member)
        result_moment_y.append(moment_y_member)
        result_moment_z.append(moment_z_member)
        result_shear_y.append(shear_y_member)
        result_shear_z.append(shear_z_member)
        result_torque.append(torque_member)

        # modulus from the moments of area
        #(Wy and Wz are the same within a pipe)
        data.Wy = data.Iy/(data.Do/2)

        # polar modulus of torsion
        data.WJ = data.J/(data.Do/2)

        # calculation of the longitudinal stresses
        longitudinal_stress_member = []
        for i in range(10): # get the stresses at 9 positions and
            moment_h = math.sqrt(moment_y_member[i]**2+moment_z_member[i]**2)
            if axial_member[i] > 0:
                s = axial_member[i]/data.A + moment_h/data.Wy
            else:
                s = axial_member[i]/data.A - moment_h/data.Wy
            longitudinal_stress_member.append(s)

        # get max stress of the beam
        # (can be positive or negative)
        longitudinal_stress = return_max_diff_to_zero(longitudinal_stress_member) #  -> is working as fitness

        # calculation of the shear stresses from shear force
        # (always positive)
        tau_shear_member = []
        for i in range(10): # get the stresses at 9 positions and
            shear_h = math.sqrt(shear_y_member[i]**2+shear_z_member[i]**2)
            tau = 1.333 * shear_h/data.A # for pipes
            tau_shear_member.append(tau)

        # get max shear stress of shear force of the beam
        # shear stress is mostly small compared to longitudinal
        # in common architectural usage and only importand with short beam lenght
        tau_shear = max(tau_shear_member)

        # Calculation of the torsion stresses
        # (always positiv)
        tau_torsion_member = []
        for i in range(10): # get the stresses at 9 positions and
            tau = abs(torque_member[i]/data.WJ)
            tau_torsion_member.append(tau)

        # get max torsion stress of the beam
        tau_torsion = max(tau_torsion_member)
        # torsion stress is mostly small compared to longitudinal
        # in common architectural usage

        # calculation of the shear stresses form shear force and torsion
        # (always positiv)
        sum_tau_member = []
        for i in range(10): # get the stresses at 9 positions and
            tau = tau_shear_member[0] + tau_torsion_member[0]
            sum_tau_member.append(tau)

        sum_tau = max(sum_tau_member)

        # combine shear and torque
        sigmav_member = []
        for i in range(10): # get the stresses at 9 positions and
            sv = math.sqrt(longitudinal_stress_member[0]**2 + 3*sum_tau_member[0]**2)
            sigmav_member.append(sv)

        sigmav = max(sigmav_member)
        # check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

        # for the definition of the fitness criteria prepared
        # max longitudinal stress for steel St360 in kN/cm²
        # tensile strength: 36 kN/cm², yield point 23.5 kN/cm²
        # sigma_max = 14.0
        # tau_shear_max = 9.5
        # tau_torsion_max = 10.5
        # simgav_max = 23.5

        result_sigma.append(longitudinal_stress_member)

        # deflection
        deflection = []

        # --> taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite
        scale_factor = 0.1

        cos_x = array([T[0,0:3]]) # Direction cosines of local x-axis
        cos_y = array([T[1,0:3]]) # Direction cosines of local y-axis
        cos_z = array([T[2,0:3]]) # Direction cosines of local z-axis

        DY_plot = empty((0, 3))
        for i in range(10):
            # Calculate the local y-direction displacement
            dy_tot = truss.Members[member].deflection('dy', L/9*i)

            # Calculate the scaled displacement in global coordinates
            DY_plot = append(DY_plot, dy_tot*cos_y*scale_factor, axis=0)

        # Calculate the local z-axis displacements at 20 points along the member's length
        DZ_plot = empty((0, 3))
        for i in range(10):

            # Calculate the local z-direction displacement
            dz_tot = truss.Members[member].deflection('dz', L/9*i)

            # Calculate the scaled displacement in global coordinates
            DZ_plot = append(DZ_plot, dz_tot*cos_z*scale_factor, axis=0)

        # Calculate the local x-axis displacements at 20 points along the member's length
        DX_plot = empty((0, 3))

        Xi = truss.Members[member].i_node.X
        Yi = truss.Members[member].i_node.Y
        Zi = truss.Members[member].i_node.Z

        for i in range(10):
            # Displacements in local coordinates
            dx_tot = [[Xi, Yi, Zi]] + (L/9*i + truss.Members[member].deflection('dx', L/9*i)*scale_factor)*cos_x

            # Magnified displacements in global coordinates
            DX_plot = append(DX_plot, dx_tot, axis=0)

        # Sum the component displacements to obtain overall displacement
        D_plot = DY_plot + DZ_plot + DX_plot

        # <-- taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite

        # add to results
        for i in range(10):
            x = D_plot[i, 0] * 0.01
            y = D_plot[i, 1] * 0.01
            z = D_plot[i, 2] * 0.01

            deflection.append([x,y,z])

        result_deflection.append(deflection)


    # save as current frame
    frame = bpy.context.scene.frame_current

    data.result_axial[frame] = result_axial
    data.result_moment_y[frame] = result_moment_y
    data.result_moment_z[frame] = result_moment_z
    data.result_shear_y[frame] = result_shear_y
    data.result_shear_z[frame] = result_shear_z
    data.result_torque[frame] = result_torque
    data.result_sigma[frame] = result_sigma

    data.result_deflection[frame] = result_deflection


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
        if data.force_type_viz == "sigma":
            result = data.result_axial

        if data.force_type_viz == "axial":
            result = data.result_axial

        elif data.force_type_viz == "moment_y":
            result = data.result_moment_y

        elif data.force_type_viz == "moment_z":
            result = data.result_moment_z

        else:
            pass

        # get fitness
        forces = []
        for member in result[frame]:
            for i in range(10): # get the fitness at 9 positions and
                force = member[i]
                forces.append(force)

        fitness = return_max_diff_to_zero(forces)
        fitness = abs(fitness)
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
    for member_id, deflection in enumerate(data.result_deflection[frame]):
        sigma = return_max_diff_to_zero(data.result_sigma[frame][member_id])
        # set color
        if sigma > 0:
            r,g,b = 1,0,0
        else:
            r,g,b = 0,0,1

        # create name
        name = "<Phaenotyp>member_" + str(member_id)

        # create the Curve Datablock
        curve = bpy.data.curves.new(name, type="CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2

        # add points
        polyline = curve.splines.new("POLY")

        vertex_0_id = data.edges[member_id].vertices[0]
        vertex_1_id = data.edges[member_id].vertices[1]

        vertex_0_co = data.vertices[vertex_0_id].co
        vertex_1_co = data.vertices[vertex_1_id].co

        polyline.points.add(9)

        for point_id, position in enumerate(deflection):
            x = position[0]
            y = position[1]
            z = position[2]
            polyline.points[point_id].co = (x,y,z, 1)

            radius = data.result_sigma[frame][member_id][point_id]
            polyline.points[point_id].radius = abs(radius)

        # create Object
        obj = bpy.data.objects.new(name, curve)
        curve.bevel_depth = data.scale_sigma

        # link object to collection
        bpy.data.collections["<Phaenotyp>"].objects.link(obj)

        # new material
        name = "<Phaenotyp>member_" + str(member_id)
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


    # deselect, because last curve would be selected
    bpy.ops.object.select_all(action="DESELECT")

    data.done = True


def update_curves():
    frame = bpy.context.scene.frame_current

    for id, obj in enumerate(data.curves):
        # get forcetyp and force
        if data.force_type_viz == "sigma":
            result = data.result_sigma
            scale = data.scale_sigma

        if data.force_type_viz == "axial":
            result = data.result_axial
            scale = data.scale_axial

        elif data.force_type_viz == "moment_y":
            result = data.result_moment_y
            scale = data.scale_moment_y

        elif data.force_type_viz == "moment_z":
            result = data.result_moment_z
            scale = data.scale_moment_z

        else:
            pass


        # get curve from curve-obj
        curve_name = obj.data.name
        curve = bpy.data.curves[curve_name]
        curve.bevel_depth = scale

        # get highest force of this forcetype
        force = return_max_diff_to_zero(result[frame][id])

        # set color
        if force > 0:
            r,g,b = 1,0,0
        else:
            r,g,b = 0,0,1

        mat = data.materials[id]
        mat.diffuse_color = (r,g,b,1)

        # change position and radius
        for point_id, position in enumerate(data.result_deflection[frame][id]):
            x = position[0]
            y = position[1]
            z = position[2]
            curve.splines[0].points[point_id].co = (x,y,z, 1)

            radius = result[frame][id][point_id]
            curve.splines[0].points[point_id].radius = abs(radius)


def create_texts():
    delete_texts()

    frame = bpy.context.scene.frame_current

    # draw curves
    for member_id, edge in enumerate(data.edges):
        vertex_0_id = data.edges[member_id].vertices[0]
        vertex_1_id = data.edges[member_id].vertices[1]

        vertex_0 = data.vertices[vertex_0_id]
        vertex_1 = data.vertices[vertex_1_id]

        mid = (vertex_0.co + vertex_1.co)*0.5

        name = "<Phaenotyp>text_" + str(member_id)

        text = "member: " + str(member_id) + "\n"
        text = text + "\n"

        text = text + "axial: " + str(data.result_axial[frame][member_id]) + "\n"
        text = text + "\n"

        text = text + "moment_y: " + str(data.result_moment_y[frame][member_id]) + "\n"
        text = text + "moment_z: " + str(data.result_moment_z[frame][member_id]) + "\n"
        text = text + "\n"

        text = text + "shear_y: " + str(data.result_shear_y[frame][member_id]) + "\n"
        text = text + "shear_z: " + str(data.result_shear_z[frame][member_id]) + "\n"
        text = text + "\n"

        text = text + "torque: " + str(data.result_torque[frame][member_id]) + "\n"
        text = text + "sigma: " + str(data.result_sigma[frame][member_id]) + "\n"

        # create the Font Datablock
        curve = bpy.data.curves.new(type="FONT", name=name)
        curve.body = text
        obj = bpy.data.objects.new(name=name, object_data=curve)

        # set position
        obj.location = mid

        # set size
        obj.scale = [0.05, 0.05, 0.05]

        # link object to collection
        bpy.data.collections["<Phaenotyp>"].objects.link(obj)

        # save to data
        data.texts.append(obj)


def delete_texts():
    if len(data.texts) > 0:
        for text in bpy.data.texts:
            if "<Phaenotyp>" in obj.name_full:
                bpy.data.text.remove(text)

def reset_data():
    data.curves = []
    data.materials = []
    data.texts = []

    data.shape_keys = []
    data.population = []
    data.new_generation = []
    data.generation_id = 1
    data.chromosome = {}
    data.ga_state = "create initial population"


def reset_collection_geometry_material():
    # reset scene

    for collection in bpy.data.collections:
        if "<Phaenotyp>" in collection.name_full:
            bpy.data.collections.remove(collection)

    for material in bpy.data.materials:
        if "<Phaenotyp>" in material.name_full:
            bpy.data.materials.remove(material)

    for obj in bpy.data.objects:
        if "<Phaenotyp>" in obj.name_full:
            bpy.data.objects.remove(obj)

    for curve in bpy.data.curves:
        if "<Phaenotyp>" in obj.name_full:
            bpy.data.curves.remove(curve)

    for text in bpy.data.texts:
        if "<Phaenotyp>" in obj.name_full:
            bpy.data.text.remove(text)

    collection = bpy.data.collections.new("<Phaenotyp>")
    bpy.context.scene.collection.children.link(collection)


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
        if data.force_type_viz == "sigma":
            data.scale_sigma = data.scale_sigma * 1.25

        if data.force_type_viz == "axial":
            data.scale_axial = data.scale_axial * 1.25

        elif data.force_type_viz == "moment_y":
            data.scale_moment_y = data.scale_moment_y * 1.25

        elif data.force_type_viz == "moment_z":
            data.scale_moment_z = data.scale_moment_z * 1.25

        else:
            pass

        update_curves()

        return {"FINISHED"}


class WM_OT_viz_scale_down(Operator):
    bl_label = "viz_scale_down"
    bl_idname = "wm.viz_scale_down"

    def execute(self, context):
        # get forcetyp and force
        if data.force_type_viz == "sigma":
            data.scale_sigma = data.scale_sigma * 0.75

        if data.force_type_viz == "axial":
            data.scale_axial = data.scale_axial * 0.75

        elif data.force_type_viz == "moment_y":
            data.scale_moment_y = data.scale_moment_y * 0.75

        elif data.force_type_viz == "moment_z":
            data.scale_moment_z = data.scale_moment_z * 0.75

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


class WM_OT_text(Operator):
    bl_label = "text"
    bl_idname = "wm.text"

    def execute(self, context):
        delete_texts()
        create_texts()

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
    bl_label = "Phänotyp 0.0.3(test mit Karl)"
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

        # define material and geometry
        box = layout.box()
        box.label(text="Setup:")

        box.prop(phaenotyp, "Do", text="Diameter outside")
        box.prop(phaenotyp, "Di", text="Diameter inside")
        box.prop(phaenotyp, "E", text="Modulus of elasticity")
        box.prop(phaenotyp, "G", text="Shear modulus")
        box.prop(phaenotyp, "d", text="Density")

        data.Do = phaenotyp.Do
        data.Di = phaenotyp.Di

        data.E = phaenotyp.E
        data.G = phaenotyp.G
        data.d = phaenotyp.d

        data.update() # calculate Iy, Iz, J, A, kg
        box.label(text="Iy = " + str(round(data.Iy, 2)) + " cm⁴")
        box.label(text="Iz = " + str(round(data.Iz, 2)) + " cm⁴")
        box.label(text="J = " + str(round(data.J, 2)) + " cm⁴")
        box.label(text="A = " + str(round(data.A, 2)) + " cm²")
        box.label(text="kg = " + str(round(data.kg, 2)) + " kg/m")

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

                    # Text
                    box = layout.box()
                    box.label(text="Text:")
                    box.operator("wm.text", text="generate")

        box = layout.box()
        box.operator("wm.reset", text="Reset")


classes = (
    CustomProperties,

    WM_OT_set_structure,
    WM_OT_set_support,
    WM_OT_calculate_single_frame,
    WM_OT_calculate_animation,
    WM_OT_genetic_mutation,

    WM_OT_viz_scale_up,
    WM_OT_viz_scale_down,
    WM_OT_viz_update,

    WM_OT_text,

    WM_OT_reset,
    OBJECT_PT_CustomPanel
)


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


@persistent
def update_post(scene):
    delete_texts()
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


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.phaenotyp = PointerProperty(type=CustomProperties)
    draw_handler = bpy.types.SpaceView3D.draw_handler_add(draw, (), "WINDOW", "POST_VIEW")
    bpy.app.handlers.frame_change_post.append(update_post)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.phaenotyp
    bpy.app.handlers.frame_change_post.remove(update_post)


if __name__ == "__main__":
    register()
