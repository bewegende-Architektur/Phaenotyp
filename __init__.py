bl_info = {
    "name": "Phänotyp",
    "description": "Genetic optimization of architectural structures",
    "author": "bewegende Architektur e.U. and Karl Deix",
    "version": (0, 1, 5),
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

from phaenotyp import basics, operators, material, geometry, calculation, ga, report, progress

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
        operators.set_structure()
        return {"FINISHED"}

class WM_OT_set_support(Operator):
    bl_label = "set_support"
    bl_idname = "wm.set_support"
    bl_description = "Please select vertices and press set, to define them as support (Be sure, that you are in Edit Mode of the Structure)"

    def execute(self, context):
        operators.set_support()
        return {"FINISHED"}

class WM_OT_set_profile(Operator):
    bl_label = "set_profile"
    bl_idname = "wm.set_profile"
    bl_description = "Please select edges in Edit-Mode and press set, to define profiles"

    def execute(self, context):
        operators.set_profile()
        return {"FINISHED"}

class WM_OT_set_load(Operator):
    bl_label = "set_load"
    bl_idname = "wm.set_load"
    bl_description = "Add load to selected vertices, edges, or faces"

    def execute(self, context):
        operators.set_load()
        return {"FINISHED"}

class WM_OT_calculate_single_frame(Operator):
    bl_label = "calculate_single_frame"
    bl_idname = "wm.calculate_single_frame"
    bl_description = "Calulate single frame"

    def execute(self, context):
        operators.calculate_single_frame()
        return {"FINISHED"}

class WM_OT_calculate_animation(Operator):
    bl_label = "calculate_animation"
    bl_idname = "wm.calculate_animation"
    bl_description = "Calulate animation"

    def execute(self, context):
        operators.calculate_animation()
        return {"FINISHED"}

class WM_OT_optimize_simple(Operator):
    bl_label = "optimize_simple"
    bl_idname = "wm.optimize_simple"
    bl_description = "Simple sectional performance"

    def execute(self, context):
        operators.optimize_simple()
        return {"FINISHED"}

class WM_OT_optimize_utilization(Operator):
    bl_label = "optimize_utilization"
    bl_idname = "wm.optimize_utilization"
    bl_description = "utilization sectional performance"

    def execute(self, context):
        operators.optimize_utilization()
        return {"FINISHED"}

class WM_OT_optimize_complex(Operator):
    bl_label = "optimize_complex"
    bl_idname = "wm.optimize_complex"
    bl_description = "Complex sectional performance"

    def execute(self, context):
        operators.optimize_complex()
        return {"FINISHED"}

class WM_OT_topology_1(Operator):
    bl_label = "topolgy_decimate"
    bl_idname = "wm.topolgy_decimate"
    bl_description = "Decimate topological performance"

    def execute(self, context):
        operators.topolgy_decimate()
        return {"FINISHED"}

class WM_OT_ga_start(Operator):
    bl_label = "ga_start"
    bl_idname = "wm.ga_start"
    bl_description = "Start genetic muatation over selected shape keys"

    def execute(self, context):
        operators.ga_start()
        return {"FINISHED"}

class WM_OT_ga_ranking(Operator):
    bl_label = "ga_ranking"
    bl_idname = "wm.ga_ranking"
    bl_description = "Go to indivual by ranking."

    def execute(self, context):
        operators.ga_ranking()
        return {"FINISHED"}

class WM_OT_ga_render_animation(Operator):
    bl_label = "ga_ranking"
    bl_idname = "wm.ga_render_animation"
    bl_description = "Go to indivual by ranking."

    def execute(self, context):
        operators.ga_ranking()
        return {"FINISHED"}

class WM_OT_text(Operator):
    bl_label = "text"
    bl_idname = "wm.text"
    bl_description = "Generate output at the selected vertex"

    def execute(self, context):
        operators.text()
        return {"FINISHED"}

class WM_OT_report_members(Operator):
    bl_label = "report_members"
    bl_idname = "wm.report_members"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        operators.report_members()
        return {"FINISHED"}

class WM_OT_report_frames(Operator):
    bl_label = "report_frames"
    bl_idname = "wm.report_frames"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        operators.report_frames()
        return {"FINISHED"}

class WM_OT_report_chromosomes(Operator):
    bl_label = "report_chromosomes"
    bl_idname = "wm.report_chromosomes"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        operators.report_chromosomes()
        return {"FINISHED"}

class WM_OT_report_tree(Operator):
    bl_label = "report_tree"
    bl_idname = "wm.report_tree"
    bl_description = "Generate report as html-format"

    def execute(self, context):
        operators.report_tree()
        return {"FINISHED"}

class WM_OT_reset(Operator):
    bl_label = "reset"
    bl_idname = "wm.reset"
    bl_description = "Reset Phaenotyp"

    def execute(self, context):
        operators.reset()
        return {"FINISHED"}

class OBJECT_PT_Phaenotyp(Panel):
    bl_label = "Phänotyp 0.1.5"
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
        frame = bpy.context.scene.frame_current

        # start with defining a structure
        box_structure = layout.box()
        data = bpy.context.scene.get("<Phaenotyp>")

        # check if phaenotyp created data allready
        ready_to_go = True

        if not data:
            ready_to_go = False

        else:
            structure = data.get("structure")

            # is the obj defined? Maybe someone deleted the structure after calc ...
            if not structure:
                ready_to_go = False

            else:
                # Phaenotyp started, but no structure defined by user
                if structure == None:
                    ready_to_go = False

        # user needs to define a structure
        if not ready_to_go:
            box_structure.label(text="Structure:")
            box_structure.operator("wm.set_structure", text="Set")

        else:
             # disable previous box
            box_structure.enabled = False

            obj = data["structure"]
            box_structure.label(text = obj.name_full + " is defined as structure")

            # check or uncheck scipy if available
            if data["scipy_available"]:
                box_scipy = layout.box()
                box_scipy.label(text = "Sparse matrix:")
                box_scipy.prop(phaenotyp, "use_scipy", text="Use scipy")

            # calculaton type
            box_scipy = layout.box()
            box_scipy.label(text = "Calculation type:")
            box_scipy.prop(phaenotyp, "calculation_type", text="Calculation type")

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
                box_support.label(text = str(len(data["supports"])) + " vertices defined as support.")

                # define material and geometry
                box_profile = layout.box()
                box_profile.label(text="Profile:")

                box_profile.prop(phaenotyp, "Do", text="Diameter outside")
                box_profile.prop(phaenotyp, "Di", text="Diameter inside")

                # current setting passed from gui
                # (because a property can not be set in gui)
                material.current["Do"] = phaenotyp.Do * 0.1
                material.current["Di"] = phaenotyp.Di * 0.1

                box_profile.separator()

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
                box_profile.label(text="kg = " + str(round(material.current["kg_A"], 4)) + " kg/m")

                box_profile.operator("wm.set_profile", text="Set")

                # if not all edges are defined as member
                len_structure_edges = len(data["structure"].data.edges)
                len_members = len(data["members"])
                if len_members == 0:
                    pass

                elif len_structure_edges != len_members:
                    text = str(len_members) + " edges of " + str(len_structure_edges) + " set as members."
                    box_profile.label(text=text)

                else:
                    text = str(len_members) + " edges set as members."
                    box_profile.label(text=text)

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

                    len_loads = len(data["loads_v"]) + len(data["loads_e"]) + len(data["loads_f"])
                    if len_loads > 0:
                        text = str(len_loads) + " loads defined."
                        box_load.label(text=text)

                    if phaenotyp.calculation_type != "geometrical":
                        if not bpy.data.is_saved:
                            box_file = layout.box()
                            box_file.label(text="Please save Blender-File first.")

                        else:
                            # Analysis
                            box_analysis = layout.box()
                            box_analysis.label(text="Analysis:")
                            box_analysis.operator("wm.calculate_single_frame", text="Single Frame")
                            box_analysis.operator("wm.calculate_animation", text="Animation")

                            # Optimization
                            box_opt = layout.box()
                            box_opt.label(text="Optimization:")

                            result = data["done"].get(str(frame))
                            if result:
                                box_opt.operator("wm.optimize_simple", text="Simple - sectional performance")
                                box_opt.operator("wm.optimize_utilization", text="Utilization - sectional performance")
                                box_opt.operator("wm.optimize_complex", text="Complex - sectional performance")
                            else:
                                box_opt.label(text="Run single analysis first.")

                            # Topology
                            box_opt = layout.box()
                            box_opt.label(text="Topology:")

                            result = data["done"].get(str(frame))
                            if result:
                                box_opt.operator("wm.topolgy_decimate", text="Decimate - topological performance")
                            else:
                                box_opt.label(text="Run single analysis first.")

                    shape_key = data["structure"].data.shape_keys
                    if shape_key:
                        # Genetic Mutation:
                        box_ga = layout.box()
                        box_ga.label(text="Genetic Mutation:")
                        box_ga.prop(phaenotyp, "mate_type", text="Type of mating")
                        if phaenotyp.calculation_type != "geometrical":
                            box_ga.prop(phaenotyp, "ga_optimization", text="Sectional optimization")
                            if phaenotyp.ga_optimization != "none":
                                box_ga.prop(phaenotyp, "ga_optimization_amount", text="Amount of sectional optimization")

                        if phaenotyp.mate_type in ["direct", "morph"]:
                            box_ga.prop(phaenotyp, "generation_size", text="Size of generation for GA")
                            box_ga.prop(phaenotyp, "elitism", text="Size of elitism for GA")
                            box_ga.prop(phaenotyp, "generation_amount", text="Amount of generations")

                        box_ga.separator()

                        # fitness headline
                        box_ga.label(text="Fitness function:")

                        # architectural fitness
                        col = box_ga.column()
                        split = col.split()
                        split.prop(phaenotyp, "fitness_volume", text="Volume")
                        split.prop(phaenotyp, "fitness_volume_invert", text="Invert")

                        col = box_ga.column()
                        split = col.split()
                        split.prop(phaenotyp, "fitness_area", text="Area")
                        split.prop(phaenotyp, "fitness_area_invert", text="Invert")

                        col = box_ga.column()
                        split = col.split()
                        split.prop(phaenotyp, "fitness_kg", text="Kg")
                        split.prop(phaenotyp, "fitness_kg_invert", text="Invert")

                        col = box_ga.column()
                        split = col.split()
                        split.prop(phaenotyp, "fitness_rise", text="Rise")
                        split.prop(phaenotyp, "fitness_rise_invert", text="Invert")

                        col = box_ga.column()
                        split = col.split()
                        split.prop(phaenotyp, "fitness_span", text="Span")
                        split.prop(phaenotyp, "fitness_span_invert", text="Invert")

                        col = box_ga.column()
                        split = col.split()
                        split.prop(phaenotyp, "fitness_cantilever", text="Cantilever")
                        split.prop(phaenotyp, "fitness_cantilever_invert", text="Invert")

                        # structural fitness
                        if phaenotyp.calculation_type != "geometrical":
                            box_ga.prop(phaenotyp, "fitness_average_sigma", text="Sigma")
                            box_ga.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy")

                        box_ga.separator()

                        box_ga.label(text="Shape keys:")
                        for keyblock in shape_key.key_blocks:
                            name = keyblock.name
                            box_ga.label(text=name)

                        # check generation_size and elitism
                        if phaenotyp.generation_size*0.5 > phaenotyp.elitism:
                            box_ga.operator("wm.ga_start", text="Start")
                        else:
                            box_ga.label(text="Elitism should be smaller than 50% of generation size.")

                        if len(data["ga_individuals"]) > 0 and not bpy.context.screen.is_animation_playing:
                            box_ga.separator()
                            box_ga.label(text="Select individual by fitness:")
                            box_ga.prop(phaenotyp, "ga_ranking", text="Result sorted by fitness.")
                            if phaenotyp.ga_ranking >= len(data["ga_individuals"]):
                                text = "Only " + str(len(data["ga_individuals"])) + " available."
                                box_ga.label(text=text)
                            else:
                                # show
                                box_ga.operator("wm.ga_ranking", text="Generate")

                            box_ga.separator()

                            box_ga.label(text="Render sorted indiviuals:")
                            box_ga.operator("wm.ga_render_animation", text="Generate")

                    # Visualization
                    result = data["done"].get(str(frame))
                    if result:
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
                        box_text.label(text="Volume: "+str(round(data["frames"][str(frame)]["volume"],3)) + " m³")
                        box_text.label(text="Area: "+str(round(data["frames"][str(frame)]["area"],3)) + " m²")
                        box_text.label(text="Length: "+str(round(data["frames"][str(frame)]["length"],3)) + " m")
                        box_text.label(text="Kg: "+str(round(data["frames"][str(frame)]["kg"],3)) + " kg")
                        box_text.label(text="Rise: "+str(round(data["frames"][str(frame)]["rise"],3)) + " m")
                        box_text.label(text="Span: "+str(round(data["frames"][str(frame)]["span"],3)) + " m")
                        box_text.label(text="Cantilever: "+str(round(data["frames"][str(frame)]["cantilever"],3)) + " m")

                        if phaenotyp.calculation_type != "geometrical":
                            box_text.separator()
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

                        if phaenotyp.calculation_type != "geometrical":
                            box_report.operator("wm.report_members", text="members")
                            box_report.operator("wm.report_frames", text="frames")
                        else:
                            box_report.label(text="No report for members or frames available in geometrical mode.")

                        # if ga
                        ga_available = data.get("ga_environment")
                        if ga_available:
                            box_report.operator("wm.report_chromosomes", text="chromosomes")
                            box_report.operator("wm.report_tree", text="tree")


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

    WM_OT_optimize_simple,
    WM_OT_optimize_utilization,
    WM_OT_optimize_complex,
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
    OBJECT_PT_Phaenotyp
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

            result = data["done"].get(str(frame))
            if result:
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
