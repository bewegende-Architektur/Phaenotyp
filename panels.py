import bpy
from phaenotyp import material

def structure(layout, phaenotyp, frame):
    box = layout.box()
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
        box.operator("wm.set_structure", text="Set")

    else:
        obj = data["structure"]
        box.label(text = obj.name_full + " is defined as structure")

        # gray out if done
        box.enabled = False

def scipy(data, layout, phaenotyp, frame):
    box = layout.box()
    if data["scipy_available"]:
        box.prop(phaenotyp, "use_scipy", text="Use scipy")
    else:
        box.label(text = "Using internal python.")

    # gray out if done
    done = data["done"].get(str(frame))
    if done:
        box.enabled = False

def calculation_type(data, layout, phaenotyp, frame):
    box = layout.box()
    box.prop(phaenotyp, "calculation_type", text="Type:")

    # gray out if done
    done = data["done"].get(str(frame))
    if done:
        box.enabled = False

def support(data, layout, phaenotyp, frame):
    box = layout.box()

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

    supports = data.get("supports")
    if supports:
        box.label(text = str(len(data["supports"])) + " vertices defined as support")

    # gray out if done
    done = data["done"].get(str(frame))
    if done:
        box.enabled = False

def profile(data, layout, phaenotyp, frame):
    box = layout.box()
    box.prop(phaenotyp, "Do", text="Diameter outside")
    box.prop(phaenotyp, "Di", text="Diameter inside")

    # current setting passed from gui
    # (because a property can not be set in gui)
    material.current["Do"] = phaenotyp.Do * 0.1
    material.current["Di"] = phaenotyp.Di * 0.1

    box.label(text="Material:")
    box.prop(phaenotyp, "material", text="Type")
    if phaenotyp.material == "custom":
        box.prop(phaenotyp, "E", text="Modulus of elasticity")
        box.prop(phaenotyp, "G", text="Shear modulus")
        box.prop(phaenotyp, "d", text="Density")

        box.prop(phaenotyp, "acceptable_sigma", text="Acceptable sigma")
        box.prop(phaenotyp, "acceptable_shear", text="Acceptable shear")
        box.prop(phaenotyp, "acceptable_torsion", text="Acceptable torsion")
        box.prop(phaenotyp, "acceptable_sigmav", text="Acceptable sigmav")
        box.prop(phaenotyp, "ir", text="Ir")

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


        box.label(text="E = " + str(material.current["E"]) + " kN/cm²")
        box.label(text="G = " + str(material.current["G"]) + " kN/cm²")
        box.label(text="d = " + str(material.current["d"]) + " g/cm3")

        box.label(text="Acceptable sigma = " + str(material.current["acceptable_sigma"]))
        box.label(text="Acceptable shear = " + str(material.current["acceptable_shear"]))
        box.label(text="Acceptable torsion = " + str(material.current["acceptable_torsion"]))
        box.label(text="Acceptable sigmav = " + str(material.current["acceptable_sigmav"]))

    material.update() # calculate Iy, Iz, J, A, kg
    box.label(text="Iy = " + str(round(material.current["Iy"], 4)) + " cm⁴")
    box.label(text="Iz = " + str(round(material.current["Iz"], 4)) + " cm⁴")
    box.label(text="J = " + str(round(material.current["J"], 4)) + " cm⁴")
    box.label(text="A = " + str(round(material.current["A"], 4)) + " cm²")
    box.label(text="kg = " + str(round(material.current["kg_A"], 4)) + " kg/m")

    box.operator("wm.set_profile", text="Set")

    # gray out if done
    done = data["done"].get(str(frame))
    if done:
        box.enabled = False

def load(data, layout, phaenotyp, frame):
    box = layout.box()
    box.prop(phaenotyp, "load_type", text="Type")

    if phaenotyp.load_type == "faces": # if faces
        box.prop(phaenotyp, "load_normal", text="normal (like wind)")
        box.prop(phaenotyp, "load_projected", text="projected (like snow)")
        box.prop(phaenotyp, "load_area_z", text="area z (like weight of facade)")

    else: # if vertices or edges
        box.prop(phaenotyp, "load_x", text="x")
        box.prop(phaenotyp, "load_y", text="y")
        box.prop(phaenotyp, "load_z", text="z")

    box.operator("wm.set_load", text="Set")

    # gray out if done
    done = data["done"].get(str(frame))
    if done:
        box.enabled = False

def analysis(data, layout, phaenotyp, frame):
    box = layout.box()
    if bpy.context.scene.phaenotyp.calculation_type != "geometrical":
        if not bpy.data.is_saved:
            box.label(text="Please save Blender-File first")

        else:
            box.operator("wm.calculate_single_frame", text="Single Frame")
            box.operator("wm.calculate_animation", text="Animation")
    else:
        box.label(text="No analysis available in geometrical mode.")

def optimization(data, layout, phaenotyp, frame):
    box = layout.box()
    if bpy.context.scene.phaenotyp.calculation_type != "geometrical":
        done = data["done"].get(str(frame))
        if done:
            box.label(text="Sectional performance:")
            box.operator("wm.optimize_1", text="Simple - sectional performance")
            box.operator("wm.optimize_2", text="Utilization - sectional performance")
            box.operator("wm.optimize_3", text="Complex - sectional performance")

            # Topology
            box = layout.box()
            box.label(text="Topology:")
            box.operator("wm.topolgy_1", text="Decimate - topological performance")

        else:
            box.label(text="Run analysis first.")

    else:
        box.label(text="No optimization available in geometrical mode.")

def ga(data, layout, phaenotyp, frame):
    box = layout.box()
    shape_key = data["structure"].data.shape_keys
    if not shape_key:
        box.label(text="Create at least two shape keys (basis and another).")
    else:
        # Genetic Mutation:
        box.label(text="Mate type:")
        box.prop(phaenotyp, "mate_type", text="Type of mating")
        if phaenotyp.calculation_type != "geometrical":
            box.prop(phaenotyp, "ga_optimization", text="Sectional optimization")
            if phaenotyp.ga_optimization != "none":
                box.prop(phaenotyp, "ga_optimization_amount", text="Amount of sectional optimization")

        if phaenotyp.mate_type in ["direct", "morph"]:
            box.prop(phaenotyp, "generation_size", text="Size of generation for GA")
            box.prop(phaenotyp, "elitism", text="Size of elitism for GA")
            box.prop(phaenotyp, "generation_amount", text="Amount of generations")

        # fitness headline
        box = layout.box()
        box.label(text="Fitness function:")

        # architectural fitness
        col = box.column()
        split = col.split()
        split.prop(phaenotyp, "fitness_volume", text="Volume")
        split.prop(phaenotyp, "fitness_volume_invert", text="Invert")

        col = box.column()
        split = col.split()
        split.prop(phaenotyp, "fitness_area", text="Area")
        split.prop(phaenotyp, "fitness_area_invert", text="Invert")

        col = box.column()
        split = col.split()
        split.prop(phaenotyp, "fitness_kg", text="Kg")
        split.prop(phaenotyp, "fitness_kg_invert", text="Invert")

        col = box.column()
        split = col.split()
        split.prop(phaenotyp, "fitness_rise", text="Rise")
        split.prop(phaenotyp, "fitness_rise_invert", text="Invert")

        col = box.column()
        split = col.split()
        split.prop(phaenotyp, "fitness_span", text="Span")
        split.prop(phaenotyp, "fitness_span_invert", text="Invert")

        col = box.column()
        split = col.split()
        split.prop(phaenotyp, "fitness_cantilever", text="Cantilever")
        split.prop(phaenotyp, "fitness_cantilever_invert", text="Invert")

        # structural fitness
        if phaenotyp.calculation_type != "geometrical":
            box.prop(phaenotyp, "fitness_average_sigma", text="Sigma")
            box.prop(phaenotyp, "fitness_average_strain_energy", text="Strain energy")

        # run
        box = layout.box()
        box.label(text="Shape keys:")
        for keyblock in shape_key.key_blocks:
            name = keyblock.name
            box.label(text=name)

        # check generation_size and elitism
        if phaenotyp.generation_size*0.5 > phaenotyp.elitism:
            box.operator("wm.ga_start", text="Start")
        else:
            box.label(text="Elitism should be smaller than 50% of generation size.")

        if len(data["ga_individuals"]) > 0 and not bpy.context.screen.is_animation_playing:
            box = layout.box()
            box.label(text="Select individual by fitness:")
            box.prop(phaenotyp, "ga_ranking", text="Result sorted by fitness.")
            if phaenotyp.ga_ranking >= len(data["ga_individuals"]):
                text = "Only " + str(len(data["ga_individuals"])) + " available."
                box.label(text=text)
            else:
                # show
                box.operator("wm.ga_ranking", text="Generate")

            box = layout.box()
            box.label(text="Render sorted indiviuals:")
            box.operator("wm.ga_render_animation", text="Generate")

def viz(data, layout, phaenotyp, frame):
    box = layout.box()
    box.label(text="Type and scale:")
    box.prop(phaenotyp, "forces", text="Force")

    # sliders to scale forces and deflection
    box.prop(phaenotyp, "viz_scale", text="scale", slider=True)
    box.prop(phaenotyp, "viz_deflection", text="deflected / original", slider=True)

    # Text
    box = layout.box()
    box.label(text="Result:")
    box.label(text="Volume: "+str(round(data["frames"][str(frame)]["volume"],3)) + " m³")
    box.label(text="Area: "+str(round(data["frames"][str(frame)]["area"],3)) + " m²")
    box.label(text="Length: "+str(round(data["frames"][str(frame)]["length"],3)) + " m")
    box.label(text="Kg: "+str(round(data["frames"][str(frame)]["kg"],3)) + " kg")
    box.label(text="Rise: "+str(round(data["frames"][str(frame)]["rise"],3)) + " m")
    box.label(text="Span: "+str(round(data["frames"][str(frame)]["span"],3)) + " m")
    box.label(text="Cantilever: "+str(round(data["frames"][str(frame)]["cantilever"],3)) + " m")

    if phaenotyp.calculation_type != "geometrical":
        selected_objects = bpy.context.selected_objects
        if len(selected_objects) > 1:
            box.label(text="Please select the vizualisation object only - too many objects")

        elif len(selected_objects) == 0:
                box.label(text="Please select the vizualisation object - no object selected")

        elif selected_objects[0].name_full != "<Phaenotyp>member":
                box.label(text="Please select the vizualisation object - wrong object selected")

        else:
            if context.active_object.mode == 'EDIT':
                vert_sel = bpy.context.active_object.data.total_vert_sel
                if vert_sel != 1:
                    box.label(text="Select one vertex only")

                else:
                    box.operator("wm.text", text="Generate")
                    if len(data["texts"]) > 0:
                        for text in data["texts"]:
                            box.label(text=text)
            else:
                box.label(text="Switch to edit-mode")

def report(data, layout, phaenotyp, frame):
    box = layout.box()
    box.label(text="Report:")

    if phaenotyp.calculation_type != "geometrical":
        box.operator("wm.report_members", text="members")
        box.operator("wm.report_frames", text="frames")
    else:
        box.label(text="No report for members or frames available in geometrical mode.")

    # if ga
    ga_available = data.get("ga_environment")
    if ga_available:
        box.operator("wm.report_chromosomes", text="chromosomes")
        box.operator("wm.report_tree", text="tree")

def reset(data, layout, phaenotyp, frame):
    box = layout.box()
    box.operator("wm.reset", text="Reset")
