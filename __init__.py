bl_info = {
    "name": "Phänotyp",
    "description": "Genetic optimization of architectural structures",
    "author": "bewegende Architektur e.U. and Karl Deix",
    "version": (0, 1, 0),
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

from phaenotyp import basics, material, geometry, calculation, ga, report

def create_data():
    data = bpy.context.scene.get("<Phaenotyp>")
    if not data:
        data = bpy.context.scene["<Phaenotyp>"] = {
            "structure":{},
            "supports":{},
            "members":{},
            "loads_v":{},
            "loads_e":{},
            "loads_f":{},
            "process":{},
            "ga_environment":{},
            "ga_individuals":{},
            "texts":{}
        }

        data["structure"] = None
        data["supports"] = {}
        data["members"] = {}
        data["loads_v"] = {}
        data["loads_e"] = {}
        data["loads_f"] = {}

        data["process"]["calculate_update_post"] = False
        data["process"]["genetetic_mutation_update_post"] = False
        data["process"]["scipy_available"] = False
        data["process"]["done"] = False

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

    fitness_function: EnumProperty(
        name = "fitness_function",
        description = "Fitness function",
        items=[
                ("average_sigma", "Average sigma", ""),
                ("member_sigma", "Member sigma", ""),
                ("volume", "Volume", ""),
                ("lever_arm_truss", "Lever arm for normal forces", ""),
                ("lever_arm_bending", "Lever arm for moment forces", "")
               ]
        )

    mate_type: EnumProperty(
        name="mate_type:",
        description="Type of mating",
        items=[
                ("direct", "direct", ""),
                ("morph", "morph", "")
               ]
        )

    ga_optimization: EnumProperty(
        name="ga_optimization:",
        description="Enables sectional optimization after each frame",
        items=[
                ("none", "None", ""),
                ("simple", "Simple", ""),
                ("complex", "Complex", "")
               ]
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
                ("moment_z", "Moment Z", "")
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

        # if user is changing the setup, the visualization is disabled
        data["process"]["done"] = False

        # check for scipy
        calculation.check_scipy()

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

        # if user is changing the setup, the visualization is disabled
        data["process"]["done"] = False

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
                member["name"] = "Member_" + str(id) # equals edge-id
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
                member["Do"] = {}
                member["Di"] = {}

                member["Do"][str(frame)] = material.current["Do"] # from gui
                member["Di"][str(frame)] = material.current["Di"] # from fui

                member["Iy"] = {}
                member["Iz"] = {}
                member["J"] = {}
                member["A"] = {}
                member["kg"] = {}

                member["Iy"][str(frame)] = material.current["Iy"] # from gui
                member["Iz"][str(frame)] = material.current["Iz"] # from gui
                member["J"][str(frame)] = material.current["J"] # from gui
                member["A"][str(frame)] = material.current["A"] # from gui
                member["kg"][str(frame)] = material.current["kg"] # from gui

                # results
                member["axial"] = {}
                member["moment_y"] = {}
                member["moment_z"] = {}
                member["shear_y"] = {}
                member["shear_z"] = {}
                member["torque"] = {}
                member["sigma"] = {}

                member["ir"] = {}
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
                member["acceptable_sigma_buckling"] = {} # <---------------- sonst doppelt?
                member["lamda"] = {}
                member["lever_arm"] = {} # lever_arm at eleven points of each member
                member["max_lever_arm"] = {} # max value of lever_arm
                member["initial_positions"] = {}
                member["deflection"] = {}
                member["overstress"] = {}

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

        # if user is changing the setup, the visualization is disabled
        data["process"]["calculate_update_post"] = False
        data["process"]["genetetic_mutation_update_post"] = False
        data["process"]["done"] = False

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

        # if user is changing the setup, the visualization is disabled
        data["process"]["done"] = False

        bpy.ops.object.mode_set(mode="EDIT")
        return {"FINISHED"}

class WM_OT_calculate_single_frame(Operator):
    bl_label = "calculate_single_frame"
    bl_idname = "wm.calculate_single_frame"
    bl_description = "Calulate single frame"

    def execute(self, context):
        geometry.update_members_pre()
        calculation.transfer_analyze()
        geometry.update_members_post()

        return {"FINISHED"}

class WM_OT_calculate_animation(Operator):
    bl_label = "calculate_animation"
    bl_idname = "wm.calculate_animation"
    bl_description = "Calulate animation"

    def execute(self, context):
        scene = context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]

        geometry.update_members_pre()
        calculation.transfer_analyze()
        geometry.update_members_post()

        # activate calculation in update_post
        data["process"]["calculate_update_post"] = True

        # set animation to first frame and start
        start = bpy.context.scene.frame_start
        bpy.context.scene.frame_current = start
        bpy.ops.screen.animation_play()

        return {"FINISHED"}

class WM_OT_optimize_1(Operator):
    bl_label = "optimize_1"
    bl_idname = "wm.optimize_1"
    bl_description = "Simple sectional performance"

    def execute(self, context):
        print_data("optimization 1 - simple sectional performance")

        calculation.simple_sectional()
        geometry.update_members_pre()
        calculation.transfer_analyze()
        geometry.update_members_post()

        return {"FINISHED"}

class WM_OT_optimize_2(Operator):
    bl_label = "optimize_2"
    bl_idname = "wm.optimize_2"
    bl_description = "Complex sectional performance"

    def execute(self, context):
        print_data("optimization 2 - complex sectional performance")

        calculation.complex_sectional()
        geometry.update_members_pre()
        calculation.transfer_analyze()
        geometry.update_members_post()

        return {"FINISHED"}

class WM_OT_optimize_3(Operator):
    bl_label = "optimize_3"
    bl_idname = "wm.optimize_3"
    bl_description = "Decimate topological performance"

    def execute(self, context):
        print_data("optimization 3 - Decimate topological performance")
        geometry.update_members_pre()
        calculation.transfer_analyze()
        geometry.update_members_post()
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
        data["ga_environment"]["population_size"] = phaenotyp.population_size
        data["ga_environment"]["elitism"] = phaenotyp.elitism
        data["ga_environment"]["new_generation_size"] = phaenotyp.population_size - phaenotyp.elitism
        data["ga_environment"]["fitness_function"] = phaenotyp.fitness_function

        # clear to restart
        data["ga_environment"]["population"] = {}
        data["ga_environment"]["new_generation"] = {}
        data["ga_environment"]["generation_id"] = 1
        data["ga_environment"]["genes"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        data["ga_environment"]["ga_state"] = "create initial population"
        data["ga_environment"]["best"] = None
        data["ga_individuals"] = {}

        # activate calculation in update_post
        data["process"]["genetetic_mutation_update_post"] = True

        # set animation to first frame and start
        start = bpy.context.scene.frame_start
        bpy.context.scene.frame_current = start
        bpy.ops.screen.animation_play()

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

class WM_OT_report(Operator):
    bl_label = "report"
    bl_idname = "wm.report"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        print_data("Generate report as html-format")

        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        members = data["members"]
        frame = bpy.context.scene.frame_current

        # create folder
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)

        try:
            os.mkdir(os.path.join(directory, "report"))
        except:
            pass


        ### members
        for id, member in members.items():
            name = member["name"]
            file = report.start(directory, name, 1920, 800)

            # list elements with one entry at all
            results = ["vertex_1_id", "vertex_0_id",
                "acceptable_sigma", "acceptable_shear", "acceptable_torsion", "acceptable_sigmav",
                "E", "G", "d"]
            y = 20
            for result in results:
                value = "member['" + result + "']"
                report.text(file, 0, y, result + ": " + str(eval(value)), 'start')
                y = y + 20

            # list elements with one entry per frame
            results = ["ir", "Do", "Di", "Iy", "Iz", "J", "A", "kg","Wy", "WJ"]

            y = 220
            for result in results:
                value = "member['" + result + "']['" + str(frame) + "']"
                value = round(eval(value), 3)
                report.text(file, 0, y, result + ": " + str(value), 'start')
                y = y + 20

            # positions within members
            y = 460
            for pos in range(11):
                report.text(file, 0, y, "pos: " + str(pos), 'start')
                y = y + 20

            # write forces
            results = ["axial", "moment_y", "moment_z", "shear_y", "shear_z", "torque", "sigma", "long_stress", "tau_shear", "tau_torsion", "sum_tau", "lever_arm"]
            x = 150
            for result in results:
                y = 460
                report.text(file, x, y-20, result + ":", 'end')
                for pos in range(11):
                    value = "member['" + result + "']['" + str(frame) + "']" + "[" + str(pos) + "]"
                    value = round(eval(value), 3)
                    report.text(file, x, y, str(value), 'end')
                    y = y + 20

                x = x + 160

        report.end(file)

        ### overview
        # lists with 1 value per member per frame
        results = ["max_long_stress", "max_tau_shear", "max_tau_torsion", "max_sum_tau", "max_sigmav", "max_sigma", "max_lever_arm"]
        for result in results:
            html = result + ".html"
            file = report.start(directory, html, 1920, 20*len(members)+20)

            y = 20
            # create list of specific result
            list_result = []
            for id, member in members.items():
                value = "member['" + result + "']['" + str(frame) + "']"
                value = round(eval(value), 3)
                list_result.append([member["name"], value])

            sorted_list = sorted(list_result, key = lambda x: x[1])

            # calculate factor for scaling
            bottom = abs(sorted_list[0][1])
            top = abs(sorted_list[len(sorted_list)-1][1])

            if bottom > top:
                factor = 1/bottom

            elif top > bottom:
                factor = 1/top

            elif top == bottom:
                if top != 0:
                    factor = 1/top
                else:
                    factor = 0

            else:
                factor = 0

            # draw results of members
            for name, value in sorted_list:
                report.text_link(file, 0, y, name) # 'start' 'middle' 'end'

                if value > 0:
                    color = "255,0,0"
                else:
                    color = "0,0,255"

                report.line(file, 150, y-4, 150+abs(value*500)*factor, y-4, 5, color)

                text = str(round(value, 3)) + " xx"
                report.text(file, 150+abs(value*500)*factor+5, y, text, 'start') # 'start' 'middle' 'end'

                y = y + 20

            report.end(file)

        # lists with 10 values per member per frame

        results = ["axial", "moment_y", "moment_z", "shear_y", "shear_z", "torque", "lever_arm"]
        for result in results:
            html = result + ".html"
            file = report.start(directory, html, 1920, 20*len(members)+20)

            y = 20

            # create list of specific result
            list_result = []
            for id, member in members.items():
                values = "member['" + result + "']['" + str(frame) + "']"
                values = eval(values)
                entries = []
                for x in values:
                    entries.append(x)

                value = basics.return_max_diff_to_zero(entries)
                value = round(value, 3)
                list_result.append([member["name"], value])

            sorted_list = sorted(list_result, key = lambda x: x[1])

            # calculate factor for scaling
            bottom = abs(sorted_list[0][1])
            top = abs(sorted_list[len(sorted_list)-1][1])

            if bottom > top:
                factor = 1/bottom

            elif top > bottom:
                factor = 1/top

            elif top == bottom:
                if top != 0:
                    factor = 1/top
                else:
                    factor = 0

            else:
                factor = 0

            # draw results of members
            for name, value in sorted_list:
                report.text_link(file, 0, y, name) # 'start' 'middle' 'end'

                if value > 0:
                    color = "255,0,0"
                else:
                    color = "0,0,255"

                report.line(file, 150, y-4, 150+abs(value*500)*factor, y-4, 5, color)

                text = str(round(value, 3)) + " xx"
                report.text(file, 150+abs(value*500)*factor+5, y, text, 'start') # 'start' 'middle' 'end'

                y = y + 20

            report.end(file)

        # open file
        file_to_open = directory + "/report/axial.html"
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
        data["loads_v"] = {}
        data["loads_e"] = {}
        data["loads_f"] = {}

        data["process"]["calculate_update_post"] = False
        data["process"]["genetetic_mutation_update_post"] = False
        data["process"]["scipy_available"] = False
        data["process"]["done"] = False

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

        # switch to object-mode
        bpy.ops.object.mode_set(mode="OBJECT")

        return {"FINISHED"}

class OBJECT_PT_Phaenotyp(Panel):
    bl_label = "Phänotyp 0.1.0"
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

        # start with defining a structure
        box_structure = layout.box()
        data = bpy.context.scene.get("<Phaenotyp>")

        if not data or data["structure"] == None:
            box_structure.label(text="Structure:")
            box_structure.operator("wm.set_structure", text="Set")

        else:
             # disable previous box
            box_structure.enabled = False

            obj = data["structure"]
            box_structure.label(text = obj.name_full + " is defined as structure")

            text = "Press Strg+A and apply "
            if obj.location[0] != 0 or obj.location[1] != 0 or obj.location[2] != 0:
                text = text + "Location "

            if obj.rotation_euler[0] != 0 or obj.rotation_euler[1] != 0 or obj.rotation_euler[2] != 0:
                text = text + "Rotation "

            if obj.scale[0] != 1 or obj.scale[1] != 1 or obj.scale[2] != 1:
                text = text + "Scale "

            if text != "Press Strg+A and apply ":
                text = text + "to avoid weird behaviour"
                box_structure.label(text = text)

            # check or uncheck scipy if available
            if data["scipy_available"]:
                box_scipy = layout.box()
                box_scipy.label(text = "Scipy is available.")
                box_scipy.prop(phaenotyp, "use_scipy", text="use scipy")

            # define support
            box_support = layout.box()
            box_support.label(text="Support:")

            col = box_support.column()
            split = col.split()
            split.prop(phaenotyp, "loc_x", text="loc x")
            split.prop(phaenotyp, "rot_x", text="rot x")

            col = box_support.column()
            split = col.split()
            split.prop(phaenotyp, "loc_y", text="loc y")
            split.prop(phaenotyp, "rot_y", text="rot y")

            col = box_support.column()
            split = col.split()
            split.prop(phaenotyp, "loc_z", text="loc z")
            split.prop(phaenotyp, "rot_z", text="rot z")

            box_support.operator("wm.set_support", text="Set")

            if len(data["supports"]) > 0:
                box_support.label(text = str(len(data["supports"])) + " vertices defined as support")

                # define material and geometry
                box_profile = layout.box()
                box_profile.label(text="Profile:")

                box_profile.prop(phaenotyp, "Do", text="Diameter outside")
                box_profile.prop(phaenotyp, "Di", text="Diameter inside")

                # current setting passed from gui
                # (because a property can not be set in gui)
                material.current["Do"] = phaenotyp.Do * 0.1
                material.current["Di"] = phaenotyp.Di * 0.1

                box_profile.label(text="Material:")
                box_profile.prop(phaenotyp, "material", text="Type")
                if phaenotyp.material == "custom":
                    box_profile.prop(phaenotyp, "E", text="Modulus of elasticity")
                    box_profile.prop(phaenotyp, "G", text="Shear modulus")
                    box_profile.prop(phaenotyp, "d", text="Density")

                    box_profile.prop(phaenotyp, "acceptable_sigma", text="Acceptable sigma")
                    box_profile.prop(phaenotyp, "acceptable_shear", text="Acceptable shear")
                    box_profile.prop(phaenotyp, "acceptable_torsion", text="Acceptable torsion")
                    box_profile.prop(phaenotyp, "acceptable_sigmav", text="Acceptable sigmav")
                    box_profile.prop(phaenotyp, "ir", text="Ir")

                    material.current["E"] = phaenotyp.E
                    material.current["G"] = phaenotyp.G
                    material.current["d"] = phaenotyp.d

                    material.current["acceptable_sigma"] = phaenotyp.acceptable_sigma
                    material.current["acceptable_shear"] = phaenotyp.acceptable_shear
                    material.current["acceptable_torsion"] = phaenotyp.acceptable_torsion
                    material.current["acceptable_sigmav"] = phaenotyp.acceptable_sigmav

                else:
                    # pass input form library to data
                    for mat in material.library:
                        if phaenotyp.material == mat[0]: # select correct material
                            # current setting passed from gui
                            # (because a property can not be set in gui)
                            material.current["E"] = mat[2]
                            material.current["G"] = mat[3]
                            material.current["d"] = mat[4]

                            material.current["acceptable_sigma"] = mat[5]
                            material.current["acceptable_shear"] = mat[6]
                            material.current["acceptable_torsion"] = mat[7]
                            material.current["acceptable_sigmav"] = mat[8]
                            material.current["knick_model"] = mat[9]


                    box_profile.label(text="E = " + str(material.current["E"]) + " kN/cm²")
                    box_profile.label(text="G = " + str(material.current["G"]) + " kN/cm²")
                    box_profile.label(text="d = " + str(material.current["d"]) + " g/cm3")

                    box_profile.label(text="Acceptable sigma = " + str(material.current["acceptable_sigma"]))
                    box_profile.label(text="Acceptable shear = " + str(material.current["acceptable_shear"]))
                    box_profile.label(text="Acceptable torsion = " + str(material.current["acceptable_torsion"]))
                    box_profile.label(text="Acceptable sigmav = " + str(material.current["acceptable_sigmav"]))

                material.update() # calculate Iy, Iz, J, A, kg
                box_profile.label(text="Iy = " + str(round(material.current["Iy"], 4)) + " cm⁴")
                box_profile.label(text="Iz = " + str(round(material.current["Iz"], 4)) + " cm⁴")
                box_profile.label(text="J = " + str(round(material.current["J"], 4)) + " cm⁴")
                box_profile.label(text="A = " + str(round(material.current["A"], 4)) + " cm²")
                box_profile.label(text="kg = " + str(round(material.current["kg"], 4)) + " kg/m")

                box_profile.operator("wm.set_profile", text="Set")

                # if all edges are defined as member
                if len(data["structure"].data.edges) == len(data["members"]):
                    # Define loads
                    box_load = layout.box()
                    box_load.label(text="Loads:")
                    box_load.prop(phaenotyp, "load_type", text="Type")

                    if phaenotyp.load_type == "faces": # if faces
                        box_load.prop(phaenotyp, "load_normal", text="normal (like wind)")
                        box_load.prop(phaenotyp, "load_projected", text="projected (like snow)")
                        box_load.prop(phaenotyp, "load_area_z", text="area z (like weight of facade)")

                    else: # if vertices or edges
                        box_load.prop(phaenotyp, "load_x", text="x")
                        box_load.prop(phaenotyp, "load_y", text="y")
                        box_load.prop(phaenotyp, "load_z", text="z")

                    box_load.operator("wm.set_load", text="Set")

                    # Analysis
                    box_analysis = layout.box()
                    box_analysis.label(text="Analysis:")
                    box_analysis.operator("wm.calculate_single_frame", text="Single Frame")
                    box_analysis.operator("wm.calculate_animation", text="Animation")

                    # Optimization
                    box_opt = layout.box()
                    box_opt.label(text="Optimization:")
                    if data["process"]["done"]:
                        box_opt.operator("wm.optimize_1", text="Simple - sectional performance")
                        box_opt.operator("wm.optimize_2", text="Complex - sectional performance")
                        box_opt.operator("wm.optimize_3", text="Decimate - topological performance")
                    else:
                        box_opt.label(text="Run single analysis first.")

                    shape_key = data["structure"].data.shape_keys
                    if shape_key:
                        # Genetic Mutation:
                        box_ga = layout.box()
                        box_ga.label(text="Genetic Mutation:")
                        box_ga.prop(phaenotyp, "population_size", text="Size of population for GA")
                        box_ga.prop(phaenotyp, "elitism", text="Size of elitism for GA")
                        box_ga.prop(phaenotyp, "fitness_function", text="Fitness function")
                        box_ga.prop(phaenotyp, "mate_type", text="Type of mating")
                        box_ga.prop(phaenotyp, "ga_optimization", text="Sectional optimization")

                        for keyblock in shape_key.key_blocks:
                            name = keyblock.name
                            box_ga.label(text=name)

                        # check population_size and elitism
                        if phaenotyp.population_size*0.5 > phaenotyp.elitism:
                            box_ga.operator("wm.ga_start", text="Start")
                        else:
                            box_ga.label(text="Elitism should be smaller than 50% of population size.")

                        if len(data["ga_individuals"]) > 0 and not bpy.context.screen.is_animation_playing:
                            box_ga.prop(phaenotyp, "ga_ranking", text="Result sorted by fitness.")
                            if phaenotyp.ga_ranking >= len(data["ga_individuals"]):
                                text = "Only " + str(len(data["ga_individuals"])) + " available."
                                box_ga.label(text=text)
                            else:
                                # show
                                box_ga.operator("wm.ga_ranking", text="Generate")

                    # Visualization
                    if data["process"]["done"]:
                        # hide previous boxes
                        # (to avoid confusion, if user is changing the setup
                        # the setup and the result would not match
                        # new setup needs new calculation by pressing reset)
                        box_support.enabled = False
                        box_profile.enabled = False
                        box_load.enabled = False

                        try:
                            box_scipy.enabled = False
                        except:
                            pass

                        box_viz = layout.box()
                        box_viz.label(text="Vizualisation:")
                        box_viz.prop(phaenotyp, "forces", text="Force")

                        # sliders to scale forces and deflection
                        box_viz.prop(phaenotyp, "viz_scale", text="scale", slider=True)
                        box_viz.prop(phaenotyp, "viz_deflection", text="deflected / original", slider=True)

                        # Text
                        box_text = layout.box()
                        box_text.label(text="Result:")

                        selected_objects = bpy.context.selected_objects
                        if len(selected_objects) > 1:
                            box_text.label(text="Please select the vizualisation object only - too many objects")

                        elif len(selected_objects) == 0:
                                box_text.label(text="Please select the vizualisation object - no object selected")

                        elif selected_objects[0].name_full != "<Phaenotyp>member":
                                box_text.label(text="Please select the vizualisation object - wrong object selected")

                        else:
                            if context.active_object.mode == 'EDIT':
                                vert_sel = bpy.context.active_object.data.total_vert_sel
                                if vert_sel != 1:
                                    box_text.label(text="Select one vertex only")

                                else:
                                    box_text.operator("wm.text", text="Generate")
                                    if len(data["texts"]) > 0:
                                        for text in data["texts"]:
                                            box_text.label(text=text)
                            else:
                                box_text.label(text="Switch to edit-mode")

                        # Report
                        box_report = layout.box()
                        box_report.label(text="Report:")
                        if bpy.data.is_saved:
                            box_report.operator("wm.report", text="Generate")
                        else:
                            box_report.label(text="Please save Blender-File first")


        box_reset = layout.box()
        box_reset.operator("wm.reset", text="Reset")

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

    WM_OT_ga_start,
    WM_OT_ga_ranking,

    WM_OT_text,
    WM_OT_report,

    WM_OT_reset,
    OBJECT_PT_Phaenotyp
)

@persistent
def update_post(scene):
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]

    geometry.update_members_pre()

    # Analyze Animation
    if data["process"]["calculate_update_post"]:
        calculation.transfer_analyze()

        # avoid to repeat at end
        if bpy.context.scene.frame_end == bpy.context.scene.frame_current:
            bpy.ops.screen.animation_cancel()
            data["process"]["calculate_update_post"] = False
            print_data("calculation - done")

    # Genetic Mutation (Analys in fitness function)
    if data["process"]["genetetic_mutation_update_post"]:
        ga.update()
        # avoid to repeat at end
        if bpy.context.scene.frame_end == bpy.context.scene.frame_current:
            bpy.ops.screen.animation_cancel()
            data["process"]["genetetic_mutation_update_post"] = False
            print_data("calculation - done")

    geometry.update_members_post()

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
