import bpy
import bmesh
import random
from phaenotyp import geometry, calculation

def print_data(text):
    print("Phaenotyp |", text)

def create_indivdual(chromosome):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]
    frame = bpy.context.scene.frame_current

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # apply shape keys
    for id, key in enumerate(shape_keys):
        if id > 0: # to exlude basis
            key.value = chromosome[id-1]*0.1

    # get fitness
    calculation.transfer_analyze()
    if phaenotyp.ga_optimization == "simple":
        geometry.update_members_pre()
        calculation.simple_sectional()
        calculation.transfer_analyze()

    if phaenotyp.ga_optimization == "complex":
        geometry.update_members_pre()
        calculation.complex_sectional()
        calculation.transfer_analyze()

    if environment["fitness_function"] == "average_sigma":
        forces = []
        for id, member in members.items():
            force = member["max_sigma"][str(frame)]
            forces.append(force)

        # average
        sum_forces = 0
        for force in forces:
            sum_forces = sum_forces + abs(force)

        fitness = sum_forces / len(forces)

    if environment["fitness_function"] == "member_sigma":
        forces = []
        for id, member in members.items():
            force = member["max_sigma"][str(frame)]
            forces.append(force)

        fitness = return_max_diff_to_zero(forces)
        fitness = abs(fitness)

    if environment["fitness_function"] == "volume":
        dg = bpy.context.evaluated_depsgraph_get()
        obj = scene["<Phaenotyp>"]["structure"].evaluated_get(dg)
        mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)

        bm = bmesh.new()
        bm.from_mesh(mesh)

        volume = bm.calc_volume()
        negative_volume = volume * (-1) # in order to make the highest volume the best fitness
        fitness = negative_volume

    if environment["fitness_function"] == "weight":
        for id, member in members.items():
            force = member["max_sigma"][str(frame)]
            forces.append(force)

    if environment["fitness_function"] == "lever_arm_truss":
        forces = []
        for id, member in members.items():
            force = member["max_lever_arm"][str(frame)]
            forces.append(force)

        sum_forces = 0
        for force in forces:
            sum_forces = sum_forces + abs(force)

        fitness = sum_forces *(-1)

    if environment["fitness_function"] == "lever_arm_bending":
        forces = []
        for id, member in members.items():
            force = member["max_lever_arm"][str(frame)]
            forces.append(force)

        sum_forces = 0
        for force in forces:
            sum_forces = sum_forces + abs(force)

        fitness = sum_forces

    individual = {}
    individual["name"] = str(frame) # individuals are identified by frame
    individual["chromosome"] = chromosome
    individual["fitness"] = fitness
    individuals[str(frame)] = individual

    text = "new individual frame:" + str(frame) + " " + str(chromosome) + ", fitness: " + str(fitness)
    print_data(text)

def mate_chromosomes(chromosome_1, chromosome_2):
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # chromosome for offspring
    child_chromosome = []
    for gp1, gp2 in zip(chromosome_1, chromosome_2):

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
            child_chromosome.append(random.choice(environment["genes"]))

    return child_chromosome

def update():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]
    frame = bpy.context.scene.frame_current

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    if environment["ga_state"] == "create initial population":
        if len(individuals) < environment["population_size"]:
            # create chromosome with set of shapekeys (random for first population)
            chromosome = []
            for gnome_len in range(len(shape_keys)-1): # -1 to exlude basis
                gene = random.choice(environment["genes"])
                chromosome.append(gene)

            create_indivdual(chromosome)

        else:
            environment["ga_state"] = "create new generation"


    if environment["ga_state"] == "create new generation":
        # sort previous population according to fitness
        list_result = []
        for name, individual in individuals.items():
            list_result.append([name, individual["chromosome"], individual["fitness"]])

        sorted_list = sorted(list_result, key = lambda x: x[2])

        print_data("Sorted population:")
        for individual in sorted_list:
            name = individual[0]
            chromosome = individual[1]
            fitness = individual[2]

            # copy individuals to population (can't be appended)
            individual = {}
            individual["name"] = name # indiviuals are identified by the frame
            individual["chromosome"] = chromosome
            individual["fitness"] = fitness
            environment["population"][name] = individual

            text = "individual" + name + " with fitness " + str(fitness)
            print_data(text)


        # for first run only
        if environment["best"] == None:
            name = list(environment["population"].keys())[0] # get first element
            environment["best"] = environment["population"][name]


        # replace overall best of all generations
        for id, individual in individuals.items():
            if individual["fitness"] < environment["best"]["fitness"]:
                environment["best"] = individual

        text = "best individual: " + str(environment["best"]["name"]) + " with fitness: " + str(environment["best"]["fitness"])
        print_data(text)


        # create empty list of a new generation
        new_generation = []
        text = "generation " + str(environment["generation_id"]) + ":"
        print_data(text)

        # copy fittest ten percent directly
        for i in range(environment["elitism"]):
            name = list(environment["population"].keys())[i] # get nth element
            individual = individuals[name]
            environment["new_generation"][name] = individual

        environment["ga_state"] = "populate new generation"


    if environment["ga_state"] == "populate new generation":
        if len(environment["new_generation"]) < environment["new_generation_size"]:
            # pair best 50 % of the previous population
            random_number_1 = random.randint(0, int(len(environment["population"])*0.5))
            random_number_2 = random.randint(0, int(len(environment["population"])*0.5))

            parent_1_name = list(environment["population"].keys())[random_number_1]
            parent_2_name = list(environment["population"].keys())[random_number_2]

            parent_1 = individuals[parent_1_name]
            parent_2 = individuals[parent_2_name]

            chromosome = mate_chromosomes(parent_1["chromosome"], parent_2["chromosome"])

            create_indivdual(chromosome)
            name = str(frame)
            individual = individuals[name]
            environment["new_generation"][name] = individual # append to new_generation

        if len(environment["new_generation"]) == environment["new_generation_size"]:

            # replace population with new_generation
            environment["population"] = {}
            for id, individual in environment["new_generation"].items():
                environment["population"][id] = individual

            environment["new_generation"] = {}
            environment["generation_id"] += 1

            # start new generation
            environment["ga_state"] = "create new generation"

def goto_indivual():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    ranking_pos = phaenotyp.ga_ranking

    data = scene["<Phaenotyp>"]
    data["process"]["genetetic_mutation_update_post"] = False # turns ga off, if user interrupted

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # sort by fitness
    list_result = []
    for name, individual in individuals.items():
        list_result.append([name, individual["chromosome"], individual["fitness"]])

    sorted_list = sorted(list_result, key = lambda x: x[2])
    ranked_indiviual = sorted_list[ranking_pos]

    text = str(ranking_pos) + ". ranked with fitness: " + str(ranked_indiviual[2])
    print_data(text)

    frame_to_switch_to = int(ranked_indiviual[0])

    bpy.context.scene.frame_current = frame_to_switch_to