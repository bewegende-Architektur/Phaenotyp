import bpy

import os
import webbrowser

from phaenotyp import basics, material, geometry, calculation, ga, report, progress
import itertools

def print_data(text):
    print("Phaenotyp |", text)

def set_structure():
    context = bpy.context
    scene = context.scene

    selected_objects = context.selected_objects
    obj = context.active_object

    # more than two objects
    if len(selected_objects) > 1:
        if obj.type == 'CURVE':
            text = ["The selection is of typ curve.",
                "Should Phaenotyp try to convert the selection to mesh?"]
            basics.popup_operator(lines=text, operator="wm.fix_structure", text="Convert curves to mesh")
            basics.to_be_fixed = "curve_to_mesh"

        else:
            text = ["Select multiple curves or a mesh only."]
            basics.popup(lines = text)

    # one object
    else:
        # mesh or curve
        if obj.type not in ['CURVE', 'MESH']:
            text = ["Select multiple curves or a mesh only."]
            basics.popup(lines = text)

        else:
            if obj.type == 'CURVE':
                text = ["The selection is of typ curve.",
                    "Should Phaenotyp try to convert the selection to mesh?"]
                basics.popup_operator(lines=text, operator="wm.fix_structure", text="Convert curve to mesh")
                basics.to_be_fixed = "curve_to_mesh"

            else:
                bpy.ops.object.mode_set(mode="EDIT")

                amount_of_mesh_parts = basics.amount_of_mesh_parts()
                amount_of_loose_parts = basics.amount_of_loose_parts()

                if amount_of_mesh_parts > 1:
                    text = [
                        "The mesh contains " + str(amount_of_mesh_parts) + " parts.",
                        "Should Phaenotyp try to fix this?"]
                    basics.popup_operator(lines=text, operator="wm.fix_structure", text="Delete or seperate loose parts")
                    basics.to_be_fixed = "seperate_by_loose"

                elif amount_of_loose_parts > 0:
                    text = [
                        "The mesh contains loose elements: " + str(amount_of_loose_parts),
                        "Should Phaenotyp try to fix this?"]
                    basics.popup_operator(lines=text, operator="wm.fix_structure", text="Delete loose parts")
                    basics.to_be_fixed = "delete_loose"

                # everything looks ok
                else:
                    # crete / recreate collection
                    basics.delete_col_if_existing("<Phaenotyp>")
                    collection = bpy.data.collections.new("<Phaenotyp>")
                    bpy.context.scene.collection.children.link(collection)

                    basics.create_data()

                    basics.to_be_fixed = None
                    data = scene["<Phaenotyp>"]
                    data["structure"] = obj

                    # check for scipy
                    calculation.check_scipy()

def fix_structure():
    if basics.to_be_fixed == "seperate_by_loose":
        print_data("Seperate by loose parts")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')

    elif basics.to_be_fixed == "curve_to_mesh":
        print_data("Try to convert the curves to mesh")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.join()
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode='OBJECT')

    elif basics.to_be_fixed == "delete_loose":
        print_data("Delete loose parts")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode='OBJECT')

    else:
        print_data("No idea to fix this")

def set_support():
    context = bpy.context
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

def set_profile():
    scene = bpy.context.scene
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

    # to avoid key-error in optimization
    data["done"][str(frame)] = False

def set_load():
    scene = bpy.context.scene
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

def calculate_single_frame():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = scene["<Phaenotyp>"]["members"]
    frame = bpy.context.scene.frame_current

    try:
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
    except Exception as exception:
        print_data(exception.__class__.__name__)
        text = [
            "It looks like the structure is unstable.",
            "Are there any loose parts?",
            "",
            "Maybe you can solve this by doing:",
            "- Mesh | Clean up | Delete loose parts.",
            "- Mesh | Clean up | Merge by distance."]
        basics.popup(lines = text)

def calculate_animation():
    scene = bpy.context.scene
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

    try:
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
    except Exception as exception:
        print_data(exception.__class__.__name__)
        text = [
            "It looks like the structure is unstable.",
            "Are there any loose parts?",
            "",
            "Maybe you can solve this by doing:",
            "- Mesh | Clean up | Delete loose parts.",
            "- Mesh | Clean up | Merge by distance."]
        basics.popup(lines = text)

    # join progress
    progress.http.active = False
    progress.http.Thread_hosting.join()

def optimize_simple():
    scene = bpy.context.scene
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

def optimize_utilization():
    scene = bpy.context.scene
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

def optimize_complex():
    scene = bpy.context.scene
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

def topolgy_decimate():
    print_data("optimization 3 - Decimate topological performance")
    calculation.decimate_topology()

def ga_start():
    scene = bpy.context.scene
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

def ga_ranking():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]

    print_data("go to selected ranking")

    ga.goto_indivual()

def ga_render_animation():
    scene = bpy.context.scene
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

def text():
    scene = bpy.context.scene
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

def report_members():
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

def report_frames():
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

def report_chromosomes():
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

def report_tree():
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

def reset():
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

    # change view back to solid ...
    basics.revert_vertex_colors()
