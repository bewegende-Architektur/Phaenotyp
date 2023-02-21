import bpy
import bmesh
import random
from phaenotyp import basics, geometry, calculation, progress

def print_data(text):
    print("Phaenotyp |", text)

def generate_basis():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # create list of trusses
    trusses = {}

    # create chromosome all set to 0
    chromosome = []
    for gnome_len in range(len(shape_keys)-1): # -1 to exlude basis
        gene = 0
        chromosome.append(gene)

    # update scene
    bpy.context.scene.frame_current = 0
    bpy.context.view_layer.update()

    create_indivdual(chromosome, None, None) # and change frame to shape key

    # calculate new properties for each member
    geometry.update_members_pre()

    # created a truss object of PyNite and add to dict
    truss = calculation.prepare_fea()
    trusses[0] = truss

    # run mp and get results
    feas = calculation.run_mp(trusses)

    # wait for it and interweave results to data
    calculation.interweave_results(feas, members)

def create_indivdual(chromosome, parent_1, parent_2):
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

    individual = {}
    individual["name"] = str(frame) # individuals are identified by frame
    individual["chromosome"] = chromosome

    individual["parent_1"] = str(parent_1)
    individual["parent_2"] = str(parent_2)
    individual["fitness"] = {}

    individuals[str(frame)] = individual

def calculate_fitness(start, end):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # calculate fitness
    for frame in range(start, end):
        individual = individuals[str(frame)]

        # average_sigma
        forces = []
        for id, member in members.items():
            force = member["max_sigma"][str(frame)]
            forces.append(force)

        sum_forces = 0
        for force in forces:
            sum_forces = sum_forces + abs(force)

        fitness_average_sigma = sum_forces / len(forces)

        # average_strain_energy
        forces = []
        for id, member in members.items():
            values = []
            for value in member["strain_energy"][str(frame)]:
                values.append(value)
            force = basics.return_max_diff_to_zero(values)
            forces.append(force)

        sum_forces = 0
        for force in forces:
            sum_forces = sum_forces + abs(force)

        fitness_average_strain_energy = sum_forces / len(forces)

        # volume
        volume = data["frames"][str(frame)]["volume"]
        negative_volume = volume * (-1) # in order to make the highest volume the best fitness
        fitness_volume = negative_volume # solved by value

        # area
        area = data["frames"][str(frame)]["area"]
        negative_area = area * (-1) # just like volume
        fitness_area = negative_area # solved by value

        # kg
        kg = data["frames"][str(frame)]["kg"]
        negative_kg = kg * (-1) # just like volume
        fitness_kg = negative_kg # solved by value


        '''
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
        '''

        # pass to individual
        individual["fitness"]["average_sigma"] = fitness_average_sigma
        individual["fitness"]["average_strain_energy"] = fitness_average_strain_energy
        individual["fitness"]["volume"] = fitness_volume
        individual["fitness"]["area"] = fitness_area
        individual["fitness"]["kg"] = fitness_kg


        if frame != 0:
            # get from basis
            basis_fitness = individuals["0"]["fitness"]

            # the values of weighted at basis is 1, all other frames are weighted to this value
            weighted = basics.avoid_div_zero(1, basis_fitness["average_sigma"]) * fitness_average_sigma * phaenotyp.fitness_average_sigma
            weighted += basics.avoid_div_zero(1, basis_fitness["average_strain_energy"]) * fitness_average_strain_energy * phaenotyp.fitness_average_strain_energy
            weighted += basics.avoid_div_zero(1, basis_fitness["volume"]) * fitness_volume * phaenotyp.fitness_volume
            weighted += basics.avoid_div_zero(1, basis_fitness["area"]) * fitness_volume * phaenotyp.fitness_area
            weighted += basics.avoid_div_zero(1, basis_fitness["kg"]) * fitness_volume * phaenotyp.fitness_kg

            # if all sliders are set to one, the weight is 5 (with 5 fitness sliders)
            weight = phaenotyp.fitness_average_sigma
            weight += phaenotyp.fitness_average_strain_energy
            weight += phaenotyp.fitness_volume
            weight += phaenotyp.fitness_area
            weight += phaenotyp.fitness_kg

            # the over all weighted-value is always 1 for the basis individual
            individual["fitness"]["weighted"] = basics.avoid_div_zero(weighted, weight)

def mate_chromosomes(chromosome_1, chromosome_2):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    if phaenotyp.mate_type == "direct":
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

    if phaenotyp.mate_type == "morph":
        # chromosome for offspring
        child_chromosome = []
        for gp1, gp2 in zip(chromosome_1, chromosome_2):

            # random probability
            prob = random.random()

            # if prob is less than 0.9, morph genes from parents
            if prob < 0.90:
                morph = (gp1 + gp2)*0.5
                child_chromosome.append(morph)

            # otherwise insert random gene(mutate) to maintain diversity
            else:
                child_chromosome.append(random.choice(environment["genes"]))

    return child_chromosome

def bruteforce(chromosomes):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # create list of trusses
    trusses = {}

    # for progress
    end = bpy.context.scene.frame_end

    for i, chromosome in enumerate(chromosomes):
        # update scene
        frame = i+1  # exclude basis indivual
        bpy.context.scene.frame_current = frame
        bpy.context.view_layer.update()

        # no parents in bruteforce
        parent_1, parent_2 = [None, None]
        create_indivdual(chromosome, parent_1, parent_2 ) # and change frame to shape key

        create_indivdual(chromosome, None, None) # and change frame to shape key

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()
        trusses[frame] = truss

    # run mp and get results
    feas = calculation.run_mp(trusses)

    # wait for it and interweave results to data
    calculation.interweave_results(feas, members)

def create_initial_individuals(start, end):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # create list of trusses
    trusses = {}

    for frame in range(start, end):
        # create chromosome with set of shapekeys (random for first generation)
        chromosome = []
        for gnome_len in range(len(shape_keys)-1): # -1 to exlude basis
            gene = random.choice(environment["genes"])
            chromosome.append(gene)

        # update scene
        bpy.context.scene.frame_current = frame
        bpy.context.view_layer.update()

        create_indivdual(chromosome, None, None) # and change frame to shape key

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()
        trusses[frame] = truss

    # run mp and get results
    feas = calculation.run_mp(trusses)

    # wait for it and interweave results to data
    calculation.interweave_results(feas, members)

def sectional_optimization(start, end):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    new_generation_size = environment["new_generation_size"]
    generation_id = environment["generation_id"]

    # create list of trusses
    trusses = {}

    for frame in range(start, end):
        # update scene
        bpy.context.scene.frame_current = frame
        bpy.context.view_layer.update()

        if phaenotyp.ga_optimization == "simple":
            calculation.simple_sectional()

        if phaenotyp.ga_optimization == "utilization":
            calculation.utilization_sectional()

        if phaenotyp.ga_optimization == "complex":
            calculation.complex_sectional()

        # apply shape keys
        chromosome = individuals[str(frame)]["chromosome"]
        for id, key in enumerate(shape_keys):
            if id > 0: # to exlude basis
                key.value = chromosome[id-1]*0.1

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()
        trusses[frame] = truss

    # run mp and get results
    feas = calculation.run_mp(trusses)

    # wait for it and interweave results to data
    calculation.interweave_results(feas, members)

def populate_initial_generation():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

     # create initial generation
    environment["generations"]["0"] = {} # create dict
    initial_generation = environment["generations"]["0"]

    # copy to generation
    for name, individual in individuals.items():
        # get data from individual
        chromosome = individual["chromosome"]
        fitness = individual["fitness"]
        parent_1 = individual["parent_1"]
        parent_2 = individual["parent_2"]

        # copy individual to next generation
        individual_copy = {}
        individual_copy["name"] = name
        individual_copy["chromosome"] = chromosome
        individual_copy["fitness"] = fitness
        individual_copy["parent_1"] = parent_1
        individual_copy["parent_2"] = parent_2

        initial_generation[name] = individual_copy

        # get text from chromosome for printing
        str_chromosome = "["
        for gene in individual["chromosome"]:
            str_chromosome += str(round(gene, 3))
            str_chromosome += ", "
        str_chromosome = str_chromosome[:-2]
        str_chromosome += "]"

        # print info
        text = "individual: " + str(individual["name"]) + " "
        text += str_chromosome + ", fitness: " + str(individual["fitness"]["weighted"])
        print_data(text)

def do_elitism():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]
    generation_id = data["ga_environment"]["generation_id"]

    # the current generation
    current_generation = environment["generations"][str(generation_id)]

    # sort current generation according to fitness
    list_result = []
    for name, individual in current_generation.items():
        list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

    sorted_list = sorted(list_result, key = lambda x: x[2])

    # the next generation
    generation_id = generation_id + 1 # increase id
    data["ga_environment"]["generation_id"] = generation_id # += would not working

    environment["generations"][str(generation_id)] = {} # create dict
    next_generation = environment["generations"][str(generation_id)]

    # copy fittest ten percent directly
    for i in range(environment["elitism"]):
        # name of nth best individual
        name = sorted_list[i][0]

        # get individual
        individual = individuals[name]

        # get data from individual
        chromosome = individual["chromosome"]
        fitness = individual["fitness"]
        parent_1 = individual["parent_1"]
        parent_2 = individual["parent_2"]

        # copy individual to next generation
        individual_copy = {}
        individual_copy["name"] = name
        individual_copy["chromosome"] = chromosome
        individual_copy["fitness"] = fitness
        individual_copy["parent_1"] = parent_1
        individual_copy["parent_2"] = parent_2

        next_generation[name] = individual_copy

        # get text from chromosome for printing
        str_chromosome = "["
        for gene in individual["chromosome"]:
            str_chromosome += str(round(gene, 3))
            str_chromosome += ", "
        str_chromosome = str_chromosome[:-2]
        str_chromosome += "]"

        # print info
        text = "elitism: " + str(individual["name"]) + " "
        text += str_chromosome + ", fitness: " + str(individual["fitness"]["weighted"])
        print_data(text)

def create_new_individuals(start, end):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    new_generation_size = environment["new_generation_size"]
    generation_id = environment["generation_id"]

    old_generation = environment["generations"][str(generation_id-1)]

    # create list of trusses
    trusses = {}

    for frame in range(start, end):
        # pair best 50 % of the previous generation
        # sample is used to avoid same random numbers
        random_numbers = random.sample(range(int(new_generation_size*0.5)), 2)
        parent_1_name = list(old_generation.keys())[random_numbers[0]]
        parent_2_name = list(old_generation.keys())[random_numbers[1]]

        parent_1 = individuals[parent_1_name]
        parent_2 = individuals[parent_2_name]

        chromosome = mate_chromosomes(parent_1["chromosome"], parent_2["chromosome"])

        # update scene
        bpy.context.scene.frame_current = frame
        bpy.context.view_layer.update()

        # and change frame to shape key - save name of parents for tree
        create_indivdual(chromosome, parent_1_name, parent_2_name)

        # calculate new properties for each member
        geometry.update_members_pre()

        # created a truss object of PyNite and add to dict
        truss = calculation.prepare_fea()
        trusses[frame] = truss

    # run mp and get results
    feas = calculation.run_mp(trusses)

    # wait for it and interweave results to data
    calculation.interweave_results(feas, members)

def populate_new_generation(start, end):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    new_generation_size = environment["new_generation_size"]
    generation_id = environment["generation_id"]

    # the current generation, that was created in do_elitism
    generation = environment["generations"][str(generation_id)]

    # copy to generations
    for name, individual in individuals.items():
        for frame in range(start, end):
            # get from individuals
            if str(frame) == name:
                # get individual
                individual = individuals[name]

                # get data from individual
                chromosome = individual["chromosome"]
                fitness = individual["fitness"]
                parent_1 = individual["parent_1"]
                parent_2 = individual["parent_2"]

                # copy individual to next generation
                individual_copy = {}
                individual_copy["name"] = name
                individual_copy["chromosome"] = chromosome
                individual_copy["fitness"] = fitness
                individual_copy["parent_1"] = parent_1
                individual_copy["parent_2"] = parent_2

                generation[name] = individual_copy

                # get text from chromosome for printing
                str_chromosome = "["
                for gene in individual["chromosome"]:
                    str_chromosome += str(round(gene, 3))
                    str_chromosome += ", "
                str_chromosome = str_chromosome[:-2]
                str_chromosome += "]"

                # print info
                text = "child: " + str(individual["name"]) + " "
                text += str_chromosome + ", fitness: " + str(individual["fitness"]["weighted"])
                print_data(text)

def goto_indivual():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    ranking_pos = phaenotyp.ga_ranking

    data = scene["<Phaenotyp>"]
    # turns ga off, if user interrupted the process
    data["process"]["genetetic_mutation_update_post"] = False

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    # sort by fitness
    list_result = []
    for name, individual in individuals.items():
        list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

    sorted_list = sorted(list_result, key = lambda x: x[2])
    ranked_indiviual = sorted_list[ranking_pos]

    text = str(ranking_pos) + ". ranked with fitness: " + str(ranked_indiviual[2])
    print_data(text)

    frame_to_switch_to = int(ranked_indiviual[0])

    bpy.context.scene.frame_current = frame_to_switch_to
