
bl_info = {
    "name": "Phänotyp",
    "description": "Genetic optimization of architectural structures",
    "author": "bewegende Architektur e.U. and Karl Deix",
    "version": (0, 0, 4),
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

from bpy.props import (IntProperty, FloatProperty, BoolProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)
from bpy.app.handlers import persistent

import math
from threading import Thread
import random

import sys
import os

from PyNite import FEModel3D

from numpy import array
from numpy import empty
from numpy import append

from mathutils import Color
c = Color()


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

    # pass support types
    loc_x = None
    loc_y = None
    loc_z = None
    rot_x = None
    rot_y = None
    rot_z = None

    # store geoemtry
    obj = None
    mesh = None
    vertices = None
    edges = None
    texts = []

    # visualization
    force_type_viz = "sigma"

    scale_sigma = 0.5
    scale_axial = 0.5
    scale_moment_y = 0.5
    scale_moment_z = 0.5
    scale_deflection = 0.5

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


class supports:
    instances = []

    definend_vertex_ids = []

    def __init__(self, id, vertex):
        self.id = id # equals id of vertex
        supports.definend_vertex_ids.append(id)

        self.vertex = vertex
        self.x = vertex.co[0]
        self.y = vertex.co[1]
        self.z = vertex.co[2]

        self.sign = None

        supports.instances.append(self)

    def __del__(self):
        pass

    def update_settings(self):
        self.loc_x = data.loc_x
        self.loc_y = data.loc_y
        self.loc_z = data.loc_z
        self.rot_x = data.rot_x
        self.rot_y = data.rot_y
        self.rot_z = data.rot_z

    def create_sign(self):
        mesh = bpy.data.meshes.new("<Phaenotyp>support>")
        obj = bpy.data.objects.new(mesh.name, mesh)
        col = bpy.data.collections.get("<Phaenotyp>")
        col.objects.link(obj)
        bpy.context.view_layer.objects.active = obj

        name = "<Phaenotyp>support_" + str(self.id)
        curve = bpy.data.curves.new(name, type="CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2

        # pyramide
        polyline = curve.splines.new("POLY")
        polyline.points.add(4)
        polyline.points[0].co = -1, 1,-1, 1
        polyline.points[1].co =  1, 1,-1, 1
        polyline.points[2].co =  1,-1,-1, 1
        polyline.points[3].co = -1,-1,-1, 1
        polyline.points[4].co = -1, 1,-1, 1

        polyline = curve.splines.new("POLY")
        polyline.points.add(1)
        polyline.points[0].co = -1, 1, -1, 1
        polyline.points[1].co =  0, 0, 0, 1

        polyline = curve.splines.new("POLY")
        polyline.points.add(1)
        polyline.points[0].co =  1, 1,-1, 1
        polyline.points[1].co =  0, 0, 0, 1

        polyline = curve.splines.new("POLY")
        polyline.points.add(1)
        polyline.points[0].co =  1,-1,-1, 1
        polyline.points[1].co =  0, 0, 0, 1

        polyline = curve.splines.new("POLY")
        polyline.points.add(1)
        polyline.points[0].co = -1,-1,-1, 1
        polyline.points[1].co =  0, 0, 0, 1

        lx = 1 if self.loc_x == True else 0
        polyline = curve.splines.new("POLY")
        polyline.points.add(1)
        polyline.points[0].co =  0*lx, 0,-2*lx, 1
        polyline.points[1].co =  2*lx, 0,-2*lx, 1

        ly = 1 if self.loc_y == True else 0
        polyline = curve.splines.new("POLY")
        polyline.points.add(1)
        polyline.points[0].co =  0, 0*ly,-2*ly, 1
        polyline.points[1].co =  0, 2*ly,-2*ly, 1

        lz = 1 if self.loc_z == True else 0
        polyline = curve.splines.new("POLY")
        polyline.points.add(1)
        polyline.points[0].co =  0, 0,-2*lz, 1
        polyline.points[1].co =  0, 0,-4*lz, 1

        rx = 1 if self.rot_x == True else 0
        polyline = curve.splines.new("POLY")
        polyline.points.add(4)
        polyline.points[0].co =  2.0*rx, 0.2*rx,-2.2*rx, 1
        polyline.points[1].co =  2.0*rx,-0.2*rx,-2.2*rx, 1
        polyline.points[2].co =  2.0*rx,-0.2*rx,-1.8*rx, 1
        polyline.points[3].co =  2.0*rx, 0.2*rx,-1.8*rx, 1
        polyline.points[4].co =  2.0*rx, 0.2*rx,-2.2*rx, 1

        ry = 1 if self.rot_y == True else 0
        polyline = curve.splines.new("POLY")
        polyline.points.add(4)
        polyline.points[0].co =  0.2*ry, 2.0*ry,-2.2*ry, 1
        polyline.points[1].co = -0.2*ry, 2.0*ry,-2.2*ry, 1
        polyline.points[2].co = -0.2*ry, 2.0*ry,-1.8*ry, 1
        polyline.points[3].co =  0.2*ry, 2.0*ry,-1.8*ry, 1
        polyline.points[4].co =  0.2*ry, 2.0*ry,-2.2*ry, 1

        rz = 1 if self.rot_z == True else 0
        polyline = curve.splines.new("POLY")
        polyline.points.add(4)
        polyline.points[0].co =  0.2*rz, 0.2*rz,-4.0*rz, 1
        polyline.points[1].co = -0.2*rz, 0.2*rz,-4.0*rz, 1
        polyline.points[2].co = -0.2*rz,-0.2*rz,-4.0*rz, 1
        polyline.points[3].co =  0.2*rz,-0.2*rz,-4.0*rz, 1
        polyline.points[4].co =  0.2*rz, 0.2*rz,-4.0*rz, 1

        # create Object
        obj = bpy.data.objects.new(name, curve)
        obj.location = self.x, self.y, self.z
        obj.scale = 0.25, 0.25, 0.25

        self.sign = obj

        # link object to collection
        bpy.data.collections["<Phaenotyp>"].objects.link(obj)

    def update_sign(self):
        curve = bpy.data.curves[self.sign.name_full]

        lx = 1 if self.loc_x == True else 0
        polyline = curve.splines[5]
        polyline.points[0].co =  0*lx, 0,-2*lx, 1
        polyline.points[1].co =  2*lx, 0,-2*lx, 1

        ly = 1 if self.loc_y == True else 0
        polyline = curve.splines[6]
        polyline.points[0].co =  0, 0*ly,-2*ly, 1
        polyline.points[1].co =  0, 2*ly,-2*ly, 1

        lz = 1 if self.loc_z == True else 0
        polyline = curve.splines[7]
        polyline.points[0].co =  0, 0,-2*lz, 1
        polyline.points[1].co =  0, 0,-4*lz, 1

        rx = 1 if self.rot_x == True else 0
        polyline = curve.splines[8]
        polyline.points[0].co =  2.0*rx, 0.2*rx,-2.2*rx, 1
        polyline.points[1].co =  2.0*rx,-0.2*rx,-2.2*rx, 1
        polyline.points[2].co =  2.0*rx,-0.2*rx,-1.8*rx, 1
        polyline.points[3].co =  2.0*rx, 0.2*rx,-1.8*rx, 1
        polyline.points[4].co =  2.0*rx, 0.2*rx,-2.2*rx, 1

        ry = 1 if self.rot_y == True else 0
        polyline = curve.splines[9]
        polyline.points[0].co =  0.2*ry, 2.0*ry,-2.2*ry, 1
        polyline.points[1].co = -0.2*ry, 2.0*ry,-2.2*ry, 1
        polyline.points[2].co = -0.2*ry, 2.0*ry,-1.8*ry, 1
        polyline.points[3].co =  0.2*ry, 2.0*ry,-1.8*ry, 1
        polyline.points[4].co =  0.2*ry, 2.0*ry,-2.2*ry, 1

        rz = 1 if self.rot_z == True else 0
        polyline = curve.splines[10]
        polyline.points[0].co =  0.2*rz, 0.2*rz,-4.0*rz, 1
        polyline.points[1].co = -0.2*rz, 0.2*rz,-4.0*rz, 1
        polyline.points[2].co = -0.2*rz,-0.2*rz,-4.0*rz, 1
        polyline.points[3].co =  0.2*rz,-0.2*rz,-4.0*rz, 1
        polyline.points[4].co =  0.2*rz, 0.2*rz,-4.0*rz, 1

    @staticmethod
    def get_by_id(id):
        for support in supports.instances:
            if support.id == id:
                return support


class members:
    instances = []

    # to keep track of allready definend edges
    definend_edge_ids = []
    all_edges_definend = False

    def __init__(self, id, vertex_0, vertex_1):
        self.id = id # equals id of edge
        self.name = "member_" + str(id)
        members.definend_edge_ids.append(id)

        self.vertex_0 = vertex_0
        self.vertex_1 = vertex_1

        # geometry
        self.curve = None
        self.mat = None
        self.initial_positions = {}
        self.create_curve(id, vertex_0, vertex_1)

        members.instances.append(self)

    def __del__(self):
        pass

    def update_settings(self):
        self.Do = data.Do * 0.1
        self.Di = data.Di * 0.1
        self.E  = data.E
        self.G  = data.G
        self.d  = data.d
        self.Iy = data.Iy
        self.Iz = data.Iz
        self.J  = data.J
        self.A  = data.A
        self.kg = data.kg

        # results
        self.axial = {}
        self.moment_y = {}
        self.moment_z = {}
        self.shear_y = {}
        self.shear_z = {}
        self.torque = {}
        self.sigma = {}

        self.Wy = None
        self.WJ = None

        self.longitudinal_stress = {}
        self.tau_shear = {}
        self.tau_torsion = {}
        self.sum_tau = {}
        self.sigmav = {}
        self.sigma = {}

        self.max_longitudinal_stress = {}
        self.max_tau_shear = {}
        self.max_tau_torsion = {}
        self.max_sum_tau = {}
        self.max_sigmav = {}
        self.max_sigma = {}

        self.deflection = {}

        self.overstress = {}

        self.curve.bevel_depth = self.Do*0.01

    def create_curve(self, id, vertex_0, vertex_1):
        name = "<Phaenotyp>member_" + str(id)
        vertex_0_co = vertex_0.co
        vertex_1_co = vertex_1.co

        # create the Curve Datablock
        curve = bpy.data.curves.new(name, type="CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2

        # add points
        polyline = curve.splines.new("POLY")
        polyline.points.add(10)

        for i in range(11):
            position = (vertex_0_co*(i) + vertex_1_co*(10-i))*0.1
            x = position[0]
            y = position[1]
            z = position[2]
            polyline.points[i].co = (x,y,z, 1)

        # create Object
        obj = bpy.data.objects.new(name, curve)

        # link object to collection
        bpy.data.collections["<Phaenotyp>"].objects.link(obj)

        # create material
        name = "<Phaenotyp>member_" + str(id)
        mat = bpy.data.materials.new(name)
        obj.data.materials.append(mat)
        obj.active_material_index = len(obj.data.materials) - 1

        mat.use_nodes = True
        nodetree = mat.node_tree

        # add Color Ramp and link to Base Color
        nodetree.nodes.new(type="ShaderNodeValToRGB")
        input = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']
        output = mat.node_tree.nodes['ColorRamp'].outputs['Color']
        nodetree.links.new(input, output)

        # add xyz and link to Color Ramp
        nodetree.nodes.new(type="ShaderNodeSeparateXYZ")
        input = mat.node_tree.nodes['ColorRamp'].inputs['Fac']
        output = mat.node_tree.nodes['Separate XYZ'].outputs['X']
        nodetree.links.new(input, output)

        # add coordinate and link to xyz
        nodetree.nodes.new(type="ShaderNodeTexCoord")
        input = mat.node_tree.nodes['Separate XYZ'].inputs['Vector']
        output =  mat.node_tree.nodes['Texture Coordinate'].outputs['UV']
        nodetree.links.new(input, output)

        # add a new ramp in the middle, position = 0.5
        color_ramp = mat.node_tree.nodes['ColorRamp'].color_ramp

        # add nine further positons (two existing)
        for i in range(1, 10):
            position = i*0.1
            color_ramp.elements.new(position = position)

        # change color for eleven points
        from mathutils import Color
        c = Color()

        for i in range(11):
            h = 0
            s = 0
            v = 1
            c.hsv = h,s,v
            color_ramp.elements[i].color = c.r, c.g, c.b, 1.0

        self.curve = curve
        self.mat = mat


    def update_curve(self):
        frame = bpy.context.scene.frame_current

        # apply deflection
        polyline = self.curve.splines[0]
        for i in range(11):
            position = self.deflection[frame][i]
            f = data.scale_deflection
            x = position[0]*(1-f) + self.initial_positions[frame][10-i][0]*f
            y = position[1]*(1-f) + self.initial_positions[frame][10-i][1]*f
            z = position[2]*(1-f) + self.initial_positions[frame][10-i][2]*f
            polyline.points[i].co = (x,y,z, 1)

        # change color for eleven points
        self.mat.use_nodes = True
        nodetree = self.mat.node_tree

        # get forcetyp and force
        if data.force_type_viz == "sigma":
            result = self.sigma
            scale = data.scale_sigma

        if data.force_type_viz == "axial":
            result = self.axial
            scale = data.scale_axial

        if data.force_type_viz == "moment_y":
            result = self.moment_y
            scale = data.scale_moment_y

        if data.force_type_viz == "moment_z":
            result = self.moment_z
            scale = data.scale_moment_z

        color_ramp = self.mat.node_tree.nodes['ColorRamp'].color_ramp

        for i in range(11):
            # define h
            if result[frame][i] > 0:
                h = 0
            else:
                h = 0.666

            # define s
            s = 1 * scale

            # define v
            if self.overstress[frame] == True:
                v = 0.2
            else:
                v = 1.0

            c.hsv = h,s,v
            color_ramp.elements[i].color = c.r, c.g, c.b, 1.0

    @staticmethod
    def get_by_id(id):
        for member in members.instances:
            if member.id == id:
                return member

    @staticmethod
    def update_curves():
        for member in members.instances:
            member.update_curve()


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


class phaenotyp_properties(PropertyGroup):
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

    loc_x: BoolProperty(
        name='loc_x',
        default=True
    )

    loc_y: BoolProperty(
        name='loc_y',
        default=True
    )

    loc_z: BoolProperty(
        name='loc_z',
        default=True
    )

    rot_x: BoolProperty(
        name='rot_x',
        default=False
    )

    rot_y: BoolProperty(
        name='rot_y',
        default=False
    )

    rot_z: BoolProperty(
        name='rot_z',
        default=False
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
    data.edges = data.mesh.edges


def transfer_analyze():
    # get current frame
    frame = bpy.context.scene.frame_current

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
    for support in supports.instances:
        name = "node_" + str(support.id)
        truss.def_support(name, support.loc_x, support.loc_y, support.loc_z, support.rot_x, support.rot_y, support.rot_z)

    # create members
    for member in members.instances:
        name = member.name
        vertex_0_id = member.vertex_0.index
        vertex_1_id = member.vertex_1.index

        # save initial_positions to mix with deflection
        initial_positions = []
        for i in range(11):
            position = (data.vertices[vertex_0_id].co*(i) + data.vertices[vertex_1_id].co*(10-i))*0.1
            x = position[0]
            y = position[1]
            z = position[2]
            initial_positions.append([x,y,z])
        member.initial_positions[frame] = initial_positions

        node_0 = str("node_") + str(vertex_0_id)
        node_1 = str("node_") + str(vertex_1_id)

        truss.add_member(name, node_0, node_1, member.E, member.G, member.Iy, member.Iz, member.J, member.A)

        # add gravity
        kN = member.kg * -0.0000981

        # add distributed load
        truss.add_member_dist_load(name, "FZ", kN, kN)

    # analyze the model
    truss.analyze(check_statics=False, sparse=False)

    # get forces
    for member in members.instances:
        name = member.name
        L = truss.Members[name].L() # Member length
        T = truss.Members[name].T() # Member local transformation matrix

        axial = []
        for i in range(11): # get the forces at 11 positions and
            axial_pos = truss.Members[name].axial(x=L/10*i)
            axial.append(axial_pos)
        member.axial[frame] = axial

        moment_y = []
        for i in range(11): # get the forces at 11 positions and
            moment_y_pos = truss.Members[name].moment("My", x=L/10*i)
            moment_y.append(moment_y_pos)
        member.moment_y[frame] = moment_y

        moment_z = []
        for i in range(11): # get the forces at 11 positions and
            moment_z_pos = truss.Members[name].moment("Mz", x=L/10*i)
            moment_z.append(moment_z_pos)
        member.moment_z[frame] = moment_z

        shear_y = []
        for i in range(11): # get the forces at 11 positions and
            shear_y_pos = truss.Members[name].shear("Fy", x=L/10*i)
            shear_y.append(shear_y_pos)
        member.shear_y[frame] = shear_y

        shear_z = []
        for i in range(11): # get the forces at 11 positions and
            shear_z_pos = truss.Members[name].shear("Fz", x=L/10*i)
            shear_z.append(shear_z_pos)
        member.shear_z[frame] = shear_z

        torque = []
        for i in range(11): # get the forces at 11 positions and
            torque_pos = truss.Members[name].torque(x=L/10*i)
            torque.append(torque_pos)
        member.torque[frame] = torque


        # modulus from the moments of area
        #(Wy and Wz are the same within a pipe)
        member.Wy = member.Iy/(member.Do/2)

        # polar modulus of torsion
        member.WJ = member.J/(member.Do/2)

        # calculation of the longitudinal stresses
        longitudinal_stress = []
        for i in range(11): # get the stresses at 11 positions and
            moment_h = math.sqrt(moment_y[i]**2+moment_z[i]**2)
            if axial[i] > 0:
                s = axial[i]/member.A + moment_h/member.Wy
            else:
                s = axial[i]/member.A - moment_h/member.Wy
            longitudinal_stress.append(s)

        # get max stress of the beam
        # (can be positive or negative)
        member.longitudinal_stress[frame] = longitudinal_stress
        member.max_longitudinal_stress[frame] = return_max_diff_to_zero(longitudinal_stress) #  -> is working as fitness

        # calculation of the shear stresses from shear force
        # (always positive)
        tau_shear = []
        for i in range(11): # get the stresses at 11 positions and
            shear_h = math.sqrt(shear_y[i]**2+shear_z[i]**2)
            tau = 1.333 * shear_h/member.A # for pipes
            tau_shear.append(tau)

        # get max shear stress of shear force of the beam
        # shear stress is mostly small compared to longitudinal
        # in common architectural usage and only importand with short beam lenght
        member.tau_shear[frame] = max(tau_shear)
        member.max_tau_shear[frame] = max(tau_shear)

        # Calculation of the torsion stresses
        # (always positiv)
        tau_torsion = []
        for i in range(11): # get the stresses at 11 positions and
            tau = abs(torque[i]/member.WJ)
            tau_torsion.append(tau)

        # get max torsion stress of the beam
        member.tau_torsion[frame] = tau_torsion
        member.max_tau_torsion[frame] = max(tau_torsion)

        # torsion stress is mostly small compared to longitudinal
        # in common architectural usage

        # calculation of the shear stresses form shear force and torsion
        # (always positiv)
        sum_tau = []
        for i in range(11): # get the stresses at 11 positions and
            tau = tau_shear[0] + tau_torsion[0]
            sum_tau.append(tau)

        member.sum_tau[frame] = sum_tau
        member.max_sum_tau[frame] = max(sum_tau)

        # combine shear and torque
        sigmav = []
        for i in range(11): # get the stresses at 11 positions and
            sv = math.sqrt(longitudinal_stress[0]**2 + 3*sum_tau[0]**2)
            sigmav.append(sv)

        member.sigmav[frame] = sigmav
        member.max_sigmav[frame] = max(sigmav)
        # check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

        member.sigma = member.longitudinal_stress
        member.max_sigma = member.max_longitudinal_stress

        # for the definition of the fitness criteria prepared
        # max longitudinal stress for steel St360 in kN/cm²
        # tensile strength: 36 kN/cm², yield point 23.5 kN/cm²
        member.overstress[frame] = False

        if member.max_sigma[frame] > 14.0:
            member.overstress[frame] = True

        if member.max_tau_shear[frame] > 9.5:
            member.overstress[frame] = True

        if member.max_tau_torsion[frame] > 10.5:
            member.overstress[frame] = True

        if member.max_sigmav[frame] > 23.5:
            member.overstress[frame] = True

        # deflection
        deflection = []

        # --> taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite
        scale_factor = 10.0

        cos_x = array([T[0,0:3]]) # Direction cosines of local x-axis
        cos_y = array([T[1,0:3]]) # Direction cosines of local y-axis
        cos_z = array([T[2,0:3]]) # Direction cosines of local z-axis

        DY_plot = empty((0, 3))
        for i in range(11):
            # Calculate the local y-direction displacement
            dy_tot = truss.Members[name].deflection('dy', L/10*i)

            # Calculate the scaled displacement in global coordinates
            DY_plot = append(DY_plot, dy_tot*cos_y*scale_factor, axis=0)

        # Calculate the local z-axis displacements at 20 points along the member's length
        DZ_plot = empty((0, 3))
        for i in range(11):
            # Calculate the local z-direction displacement
            dz_tot = truss.Members[name].deflection('dz', L/10*i)

            # Calculate the scaled displacement in global coordinates
            DZ_plot = append(DZ_plot, dz_tot*cos_z*scale_factor, axis=0)

        # Calculate the local x-axis displacements at 20 points along the member's length
        DX_plot = empty((0, 3))

        Xi = truss.Members[name].i_node.X
        Yi = truss.Members[name].i_node.Y
        Zi = truss.Members[name].i_node.Z

        for i in range(11):
            # Displacements in local coordinates
            dx_tot = [[Xi, Yi, Zi]] + (L/10*i + truss.Members[name].deflection('dx', L/10*i)*scale_factor)*cos_x

            # Magnified displacements in global coordinates
            DX_plot = append(DX_plot, dx_tot, axis=0)

        # Sum the component displacements to obtain overall displacement
        D_plot = DY_plot + DZ_plot + DX_plot

        # <-- taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite

        # add to results
        for i in range(11):
            x = D_plot[i, 0] * 0.01
            y = D_plot[i, 1] * 0.01
            z = D_plot[i, 2] * 0.01

            deflection.append([x,y,z])


        member.deflection[frame] = deflection

    # change viewport to material
    bpy.context.space_data.shading.type = 'MATERIAL'
    data.done = True


# genetic algorithm
class individuals(object):
    instances = []
    best = None

    def __init__(self, chromosome):
        self.chromosome = chromosome
        self.fitness = self.cal_fitness()
        self.frame = bpy.context.scene.frame_current

        individuals.instances.append(self)

    @classmethod
    def mutated_genes(self):
        gene = random.choice(data.genes)
        return gene

    @classmethod
    def create_gnome(self):
        # create gnome from available shape keys
        gnome_len = len(data.shape_keys)-1 # to exlude basis
        chromosome = [self.mutated_genes() for _ in range(gnome_len)]

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
        '''
        child_chromosome = []
        for gene_id, gene in enumerate(self.chromosome):
            method = random.choice([0,1,2])
            if method == 0:
                mixed_gene = (gene + par2.chromosome[gene_id]) * 0.5
                child_chromosome.append(mixed_gene)

            if method == 1:
                child_chromosome.append(gene)

            if method == 2:
                child_chromosome.append(par2.chromosome[gene_id])
                '''

        frame = bpy.context.scene.frame_current
        return individuals(child_chromosome)

    def cal_fitness(self):
        # apply shape keys
        for id, key in enumerate(data.shape_keys):
            if id > 0: # to exlude basis
                key.value = self.chromosome[id-1]*0.1

        transfer_analyze()
        frame = bpy.context.scene.frame_current

        # get fitness
        forces = []
        for member in members.instances:
            force = member.max_sigma[frame]
            forces.append(force)

        #fitness = return_max_diff_to_zero(forces)
        #fitness = abs(fitness)

        # average
        sum_forces = 0
        for force in forces:
            sum_forces = sum_forces + abs(force)

        fitness = sum_forces / len(forces)

        return fitness


def genetic_mutation():
    frame = bpy.context.scene.frame_current

    if data.ga_state == "create initial population":
        if len(data.population) < data.population_size:
            # create chromosome with set of shapekeys
            chromosome = individuals.create_gnome()
            data.population.append(individuals(chromosome))
            data.chromosome[frame] = chromosome
            print("initial population append:", chromosome)

        else:
            data.ga_state = "create new generation"


    if data.ga_state == "create new generation":
        # sort previous population according to fitness
        data.population = sorted(data.population, key = lambda x:x.fitness)

        # print previous population to terminal
        print("sorted:")
        for id, gnome in enumerate(data.population):
            print(gnome.chromosome, "with fitness", gnome.fitness)
        print("")

        # for first run only
        if individuals.best == None:
            individuals.best = data.population[0]

        # replace overall best of all generations
        best = data.population[0]
        for individual in individuals.instances:
            if individual.fitness > best.fitness:
                individuals.best = best

        print("overall best individuals:")
        print(individuals.best.chromosome, "with fitness", individuals.best.fitness, "at frame", individuals.best.frame)
        print("")

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
    bl_label = "set_structure"
    bl_idname = "wm.set_structure"
    bl_description = "Please select an object in Object-Mode and press set"

    def execute(self, context):
        # create collection if it does not exist
        not_existing = True
        for collection in bpy.data.collections:
            if collection.name_full == "<Phaenotyp>":
                not_existing = False

        if not_existing:
            collection = bpy.data.collections.new("<Phaenotyp>")
            bpy.context.scene.collection.children.link(collection)

        data.obj = bpy.context.active_object
        bpy.ops.object.mode_set(mode="EDIT")

        # if user is changing the setup, the visualization is disabled
        data.done = False

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

            for id, vertex in enumerate(data.obj.data.vertices):
                if vertex.select:
                    # vertex is existing as support?
                    if id in supports.definend_vertex_ids:
                        # update parameters
                        support = supports.get_by_id(id)

                        # delete and create new sign
                        support.update_settings()
                        support.update_sign()

                    else:
                        # create new member and sign
                        new_support = supports(id, vertex)
                        new_support.update_settings()
                        new_support.create_sign()

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.mode_set(mode="EDIT")

        # if user is changing the setup, the visualization is disabled
        data.done = False

        return {"FINISHED"}


class WM_OT_set_profile(Operator):
    bl_label = "set_profile"
    bl_idname = "wm.set_profile"
    bl_description = "Please select edges in Edit-Mode and press set, to define profiles"

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")

        # create new member
        for id, edge in enumerate(data.obj.data.edges):
            vertex_0_id = edge.vertices[0]
            vertex_1_id = edge.vertices[1]

            vertex_0 = data.obj.data.vertices[vertex_0_id]
            vertex_1 = data.obj.data.vertices[vertex_1_id]

            if edge.select:
                # edge is existing as member?
                if id in members.definend_edge_ids:
                    # update parameters
                    member = members.get_by_id(id)
                    member.update_settings()

                else:
                    # create new member
                    new_member = members(id, vertex_0, vertex_1)
                    new_member.update_settings()

        # check if all members done
        if len(members.instances) == len(data.obj.data.edges):
            members.all_edges_definend = True

        # if user is changing the setup, the visualization is disabled
        data.done = False

        bpy.ops.object.mode_set(mode="EDIT")
        return {"FINISHED"}


class WM_OT_calculate_single_frame(Operator):
    bl_label = "calculate_single_frame"
    bl_idname = "wm.calculate_single_frame"
    bl_description = "Calulate single frame"

    def execute(self, context):
        transfer_analyze()
        members.update_curves()

        return {"FINISHED"}


class WM_OT_calculate_animation(Operator):
    bl_label = "calculate_animation"
    bl_idname = "wm.calculate_animation"
    bl_description = "Calulate animation"

    def execute(self, context):
        transfer_analyze()
        members.update_curves()

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
    bl_description = "Start genetic muation over selected shape keys"

    def execute(self, context):
        # shape keys
        shape_key = data.obj.data.shape_keys
        for keyblock in shape_key.key_blocks:
            data.shape_keys.append(keyblock)

        transfer_analyze()
        members.update_curves()

        # activate calculation in update_post
        data.genetetic_mutation_update_post = True

        # clear population
        data.population = []

        # set animation to first frame and start
        start = bpy.context.scene.frame_start
        bpy.context.scene.frame_current = start
        bpy.ops.screen.animation_play()

        return {"FINISHED"}


class WM_OT_viz_scale_force_up(Operator):
    bl_label = "viz_scale_force_up"
    bl_idname = "wm.viz_scale_force_up"
    bl_description = "Scale force"

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

        members.update_curves()

        return {"FINISHED"}


class WM_OT_viz_scale_force_down(Operator):
    bl_label = "viz_scale_force_down"
    bl_idname = "wm.viz_scale_force_down"
    bl_description = "Scale force"

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

        members.update_curves()

        return {"FINISHED"}

class WM_OT_viz_scale_deflection_up(Operator):
    bl_label = "viz_scale_deflection_up"
    bl_idname = "wm.viz_scale_deflection_up"
    bl_description = "Scale deflection"

    def execute(self, context):
        data.scale_deflection = data.scale_deflection + 0.1
        if data.scale_deflection > 1:
            data.scale_deflection = 1 # not bigger than one

        members.update_curves()

        return {"FINISHED"}


class WM_OT_viz_scale_deflection_down(Operator):
    bl_label = "viz_scale_deflection_down"
    bl_idname = "wm.viz_scale_deflection_down"
    bl_description = "Scale deflection"

    def execute(self, context):
        data.scale_deflection = data.scale_deflection - 0.1
        if data.scale_deflection < 0:
            data.scale_deflection = 0 # not smaller than zero

        members.update_curves()

        members.update_curves()

        return {"FINISHED"}

class WM_OT_viz_update(Operator):
    bl_label = "viz_update"
    bl_idname = "wm.viz_update"
    bl_description = "Update the force type"

    def execute(self, context):
        members.update_curves()

        return {"FINISHED"}


class WM_OT_text(Operator):
    bl_label = "text"
    bl_idname = "wm.text"
    bl_description = "Generate output at the selcted point"

    def execute(self, context):
        #try:
        data.texts = []
        selected_points = []
        curve = bpy.context.selected_objects[0]
        for point_id, point in enumerate(curve.data.splines[0].points):
            if point.select == True:
                selected_points.append(point_id)

        if len(selected_points) > 1:
            data.texts.append("Please select one point only")

        else:
            # get member id
            name = curve.name_full
            name_splited = name.split("_")
            member_id = int(name_splited[1])
            member = members.get_by_id(member_id)

            text = "Member: " + str(member.id)
            data.texts.append(text)

            # get Position
            position = selected_points[0]
            text = "Position: " + str(position)
            data.texts.append(text)

            # get frame
            frame = bpy.context.scene.frame_current

            # results
            text = "axial: " + str(member.axial[frame][position])
            data.texts.append(text)
            text = "moment_y: " + str(member.moment_y[frame][position])
            data.texts.append(text)
            text = "moment_z: " + str(member.moment_z[frame][position])
            data.texts.append(text)
            text = "shear_y: " + str(member.shear_y[frame][position])
            data.texts.append(text)
            text = "shear_z: " + str(member.shear_z[frame][position])
            data.texts.append(text)
            text = "torque: " + str(member.torque[frame][position])
            data.texts.append(text)

            text = "longitudinal_stress: " + str(member.longitudinal_stress[frame][position])
            data.texts.append(text)
            text = "tau_shear: " + str(member.tau_shear[frame])
            data.texts.append(text)
            text = "tau_torsion: " + str(member.tau_torsion[frame])
            data.texts.append(text)
            text = "sum_tau: " + str(member.sum_tau[frame])
            data.texts.append(text)
            text = "sigmav: " + str(member.sigmav[frame][position])
            data.texts.append(text)
            text = "sigma: " + str(member.sigma[frame][position])
            data.texts.append(text)

            text = "overstress: " + str(member.overstress[frame])
            data.texts.append(text)

        #except:
        #    data.texts.append("Please select one point within the profile")

        return {"FINISHED"}


class WM_OT_reset(Operator):
    bl_label = "reset"
    bl_idname = "wm.reset"
    bl_description = "Reset Phaenotyp"

    def execute(self, context):
        reset_collection_geometry_material()

        data.obj = None
        data.vertices = None
        data.edges = None
        data.done = None

        # reset members
        for member in members.instances:
            del member

        members.instances = []
        members.definend_edge_ids = []
        members.all_edges_definend = False

        # reset supports
        for support in supports.instances:
            del support

        supports.instances = []
        supports.definend_vertex_ids = []

        return {"FINISHED"}


class OBJECT_PT_Phaenotyp(Panel):
    bl_label = "Phänotyp 0.0.4"
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

        box = layout.box()
        box.label(text="Structure:")
        box.operator("wm.set_structure", text="Set")

        if data.obj:
            box.label(text = data.obj.name_full + " is defined as structure")

            # define support
            box = layout.box()
            box.label(text="Support:")

            col = box.column()
            split = col.split()
            split.prop(phaenotyp, "loc_x", text="loc x")
            split.prop(phaenotyp, "rot_x", text="rot x")

            col = box.column()
            split = col.split()
            split.prop(phaenotyp, "loc_y", text="loc y")
            split.prop(phaenotyp, "rot_y", text="rot y")

            col = box.column()
            split = col.split()
            split.prop(phaenotyp, "loc_z", text="loc z")
            split.prop(phaenotyp, "rot_z", text="rot z")

            box.operator("wm.set_support", text="Set")

            data.loc_x = phaenotyp.loc_x
            data.loc_y = phaenotyp.loc_y
            data.loc_z = phaenotyp.loc_z
            data.rot_x = phaenotyp.rot_x
            data.rot_y = phaenotyp.rot_y
            data.rot_z = phaenotyp.rot_z

            if len(supports.instances) > 0:
                box.label(text = str(len(supports.instances)) + " vertices defined as support")

                # define material and geometry
                box = layout.box()
                box.label(text="Profile:")

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

                box.operator("wm.set_profile", text="Set")

                if members.all_edges_definend:
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
                        col.operator("wm.viz_scale_force_up", text="Up")
                        col.operator("wm.viz_scale_force_down", text="Down")

                        box.label(text="Deflection:")
                        col = box.column_flow(columns=2, align=False)
                        col.operator("wm.viz_scale_deflection_up", text="Up")
                        col.operator("wm.viz_scale_deflection_down", text="Down")

                        # Text
                        box = layout.box()
                        box.label(text="Result:")
                        box.operator("wm.text", text="generate")

                        if len(data.texts) > 0:
                            for text in data.texts:
                                box.label(text=text)

        box = layout.box()
        box.operator("wm.reset", text="Reset")


classes = (
    phaenotyp_properties,
    WM_OT_set_structure,
    WM_OT_set_profile,
    WM_OT_set_support,
    WM_OT_calculate_single_frame,
    WM_OT_calculate_animation,
    WM_OT_genetic_mutation,

    WM_OT_viz_scale_force_up,
    WM_OT_viz_scale_force_down,
    WM_OT_viz_scale_deflection_up,
    WM_OT_viz_scale_deflection_down,
    WM_OT_viz_update,

    WM_OT_text,

    WM_OT_reset,
    OBJECT_PT_Phaenotyp
)


@persistent
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

    members.update_curves()


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.phaenotyp = PointerProperty(type=phaenotyp_properties)
    bpy.app.handlers.frame_change_post.append(update_post)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.phaenotyp
    bpy.app.handlers.frame_change_post.remove(update_post)


if __name__ == "__main__":
    register()
