bl_info = {
    "name": "Phänotyp",
    "description": "Genetic optimization of architectural structures",
    "author": "bewegende Architektur e.U. and Karl Deix",
    "version": (0, 1, 4),
    "blender": (3, 4, 1),
    "location": "3D View > Tools",
}


# With Support from Karl Deix
# Analysis with: https://github.com/JWock82/PyNite
# GA based on: https://www.geeksforgeeks.org/genetic-algorithms/

import bpy
from bpy.props import (IntProperty, FloatProperty, BoolProperty, StringProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)
from bpy.app.handlers import persistent

import os
import webbrowser

from phaenotyp import basics, material, geometry, calculation, ga, report, progress, panels
import itertools

def create_data():
    scene = bpy.context.scene
    data = scene.get("<Phaenotyp>")
    if not data:
        data = bpy.context.scene["<Phaenotyp>"] = {
            "structure":{},
            "supports":{},
            "members":{},
            "frames":{},
            "loads_v":{},
            "loads_e":{},
            "loads_f":{},
            "process":{},
            "done":{},
            "gui":{},
            "ga_environment":{},
            "ga_individuals":{},
            "texts":{}
        }

        data["structure"] = None
        data["supports"] = {}
        data["members"] = {}
        data["frames"] = {}
        data["loads_v"] = {}
        data["loads_e"] = {}
        data["loads_f"] = {}

        data["process"]["scipy_available"] = False
        data["gui"] = {}

        data["done"] = {}

        data["ga_environment"] = {}
        data["ga_individuals"] = {}

        data["texts"] = []

def print_data(text):
    print("Phaenotyp |", text)

def viz_update(self, context):
    scene = context.scene
    phaenotyp = scene.phaenotyp
    geometry.update_members_post()

class phaenotyp_properties(PropertyGroup):
    use_scipy: BoolProperty(
        name='use_scipy',
        description = "Scipy is available! Calculation will be much faster. Anyway: Try to uncheck if something is crashing.",
        default=True
    )

    calculation_type: EnumProperty(
        name="calculation_type:",
        description="Calculation types",
        items=[
                ("geometrical", "Geometrical", ""),
                ("first_order", "First order", ""),
                ("first_order_linear", "First order linear", ""),
                ("second_order", "Second order", "")
               ],
        default = "first_order",
        )

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

    material: EnumProperty(
        name="material:",
        description="Predefined materials",
        items=material.dropdown
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

    acceptable_sigma: FloatProperty(
        name = "acceptable_sigma",
        description = "Acceptable sigma",
        default = 16.0,
        min = 0.01,
        max = 30.0
        )

    acceptable_shear: FloatProperty(
        name = "acceptable_shear",
        description = "Acceptable shear",
        default = 9.5,
        min = 0.01,
        max = 30.0
        )

    acceptable_torsion: FloatProperty(
        name = "acceptable_torsion",
        description = "Acceptable torsion",
        default = 10.5,
        min = 0.01,
        max = 30.0
        )

    acceptable_sigmav: FloatProperty(
        name = "acceptable_sigmav",
        description = "Acceptable sigmav",
        default = 10.5,
        min = 23.5,
        max = 30.0
        )

    ir: StringProperty(
        name = "ir",
        description = "Ir of custom material",
        default = "16.5, 15.8, 15.3, 14.8, 14.2, 13.5, 12.7, 11.8, 10.7, 9.5, 8.2, 6.9, 5.9, 5.1, 4.4, 3.9, 3.4, 3.1, 2.7, 2.5, 2.2, 2.0, 1.9, 1.7, 1.6"
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

    load_type: EnumProperty(
        name="load_type:",
        description="Load types",
        items=[
                ("vertices", "Vertices", ""),
                ("edges", "Edges", ""),
                ("faces", "Faces", "")
               ]
        )

    load_x: FloatProperty(
        name = "load_x",
        description = "Load in x-Direction in kN",
        default = 0.0,
        min = -1000,
        max = 1000.0
        )

    load_y: FloatProperty(
        name = "load_y",
        description = "Load in y-Direction in kN",
        default = 0.0,
        min = -1000,
        max = 1000.0
        )

    load_z: FloatProperty(
        name = "load_z",
        description = "Load in z-Direction in kN",
        default = 0.0,
        min = -1000,
        max = 1000.0
        )

    load_normal: FloatProperty(
        name = "load_normal",
        description = "Load in normal-Direction in kN",
        default = 0.0,
        min = -1000,
        max = 1000.0
        )

    load_projected: FloatProperty(
        name = "load_projected",
        description = "Load projected on floor in kN",
        default = 0.0,
        min = -1000,
        max = 1000.0
        )

    load_area_z: FloatProperty(
        name = "load_area_z",
        description = "Load of full area in z-direction",
        default = 0.0,
        min = -1000,
        max = 1000.0
        )

    generation_size: IntProperty(
        name = "generation_size",
        description="Size of generation for GA",
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

    generation_amount: IntProperty(
        name = "generation_amount",
        description="Amount of generations",
        default = 10,
        min = 1,
        max = 100
        )

    fitness_volume: FloatProperty(
        name = "volume",
        description = "Volume of the enclosed parts of the structure",
        default = 1.0,
        min = 0.0,
        max = 1.0
        )

    fitness_volume_invert: BoolProperty(
        name='volume invert',
        description = "Activate to maximize the volume",
        default=False
    )

    fitness_area: FloatProperty(
        name = "area",
        description = "Area of all faces of the structure",
        default = 0.0,
        min = 0.0,
        max = 1.0
        )

    fitness_area_invert: BoolProperty(
        name='area invert',
        description = "Activate to maximize the area",
        default=False
    )

    fitness_kg: FloatProperty(
        name = "kg",
        description = "Weight the structure (without loads).",
        default = 0.0,
        min = 0.0,
        max = 1.0
        )

    fitness_kg_invert: BoolProperty(
        name='kg invert',
        description = "Activate to maximize the kg.",
        default=False
    )

    fitness_rise: FloatProperty(
        name = "rise",
        description = "Rise of the structure (distances between lowest and highest vertex).",
        default = 0.0,
        min = 0.0,
        max = 1.0
        )

    fitness_rise_invert: BoolProperty(
        name='rise invert',
        description = "Activate to maximize the rise.",
        default=False
    )

    fitness_span: FloatProperty(
        name = "span",
        description = "Span distance of the structure (highest distance between supports).",
        default = 0.0,
        min = 0.0,
        max = 1.0
        )

    fitness_span_invert: BoolProperty(
        name='span invert',
        description = "Activate to maximize the span.",
        default=False
    )

    fitness_cantilever: FloatProperty(
        name = "cantilever",
        description = "Cantilever of the structure (lowest distance from all vertices to all supports).",
        default = 0.0,
        min = 0.0,
        max = 1.0
        )

    fitness_cantilever_invert: BoolProperty(
        name='cantilever invert',
        description = "Activate to maximize the cantilever.",
        default=False
    )

    fitness_average_sigma: FloatProperty(
        name = "average sigma",
        description = "Average sigma of all members.",
        default = 0.0,
        min = 0.0,
        max = 1.0
        )

    fitness_average_strain_energy: FloatProperty(
        name = "average strain energy",
        description = "Average strain energy of all members.",
        default = 1.0,
        min = 0.0,
        max = 1.0
        )

    mate_type: EnumProperty(
        name="mate_type:",
        description="Type of mating",
        items=[
                ("direct", "direct", ""),
                ("morph", "morph", ""),
                ("bruteforce", "bruteforce", "")
               ]
        )

    ga_optimization: EnumProperty(
        name="ga_optimization:",
        description="Enables sectional optimization after each frame",
        items=[
                ("none", "None", ""),
                ("simple", "Simple", ""),
                ("utilization", "Utilization", ""),
                ("complex", "Complex", "")
               ]
        )

    ga_optimization_amount: IntProperty(
        name = "ga_optimization_amount",
        description="Amount of optimization to run for each member",
        default = 3,
        min = 1,
        max = 10
        )

    ga_ranking: IntProperty(
        name = "ga_ranking",
        description="Show results from best to worth fitness.",
        default = 0,
        min = 0,
        max = 250
        )

    forces: EnumProperty(
        name="forces:",
        description="Force types",
        items=[
                ("sigma", "Sigma", ""),
                ("axial", "Axial", ""),
                ("moment_y", "Moment Y", ""),
                ("moment_z", "Moment Z", ""),
                ("shear_y", "Shear Y", ""),
                ("shear_z", "Shear_y", ""),
                ("torque", "Torque", ""),
                ("utilization", "Utilization", ""),
                ("normal_energy", "Normal energy", ""),
                ("moment_energy", "Moment energy", ""),
                ("strain_energy", "Strain energy", "")
               ],
        update=viz_update
        )

    viz_scale: IntProperty(
        name = "viz_scale",
        description = "scale",
        update = viz_update,
        subtype = "PERCENTAGE",
        default = 50,
        min = 1,
        max = 100
        )

    viz_deflection: IntProperty(
        name = "viz_scale",
        description = "deflected / original",
        update = viz_update,
        subtype = "PERCENTAGE",
        default = 50,
        min = 1,
        max = 100
        )

class WM_OT_set_structure(Operator):
    bl_label = "set_structure"
    bl_idname = "wm.set_structure"
    bl_description = "Please select an object in Object-Mode and press set"

    def execute(self, context):
        # crete / recreate collection
        basics.delete_col_if_existing("<Phaenotyp>")
        collection = bpy.data.collections.new("<Phaenotyp>")
        bpy.context.scene.collection.children.link(collection)

        create_data()
        scene = context.scene
        data = scene["<Phaenotyp>"]

        data["structure"] = bpy.context.active_object
        bpy.ops.object.mode_set(mode="EDIT")

        # check for scipy
        calculation.check_scipy()

        # change gui
        data["gui"]["scipy"] = True
        data["gui"]["calculation_type"] = True
        data["gui"]["support"] = True
        data["gui"]["profile"] = False
        data["gui"]["load"] = False
        data["gui"]["analysis"] = False
        data["gui"]["optimization"] = False
        data["gui"]["ga"] = False
        data["gui"]["viz"] = False
        data["gui"]["report"] = False
        data["gui"]["reset"] = True

        return {"FINISHED"}

class WM_OT_set_support(Operator):
    bl_label = "set_support"
    bl_idname = "wm.set_support"
    bl_description = "Please select vertices and press set, to define them as support (Be sure, that you are in Edit Mode of the Structure)"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        obj = data["structure"]

        if context.active_object.mode == "EDIT":
            # get selected vertices
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.mode_set(mode="EDIT")

            for vertex in obj.data.vertices:
                if vertex.select:
                    id = vertex.index

                    support = [
                        phaenotyp.loc_x,
                        phaenotyp.loc_y,
                        phaenotyp.loc_z,
                        phaenotyp.rot_x,
                        phaenotyp.rot_y,
                        phaenotyp.rot_z
                        ]

                    data["supports"][str(id)] = support

                    # delete support if user is deleting the support
                    # (set all conditions to False and apply)
                    fixed = False
                    for i in range(6):
                        if support[i] == True:
                            fixed = True

                    if not fixed:
                        data["supports"].pop(str(id))

            # delete obj if existing
            basics.delete_obj_if_existing("<Phaenotyp>support")
            basics.delete_mesh_if_existing("<Phaenotyp>support")

            # create one mesh for all
            geometry.create_supports(data["structure"], data["supports"])

        # leave signs of support, structure and go to edit-mode
        # (in order to let the user define more supports)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        data["gui"]["profile"] = True

        return {"FINISHED"}

class WM_OT_set_profile(Operator):
    bl_label = "set_profile"
    bl_idname = "wm.set_profile"
    bl_description = "Please select edges in Edit-Mode and press set, to define profiles"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        obj = data["structure"]
        frame = bpy.context.scene.frame_current

        bpy.ops.object.mode_set(mode="OBJECT")

        # create new member
        for edge in obj.data.edges:
            vertex_0_id = edge.vertices[0]
            vertex_1_id = edge.vertices[1]

            if edge.select:
                id = edge.index

                member = {}

                # this variables are always fix
                member["name"] = "member_" + str(id) # equals edge-id
                member["vertex_0_id"] = vertex_0_id # equals id of vertex
                member["vertex_1_id"] = vertex_1_id # equals id of vertex

                member["acceptable_sigma"] = material.current["acceptable_sigma"] # from gui
                member["acceptable_shear"] = material.current["acceptable_shear"] # from gui
                member["acceptable_torsion"] = material.current["acceptable_torsion"] # from gui
                member["acceptable_sigmav"] = material.current["acceptable_sigmav"] # from gui
                member["knick_model"] = material.current["knick_model"] # from gui

                member["E"] = material.current["E"] # from gui
                member["G"] = material.current["G"] # from gui
                member["d"] = material.current["d"] # from gui

                # this variables can change per frame
                # the key "first" is used to store the user-input of each member
                # this is importand, if a user is chaning the frame during the
                # input for some reason
                member["Do"] = {}
                member["Di"] = {}

                member["Do_first"] = material.current["Do"] # from gui
                member["Di_first"] = material.current["Di"] # from fui

                member["Iy"] = {}
                member["Iz"] = {}
                member["J"] = {}
                member["A"] = {}
                member["kg_A"] = {}
                member["ir"] = {}

                member["Iy_first"] = material.current["Iy"] # from gui
                member["Iz_first"] = material.current["Iz"] # from gui
                member["J_first"] = material.current["J"] # from gui
                member["A_first"] = material.current["A"] # from gui
                member["kg_first"] = material.current["kg_A"] # from gui
                member["ir_first"] = material.current["ir"] # from gui

                # results
                member["axial"] = {}
                member["moment_y"] = {}
                member["moment_z"] = {}
                member["moment_h"] = {}
                member["shear_y"] = {}
                member["shear_z"] = {}
                member["shear_h"] = {}
                member["torque"] = {}
                member["sigma"] = {}

                member["Wy"] = {}
                member["WJ"] = {}

                member["long_stress"] = {}
                member["tau_shear"] = {}
                member["tau_torsion"] = {}
                member["sum_tau"] = {}
                member["sigmav"] = {}
                member["sigma"] = {}
                member["max_long_stress"] = {}
                member["max_tau_shear"] = {}
                member["max_tau_torsion"] = {}
                member["max_sum_tau"] = {}
                member["max_sigmav"] = {}
                member["max_sigma"] = {}
                member["acceptable_sigma_buckling"] = {}
                member["lamda"] = {}
                member["lever_arm"] = {}
                member["max_lever_arm"] = {}
                member["initial_positions"] = {}
                member["deflection"] = {}
                member["overstress"] = {}
                member["utilization"] = {}

                member["normal_energy"] = {}
                member["moment_energy"] = {}
                member["strain_energy"] = {}

                member["kg"] = {}
                member["length"] = {}

                data["members"][str(id)] = member

        # delete obj if existing
        basics.delete_obj_if_existing("<Phaenotyp>member")
        basics.delete_mesh_if_existing("<Phaenotyp>member")

        # create one mesh for all
        geometry.create_members(data["structure"], data["members"])

        # leave membersand go to edit-mode
        # (in order to let the user define more supports)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = data["structure"]
        bpy.ops.object.mode_set(mode="EDIT")

        # switch to wireframe
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'WIREFRAME'


        # if all edges are defined as member
        if len(data["structure"].data.edges) == len(data["members"]):
            data["gui"]["load"] = True
            data["gui"]["analysis"] = True
            data["gui"]["optimization"] = True
            data["gui"]["ga"] = True

        return {"FINISHED"}

class WM_OT_set_load(Operator):
    bl_label = "set_load"
    bl_idname = "wm.set_load"
    bl_description = "Add load to selected vertices, edges, or faces"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        obj = data["structure"]

        # create load
        #bpy.ops.object.mode_set(mode="OBJECT") # <---- to avoid "out-of-range-error" on windows
        bpy.ops.object.mode_set(mode="EDIT") # <---- to avoid "out-of-range-error" on windows
        bpy.ops.object.mode_set(mode="OBJECT") # <---- to avoid "out-of-range-error" on windows

        # pass user input to data

        if phaenotyp.load_type == "vertices":
            for vertex in obj.data.vertices:
                if vertex.select:
                    id = vertex.index

                    load = [
                        phaenotyp.load_x,
                        phaenotyp.load_y,
                        phaenotyp.load_z
                        ]

                    data["loads_v"][str(id)] = load

                    # delete load if user is deleting the load
                    # (set all conditions to False and apply)
                    force = False
                    for i in range(3):
                        if load[i] != 0:
                            force = True

                    if not force:
                        data["loads_v"].pop(str(id))

        if phaenotyp.load_type == "edges":
            for edge in obj.data.edges:
                vertex_0_id = edge.vertices[0]
                vertex_1_id = edge.vertices[1]

                if edge.select:
                    id = edge.index

                    load = [
                        phaenotyp.load_x,
                        phaenotyp.load_y,
                        phaenotyp.load_z
                        ]

                    data["loads_e"][str(id)] = load

                    # delete load if user is deleting the load
                    # (set all conditions to False and apply)
                    force = False
                    for i in range(3):
                        if load[i] != 0:
                            force = True

                    if not force:
                        data["loads_e"].pop(str(id))

        if phaenotyp.load_type == "faces":
            for polygon in obj.data.polygons:
                if polygon.select:
                    id = polygon.index
                    load = [
                        phaenotyp.load_normal,
                        phaenotyp.load_projected,
                        phaenotyp.load_area_z,
                        ]

                    data["loads_f"][str(id)] = load

                    # delete load if user is deleting the load
                    # (set all conditions to False and apply)
                    force = False
                    for i in range(3):
                        if load[i] != 0:
                            force = True

                    if not force:
                        data["loads_f"].pop(str(id))

        # delete text of loads
        basics.delete_obj_if_name_contains("<Phaenotyp>load")

        # run one function for all loads
        geometry.create_loads(obj, data["loads_v"], data["loads_e"], data["loads_f"])

        bpy.ops.object.mode_set(mode="EDIT")

        return {"FINISHED"}

class WM_OT_calculate_single_frame(Operator):
    bl_label = "calculate_single_frame"
    bl_idname = "wm.calculate_single_frame"
    bl_description = "Calulate single frame"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = scene["<Phaenotyp>"]["members"]
        frame = bpy.context.scene.frame_current

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()

        # run singlethread and get results
        feas = calculation.run_st(truss, frame)

        # wait for it and interweave results to data
        calculation.interweave_results(feas, members)

        # calculate new visualization-mesh
        geometry.update_members_post()

        basics.view_vertex_colors()

        data["gui"]["viz"] = True
        data["gui"]["report"] = True

        return {"FINISHED"}

class WM_OT_calculate_animation(Operator):
    bl_label = "calculate_animation"
    bl_idname = "wm.calculate_animation"
    bl_description = "Calulate animation"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = scene["<Phaenotyp>"]["members"]
        frame = bpy.context.scene.frame_current

        start = bpy.context.scene.frame_start
        end = bpy.context.scene.frame_end + 1 # to render also last frame

        # start progress
        progress.run()
        progress.http.reset_pci(end-start)

        # create list of trusses
        trusses = {}

        for frame in range(start, end):
            # update scene
            bpy.context.scene.frame_current = frame
            bpy.context.view_layer.update()

            # calculate new properties for each member
            geometry.update_members_pre()

            # created a truss object of PyNite and add to dict
            truss = calculation.prepare_fea()
            trusses[frame] = truss

        # run mp and get results
        feas = calculation.run_mp(trusses)

        # wait for it and interweave results to data
        calculation.interweave_results(feas, members)

        # calculate new visualization-mesh
        geometry.update_members_post()

        basics.view_vertex_colors()

        data["gui"]["viz"] = True
        data["gui"]["report"] = True

        # join progress
        progress.http.active = False
        progress.http.Thread_hosting.join()

        return {"FINISHED"}

class WM_OT_optimize_1(Operator):
    bl_label = "optimize_1"
    bl_idname = "wm.optimize_1"
    bl_description = "Simple sectional performance"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = scene["<Phaenotyp>"]["members"]
        frame = bpy.context.scene.frame_current

        print_data("optimization 1 - simple sectional performance")

        calculation.simple_sectional()

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()

        # run singlethread and get results
        feas = calculation.run_st(truss, frame)

        # wait for it and interweave results to data
        calculation.interweave_results(feas, members)

        # calculate new visualization-mesh
        geometry.update_members_post()

        basics.view_vertex_colors()

        return {"FINISHED"}

class WM_OT_optimize_2(Operator):
    bl_label = "optimize_2"
    bl_idname = "wm.optimize_2"
    bl_description = "utilization sectional performance"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = scene["<Phaenotyp>"]["members"]
        frame = bpy.context.scene.frame_current

        print_data("optimization 2 - utilization sectional performance")

        calculation.utilization_sectional()

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()

        # run singlethread and get results
        feas = calculation.run_st(truss, frame)

        # wait for it and interweave results to data
        calculation.interweave_results(feas, members)

        # calculate new visualization-mesh
        geometry.update_members_post()

        basics.view_vertex_colors()

        return {"FINISHED"}

class WM_OT_optimize_3(Operator):
    bl_label = "optimize_3"
    bl_idname = "wm.optimize_3"
    bl_description = "Complex sectional performance"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = scene["<Phaenotyp>"]["members"]
        frame = bpy.context.scene.frame_current

        print_data("optimization 3 - complex sectional performance")

        calculation.complex_sectional()

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()

        # run singlethread and get results
        feas = calculation.run_st(truss, frame)

        # wait for it and interweave results to data
        calculation.interweave_results(feas, members)

        # calculate new visualization-mesh
        geometry.update_members_post()

        basics.view_vertex_colors()

        return {"FINISHED"}

class WM_OT_topology_1(Operator):
    bl_label = "topolgy_1"
    bl_idname = "wm.topolgy_1"
    bl_description = "Decimate topological performance"

    def execute(self, context):
        print_data("optimization 3 - Decimate topological performance")
        calculation.decimate_topology()

        return {"FINISHED"}

class WM_OT_ga_start(Operator):
    bl_label = "ga_start"
    bl_idname = "wm.ga_start"
    bl_description = "Start genetic muatation over selected shape keys"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        obj = data["structure"]

        print_data("start genetic muataion over selected shape keys")

        # pass from gui
        data["ga_environment"]["generation_size"] = phaenotyp.generation_size
        data["ga_environment"]["elitism"] = phaenotyp.elitism
        data["ga_environment"]["generation_amount"] = phaenotyp.generation_amount
        data["ga_environment"]["new_generation_size"] = phaenotyp.generation_size - phaenotyp.elitism

        # clear to restart
        data["ga_environment"]["generations"] = {}
        data["ga_environment"]["generation_id"] = 0
        data["ga_environment"]["genes"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        data["ga_individuals"] = {}

        # shorten
        generation_size = data["ga_environment"]["generation_size"]
        elitism = data["ga_environment"]["elitism"]
        generation_amount = data["ga_environment"]["generation_amount"]
        new_generation_size = data["ga_environment"]["new_generation_size"]
        generation_id = data["ga_environment"]["generation_id"]
        individuals = data["ga_individuals"]

        if phaenotyp.ga_optimization in ["simple", "utilization", "complex"]:
            ga_optimization_amount = phaenotyp.ga_optimization_amount
        else:
            ga_optimization_amount = 0

        # skip ga_optimization if geometrical only
        if phaenotyp.calculation_type != "geometrical":
            ga_optimization_amount = 0

        # start progress
        progress.run()
        progress.http.reset_pci(1)
        progress.http.reset_o(ga_optimization_amount)

        # set frame_start
        bpy.context.scene.frame_start = 0

        # generate an individual as basis at frame 0
        # this individual has choromosome with all genes equals 0
        # the fitness of this chromosome is the basis for all others
        ga.generate_basis()

        for i in range(ga_optimization_amount):
            progress.http.reset_pci(1)
            ga.sectional_optimization(0, 1)
            progress.http.update_o()

        progress.http.reset_pci(1)
        ga.calculate_fitness(0, 1)
        individuals["0"]["fitness"]["weighted"] = 1

        if phaenotyp.mate_type in ["direct", "morph"]:
            # create start and end of calculation and create individuals
            start = 1
            end = generation_size

            # set frame_end to first size of inital generation
            bpy.context.scene.frame_end = end

            # progress
            progress.http.reset_pci(end-start)
            progress.http.g = [0, generation_amount]
            progress.http.reset_o(ga_optimization_amount)

            # create initial generation
            # the first generation contains 20 individuals (standard value is 20)
            # the indiviuals are created with random genes
            # there is no elitism possible, because there is no previous group
            ga.create_initial_individuals(start, end)

            # optimize if sectional performance if activated
            for i in range(ga_optimization_amount):
                progress.http.reset_pci(end-start)
                ga.sectional_optimization(start, end)
                progress.http.update_o()

            progress.http.reset_pci(end-start)
            ga.calculate_fitness(start, end)
            ga.populate_initial_generation()

            # create all other generations
            # 2 indiviuals are taken from previous group (standard value is 10)
            # 10 indiviuals are paired (standard ist 50 %)
            for i in range(generation_amount):
                start = end
                end = start + new_generation_size

                # expand frame
                bpy.context.scene.frame_end = end

                # create new generation and copy fittest percent
                ga.do_elitism()

                # create 18 new individuals (standard value of 20 - 10 % elitism)
                progress.http.reset_pci(end-start)
                progress.http.reset_o(ga_optimization_amount)

                ga.create_new_individuals(start, end)

                for i in range(ga_optimization_amount):
                    progress.http.reset_pci(end-start)
                    ga.sectional_optimization(start, end)
                    progress.http.update_o()

                ga.calculate_fitness(start, end)
                ga.populate_new_generation(start, end)

                # update progress
                progress.http.update_g()

        if phaenotyp.mate_type == "bruteforce":
            data = scene["<Phaenotyp>"]
            shape_keys = obj.data.shape_keys.key_blocks

            # create matrix of possible combinations
            matrix = []
            for key in range(len(shape_keys)-1): # to exclude basis
                genes = data["ga_environment"]["genes"]
                matrix.append(genes)

            chromosomes = list(itertools.product(*matrix))
            chromosomes.pop(0) # delete the basis individual, is allready calculated

            # create start and end of calculation and create individuals
            start = 1 # basis indiviual is allready created and optimized
            end = len(chromosomes)+1

            # set frame_end to first size of inital generation
            bpy.context.scene.frame_end = end-1

            # progress
            progress.http.reset_pci(end-start)
            progress.http.reset_o(ga_optimization_amount)
            progress.http.g = [0,1]

            # pair with bruteforce
            ga.bruteforce(chromosomes)
            for i in range(ga_optimization_amount):
                progress.http.reset_pci(end-start)
                ga.sectional_optimization(start, end)
                progress.http.update_o()

            ga.calculate_fitness(start, end)

        if phaenotyp.calculation_type != "geometrical":
            basics.view_vertex_colors()

        # join progress
        progress.http.active = False
        progress.http.Thread_hosting.join()

        data["gui"]["viz"] = True
        data["gui"]["report"] = True

        return {"FINISHED"}

class WM_OT_ga_ranking(Operator):
    bl_label = "ga_ranking"
    bl_idname = "wm.ga_ranking"
    bl_description = "Go to indivual by ranking."

    def execute(self, context):
        scene = context.scene
        data = scene["<Phaenotyp>"]

        print_data("go to selected ranking")

        ga.goto_indivual()

        return {"FINISHED"}

class WM_OT_ga_render_animation(Operator):
    bl_label = "ga_ranking"
    bl_idname = "wm.ga_render_animation"
    bl_description = "Go to indivual by ranking."

    def execute(self, context):
        scene = context.scene
        data = scene["<Phaenotyp>"]

        environment = data["ga_environment"]
        individuals = data["ga_individuals"]

        print_data("render animation")

        # change engine, shading
        bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
        bpy.context.scene.display.shading.light = 'FLAT'
        bpy.context.scene.display.shading.color_type = 'VERTEX'

        # set background to transparent
        bpy.context.scene.render.film_transparent = True

        # use stamp
        bpy.context.scene.render.use_stamp = True
        bpy.context.scene.render.use_stamp_note = True
        bpy.context.scene.render.stamp_note_text = ""
        bpy.context.scene.render.stamp_background[3] = 1
        bpy.context.scene.render.stamp_background = (0, 0, 0, 1)

        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)

        # render all indiviuals
        image_id = 0 # to sort images by fitness in filemanager
        amount_of_digts = len(str(len(individuals))) # write in format 01, 001 or 0001 ...

        # sort by fitness
        list_result = []
        for name, individual in individuals.items():
            list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

        sorted_list = sorted(list_result, key = lambda x: x[2])

        for frame, chromosome, fitness in sorted_list:
            str_image_id = str(image_id).zfill(amount_of_digts)
            filename = directory + "/Phaenotyp-ga_animation/image_id_" + str_image_id + "-individual_" + str(frame)

            # get text from chromosome
            str_chromosome = "["
            for gene in chromosome:
                str_chromosome += str(round(gene, 3))
                str_chromosome += ", "
            str_chromosome[-1]
            str_chromosome += "]"

            # set note
            text = filename + " -> " + str_chromosome + " fitness " + str(fitness)
            bpy.context.scene.render.stamp_note_text = text

            # set path and render
            bpy.context.scene.render.filepath = filename
            bpy.context.scene.render.image_settings.file_format='PNG'
            bpy.context.scene.render.filepath=filename
            bpy.ops.render.render(write_still=1)

            # update scene
            bpy.context.scene.frame_current = int(frame)
            bpy.context.view_layer.update()

            image_id += 1

        print_data("render animation - done")

        return {"FINISHED"}

class WM_OT_text(Operator):
    bl_label = "text"
    bl_idname = "wm.text"
    bl_description = "Generate output at the selected vertex"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = data["members"]
        frame = bpy.context.scene.frame_current

        print_data("Generate output at the selected point")
        data["texts"] = []
        selected_objects = bpy.context.selected_objects

        # get selected vertex
        bpy.ops.object.mode_set(mode="OBJECT")
        for vertex in bpy.context.active_object.data.vertices:
            if vertex.select == True:
                # continue with this vertex:
                # (only one is selected)
                vertex_id = vertex.index
                bpy.ops.object.mode_set(mode="EDIT")

                # get member
                for id, member in members.items():
                    for position in range(11):
                        if member["mesh_vertex_ids"][position] == vertex_id:
                            data_temp = []
                            # get member id
                            text = "Member: " + id
                            data_temp.append(text)

                            # get Position
                            text = "Position: " + str(position)
                            data_temp.append(text)

                            # get frame
                            frame = bpy.context.scene.frame_current

                            # get Do and Di
                            text = "Do: " + str(round(member["Do"][str(frame)], 3))
                            data_temp.append(text)
                            text = "Di: " + str(round(member["Di"][str(frame)], 3))
                            data_temp.append(text)

                            # results
                            text = "axial: " + str(round(member["axial"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "moment_y: " + str(round(member["moment_y"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "moment_z: " + str(round(member["moment_z"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "shear_y: " + str(round(member["shear_y"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "shear_z: " + str(round(member["shear_z"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "torque: " + str(round(member["torque"][str(frame)][position], 3))
                            data_temp.append(text)

                            text = "long_stress: " + str(round(member["long_stress"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "tau_shear: " + str(round(member["tau_shear"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "tau_torsion: " + str(round(member["tau_torsion"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "sum_tau: " + str(round(member["sum_tau"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "sigmav: " + str(round(member["sigmav"][str(frame)][position], 3))
                            data_temp.append(text)
                            text = "sigma: " + str(round(member["sigma"][str(frame)][position], 3))
                            data_temp.append(text)

                            # leverarm
                            text = "leverarm: " + str(round(member["lever_arm"][str(frame)][position], 3))
                            data_temp.append(text)

                            # overstress
                            text = "overstress: " + str(round(member["overstress"][str(frame)], 3))
                            data_temp.append(text)

                            data["texts"] = data_temp


        return {"FINISHED"}

class WM_OT_report_members(Operator):
    bl_label = "report"
    bl_idname = "wm.report_members"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        print_data("Generate report at frame in html-format")

        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = data["members"]
        frame = bpy.context.scene.frame_current


        # create folder
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)

        try:
            os.mkdir(os.path.join(directory, "Phaenotyp-members"))
        except:
            pass

        directory += "/Phaenotyp-members/"

        report.copy_sorttable(directory)

        sorted_frames = basics.sorted_keys(members["0"]["axial"])
        start = sorted_frames[0] # first frame (if user is changing start frame)
        end = sorted_frames[len(sorted_frames)-1]

        report.report_members(directory, frame)

        # open file
        file_to_open = directory + "/axial.html"
        webbrowser.open(file_to_open)

        return {"FINISHED"}

class WM_OT_report_frames(Operator):
    bl_label = "report"
    bl_idname = "wm.report_frames"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        print_data("Generate report overview in html-format")

        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = data["members"]
        frame = bpy.context.scene.frame_current


        # create folder
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)

        try:
            os.mkdir(os.path.join(directory, "Phaenotyp-frames"))
        except:
            pass

        directory += "/Phaenotyp-frames/"

        report.copy_sorttable(directory)

        sorted_frames = basics.sorted_keys(members["0"]["axial"])
        start = sorted_frames[0] # first frame (if user is changing start frame)
        end = sorted_frames[len(sorted_frames)-1]

        report.report_frames(directory, start, end)

        # open file
        file_to_open = directory + "/max_sigma.html"
        webbrowser.open(file_to_open)

        return {"FINISHED"}

class WM_OT_report_chromosomes(Operator):
    bl_label = "report"
    bl_idname = "wm.report_chromosomes"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        print_data("Generate report at frame in html-format")

        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = data["members"]
        frame = bpy.context.scene.frame_current


        # create folder
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)

        try:
            os.mkdir(os.path.join(directory, "Phaenotyp-chromosomes"))
        except:
            pass

        directory += "/Phaenotyp-chromosomes/"

        report.copy_sorttable(directory)
        report.report_chromosomes(directory)

        # open file
        file_to_open = directory + "/index.html"
        webbrowser.open(file_to_open)

        return {"FINISHED"}

class WM_OT_report_tree(Operator):
    bl_label = "report"
    bl_idname = "wm.report_tree"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        print_data("Generate report at frame in html-format")

        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = data["members"]
        frame = bpy.context.scene.frame_current


        # create folder
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)

        try:
            os.mkdir(os.path.join(directory, "Phaenotyp-tree"))
        except:
            pass

        directory += "/Phaenotyp-tree/"

        report.report_tree(directory)

        # open file
        file_to_open = directory + "/index.html"
        webbrowser.open(file_to_open)

        return {"FINISHED"}

class WM_OT_reset(Operator):
    bl_label = "reset"
    bl_idname = "wm.reset"
    bl_description = "Reset Phaenotyp"

    def execute(self, context):
        print_data("reset phaenotyp")

        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]

        # copied from create_data
        data["structure"] = None
        data["supports"] = {}
        data["members"] = {}
        data["frames"] = {}
        data["loads_v"] = {}
        data["loads_e"] = {}
        data["loads_f"] = {}

        data["process"]["scipy_available"] = False
        data["done"] = {}

        data["gui"]["scipy"] = False
        data["gui"]["calculation_type"] = False
        data["gui"]["support"] = False
        data["gui"]["profile"] = False
        data["gui"]["load"] = False
        data["gui"]["analysis"] = False
        data["gui"]["optimization"] = False
        data["gui"]["ga"] = False
        data["gui"]["viz"] = False
        data["gui"]["report"] = False
        data["gui"]["reset"] = False

        data["ga_environment"] = {}
        data["ga_individuals"] = {}

        data["texts"] = []

        # delete obj and meshes
        basics.delete_obj_if_existing("<Phaenotyp>support")
        basics.delete_mesh_if_existing("<Phaenotyp>support")

        basics.delete_obj_if_existing("<Phaenotyp>member")
        basics.delete_mesh_if_existing("<Phaenotyp>member")

        # delete collection
        basics.delete_col_if_existing("<Phaenotyp>")

        return {"FINISHED"}

class OBJECT_PT_Phaenotyp:
    bl_label = "Phänotyp"
    bl_idname = "OBJECT_PT_custom_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Phänotyp"

class OBJECT_PT_Phaenotyp_structure(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_structure"
    bl_label = "Structure"

    def draw(self, context):
        scene = bpy.context.scene
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.structure(layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_scipy(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_scipy"
    bl_label = "Sparse matrix"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["scipy"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.scipy(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_calculation_type(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_calculation_type"
    bl_label = "Calculation"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["calculation_type"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.calculation_type(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_support(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_support"
    bl_label = "Support"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["support"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.support(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_profile(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_profile"
    bl_label = "Profile"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["profile"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.profile(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_load(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_load"
    bl_label = "Load"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["load"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.load(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_analysis(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_analysis"
    bl_label = "Analysis"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["analysis"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.analysis(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_optimization(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_optimization"
    bl_label = "Optimization"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["optimization"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.optimization(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_ga(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_ga"
    bl_label = "Genetic algorithm"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["ga"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.ga(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_viz(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_viz"
    bl_label = "Visualization"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["viz"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.viz(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_report(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_report"
    bl_label = "Report"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["report"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.report(data, layout, phaenotyp, frame)

class OBJECT_PT_Phaenotyp_reset(OBJECT_PT_Phaenotyp, bpy.types.Panel):
    bl_idname = "OBJECT_PT_Phaenotyp_reset"
    bl_label = "Reset"

    @classmethod
    def poll(cls, context):
        data = bpy.context.scene.get("<Phaenotyp>")
        if data:
            return data["gui"]["reset"]
        else:
            return False

    def draw(self, context):
        scene = bpy.context.scene
        data = scene.get("<Phaenotyp>")
        layout = self.layout
        phaenotyp = scene.phaenotyp
        frame = scene.frame_current
        panels.reset(data, layout, phaenotyp, frame)

classes = (
    phaenotyp_properties,

    WM_OT_set_structure,
    WM_OT_set_support,
    WM_OT_set_profile,
    WM_OT_set_load,
    WM_OT_calculate_single_frame,
    WM_OT_calculate_animation,

    WM_OT_optimize_1,
    WM_OT_optimize_2,
    WM_OT_optimize_3,
    WM_OT_topology_1,

    WM_OT_ga_start,
    WM_OT_ga_ranking,
    WM_OT_ga_render_animation,

    WM_OT_text,
    WM_OT_report_members,
    WM_OT_report_frames,
    WM_OT_report_chromosomes,
    WM_OT_report_tree,

    WM_OT_reset,

    OBJECT_PT_Phaenotyp_structure,
    OBJECT_PT_Phaenotyp_scipy,
    OBJECT_PT_Phaenotyp_calculation_type,
    OBJECT_PT_Phaenotyp_support,
    OBJECT_PT_Phaenotyp_profile,
    OBJECT_PT_Phaenotyp_load,
    OBJECT_PT_Phaenotyp_analysis,
    OBJECT_PT_Phaenotyp_optimization,
    OBJECT_PT_Phaenotyp_ga,
    OBJECT_PT_Phaenotyp_viz,
    OBJECT_PT_Phaenotyp_report,
    OBJECT_PT_Phaenotyp_reset
)

@persistent
def update_post(scene):
    # only run if Phanotyp is used
    data_available = scene.get("<Phaenotyp>")

    if data_available:
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]

        # only run if member is available
        members_available = data.get("members")
        if members_available:
            members = data["members"]
            frame = scene.frame_current

            # check if a result is available for the first member
            result_available = members[str(0)].get("axial")
            if result_available:
                # check if a result is available for the first member at frame
                result_at_frame = result_available.get(str(frame))
                if data["done"][str(frame)]:
                    geometry.update_members_post()

        # apply chromosome if available
        individuals = data.get("ga_individuals")
        if individuals:
            shape_keys = data["structure"].data.shape_keys.key_blocks
            chromosome = individuals[str(frame)]["chromosome"]
            for id, key in enumerate(shape_keys):
                if id > 0: # to exlude basis
                    key.value = chromosome[id-1]*0.1

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
