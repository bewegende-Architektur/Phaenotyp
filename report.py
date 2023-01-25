import bpy
from phaenotyp import basics
import shutil
import os.path

class svg_individuals:
    instances = []

    # passed
    len_keys = None
    generation_size = None
    generation_amount = None

    # scaling
    fitness_best = None
    fitness_weakest = None

    @staticmethod
    def setup():
        svg_individuals.border_left = 100
        svg_individuals.border_right = 10
        svg_individuals.border_top = 20
        svg_individuals.border_bottom = 100

        svg_individuals.line_h = 20

        svg_individuals.box_w = 80
        svg_individuals.box_h = 4*svg_individuals.line_h + svg_individuals.line_h*svg_individuals.len_keys # space, name, fitness, space, genes ...

        svg_individuals.tree_h = 80 # splines, distance between boxes

        svg_individuals.row_w = 100
        svg_individuals.col_h = svg_individuals.box_h + svg_individuals.tree_h

        svg_individuals.drawing_w = svg_individuals.border_left + svg_individuals.generation_size*svg_individuals.row_w + svg_individuals.border_right
        svg_individuals.drawing_h = svg_individuals.border_top + svg_individuals.generation_amount*svg_individuals.col_h + svg_individuals.border_bottom + svg_individuals.box_h

    @staticmethod
    def start(file):
        # style
        file.write('<style>\n')
        file.write('    .individual {\n')
        file.write('    stroke: invisible;\n')
        file.write('    stroke-width: 3;\n')
        file.write('  }\n')
        file.write('  .individual:hover {\n')
        file.write('    stroke: black;\n')
        file.write('  }\n')
        file.write('    .individual_bg {\n')
        file.write('    stroke: grey;\n')
        file.write('    stroke-width: 1;\n')
        file.write('  }\n')
        file.write('}\n')
        file.write('</style>\n\n')

        # start svg
        w, h = [str(svg_individuals.drawing_w), str(svg_individuals.drawing_h)]
        file.write('<svg width="'+w+'" height="'+h+'">\n')

    @staticmethod
    def end(file):
        # write end
        file.write('</svg\n>')
        file.write('</body\n>')
        file.write('</html\n>')
        file.close()

    @staticmethod
    def initial_generation(file):
        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        obj = data["structure"]
        shape_keys = obj.data.shape_keys.key_blocks
        members = data["members"]

        environment = data["ga_environment"]
        individuals = data["ga_individuals"]

        generation = environment["generations"]["0"]

        row_id, col_id = [0, 0]
        for name, individual in generation.items():
            chromosome = individual["chromosome"]
            fitness = individual["fitness"]["weighted"]
            origins = None
            new_individual = svg_individuals(name, chromosome, fitness, row_id, col_id, origins)
            row_id += 1

    @staticmethod
    def other_generations(file):
        scene = bpy.context.scene
        phaenotyp = scene.phaenotyp
        data = scene["<Phaenotyp>"]
        obj = data["structure"]
        shape_keys = obj.data.shape_keys.key_blocks
        members = data["members"]

        environment = data["ga_environment"]
        individuals = data["ga_individuals"]

        # all generations except of initial generation
        col_id = 1
        for generation_id in range(1, len(environment["generations"])):
            generation = environment["generations"][str(generation_id)]

            row_id = 0
            for name, individual in generation.items():
                chromosome = individual["chromosome"]
                fitness = individual["fitness"]["weighted"]
                parent_1 = individual["parent_1"]
                parent_2 = individual["parent_2"]

                # get id of parents in column above
                possible_parent_1_id = 0
                possible_parent_2_id = 0

                origins = [parent_1, parent_2]
                new_individual = svg_individuals(name, chromosome, fitness, row_id, col_id, origins)

                row_id += 1

            col_id += 1

    @staticmethod
    def loop_bgs(file):
        for individual in svg_individuals.instances:
            individual.draw_bg(file)

    @staticmethod
    def loop_vgs(file):
        for individual in svg_individuals.instances:
            individual.draw_vg(file)

    def __init__(self, name, chromosome, fitness, row_id, col_id, origins):
        self.name = name
        self.chromosome = chromosome
        self.fitness = fitness
        self.row_id = row_id
        self.col_id = col_id
        self.origins = origins

        # overall position
        self.x = svg_individuals.border_left + svg_individuals.row_w * self.row_id
        self.y = svg_individuals.border_top + svg_individuals.col_h * self.col_id

        svg_individuals.instances.append(self)

    def draw_bg(self, file):
        x = self.x
        y = self.y

        # draw dot at ovrall position
        dot_x = 'cx="' + str(x) + '" '
        dot_y = 'cy="' + str(y) + '" '
        file.write('  <circle ' + dot_x + dot_y + 'r="4" stroke="black" stroke-width="1" fill="transparent" />\n')

        # create color as str
        c = 'transparent'

        box_x = str(x - svg_individuals.box_w * 0.5) # centered
        box_y = str(y)

        box_w = str(svg_individuals.box_w)
        box_h = str(svg_individuals.box_h)

        # open individual
        file.write('  <g class="individual_bg">\n')
        file.write('    <rect x="'+box_x+'" y="'+box_y+'" width="'+box_w+'" height="'+box_h+'" fill="'+c+'"/>\n')

        # draw parents or elitism
        if self.origins != None: # to avoid error in first generation
            for origin in self.origins:
                # get svg_individual from parent
                for svg_individual in svg_individuals.instances:
                    if svg_individual.name == origin:

                        # start point at parent
                        x_1 = svg_individual.x
                        y_1 = svg_individual.y + svg_individual.box_h

                        # end point
                        x_4 = x
                        y_4 = y

                        # interpolated points
                        x_2 = x_1
                        y_2 = y_1 + svg_individual.box_h

                        x_3 = x_4
                        y_3 = y_4 - svg_individual.box_h

                        text = '<path d="M ' + str(x_1) + ' ' + str(y_1)
                        text += ' C' + str(x_2) + ', ' + str(y_2) + ' '
                        text += str(x_3) + ', ' + str(y_3) + ' '
                        text += str(x_4) + ', ' + str(y_4) + '" '
                        text += 'fill="transparent"/>\n'
                        file.write(text)

        # end individual
        file.write('  </g>\n')

    def draw_vg(self, file):
            # overall position
            x = svg_individuals.border_left + svg_individuals.row_w * self.row_id
            y = svg_individuals.border_top + svg_individuals.col_h * self.col_id

            # store to self to make accesable by others
            self.x = x
            self.y = y

            # draw dot at ovrall position
            dot_x = 'cx="' + str(x) + '" '
            dot_y = 'cy="' + str(y) + '" '
            file.write('  <circle ' + dot_x + dot_y + 'r="4" stroke="black" stroke-width="1" fill="transparent" />\n')

            # create color as str
            fitness_weakest = svg_individuals.fitness_weakest
            fitness = self.fitness
            value = int(basics.avoid_div_zero(255, fitness_weakest) * fitness)
            r, g, b = [value, value, 255]
            r, g, b = [str(r), str(g), str(b)]
            c = 'rgb('+r+','+g+','+b+')'

            box_x = str(x - svg_individuals.box_w * 0.5) # centered
            box_y = str(y)

            box_w = str(svg_individuals.box_w)
            box_h = str(svg_individuals.box_h)

            # open individual
            file.write('  <g class="individual">\n')
            file.write('    <rect x="'+box_x+'" y="'+box_y+'" width="'+box_w+'" height="'+box_h+'" fill="'+c+'"/>\n')

            # draw parents or elitism

            if self.origins != None: # to avoid error in first generation
                for origin in self.origins:
                    # get svg_individual from parent
                    for svg_individual in svg_individuals.instances:
                        if svg_individual.name == origin:

                            # start point at parent
                            x_1 = svg_individual.x
                            y_1 = svg_individual.y + svg_individual.box_h

                            # end point
                            x_4 = x
                            y_4 = y

                            # interpolated points
                            x_2 = x_1
                            y_2 = y_1 + svg_individual.box_h

                            x_3 = x_4
                            y_3 = y_4 - svg_individual.box_h

                            text = '<path d="M ' + str(x_1) + ' ' + str(y_1)
                            text += ' C' + str(x_2) + ', ' + str(y_2) + ' '
                            text += str(x_3) + ', ' + str(y_3) + ' '
                            text += str(x_4) + ', ' + str(y_4) + '" '
                            text += 'fill="transparent"/>\n'
                            file.write(text)

            # end individual
            file.write('  </g>\n')

            # write name
            text_x = str(x)
            text_y = str(y + svg_individuals.line_h)

            name = str(self.name).zfill(3)
            text = '<text x="' + text_x +  '" y="' + text_y
            text += '" dominant-baseline="middle" ' + 'text-anchor="middle">'
            text += name + '</text>\n'
            file.write(text)

            # write fitness
            text_x = str(x)
            text_y = str(y + svg_individuals.line_h * 2)

            text = '<text x="' + text_x +  '" y="' + text_y
            text += '" dominant-baseline="middle" ' + 'text-anchor="middle">'
            text += str(round(self.fitness,3)) + '</text>\n'
            file.write(text)

            # write chromosome
            for i, gene in enumerate(self.chromosome):
                text_x = str(x)
                text_y = str(y + svg_individuals.line_h * (4+i))

                gene = round(gene, 2)
                text = '<text x="' + text_x +  '" y="' + text_y
                text += '" dominant-baseline="middle" ' + 'text-anchor="middle">'
                text += str(gene) + '</text>\n'
                file.write(text)

def copy_sorttable(directory):
    script_folder = os.path.dirname(__file__)
    parent_dir = script_folder[:-9]

    source = parent_dir + "sorttable.js"
    destination = directory + "sorttable.js"
    shutil.copyfile(source, destination)

# from Sachin Rastogi:
# https://www.codespeedy.com/convert-rgb-to-hex-color-code-in-python/
def rgb_to_hex(rgb):
    return '%02x%02x%02x' % rgb

# create matrix like:
# [member 0 frame 0, member 0 frame 1, member 0 frame 2, ...],
# [member 1 frame 0, member 1 frame 2, member 1 frame 2, ...],
# [member 2 frame 0, member 2 frame 2, member 2 frame 2, ...],
# [...

def create_matrix(col, row):
    matrix = []
    for i in range(row):
        line = []
        for j in range(col):
            line.append(None)

        matrix.append(line)

    return matrix

def fill_matrix_members(matrix, result_type, frame, max_diff):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]

    highest = 0
    lowest = 0
    for member_id, member in members.items():
        forces = member[result_type][str(frame)]

        # apply every single pos
        if max_diff:
            for pos_id, force in enumerate(forces):
                matrix[int(member_id)][int(pos_id)] = force

                # find highest
                if force > highest:
                    highest = force

                # find highest
                if force < lowest:
                    lowest = force

        # if only one value
        else:
            force = forces
            for pos_id in range(11):
                matrix[int(member_id)][int(pos_id)] = force

                # find highest
                if force > highest:
                    highest = force

                # find highest
                if force < lowest:
                    lowest = force

    return matrix, highest, lowest

def fill_matrix_frames(matrix, result_type, max_diff):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]

    highest = 0
    lowest = 0
    for member_id, member in members.items():
        # get sorted frames
        sorted_frames = basics.sorted_keys(member[result_type])

        # matrix_frame is the index of the matrix
        # the matrix starts with 0
        # the frame_id of the member can start anywhere
        # if the user is changing the start of the animation
        for matrix_frame, frame_id in enumerate(sorted_frames):
            force = member[result_type][str(frame_id)]
            if max_diff:
                list = []
                for force_pos in force:
                    list.append(force_pos)

                force = basics.return_max_diff_to_zero(list)

            matrix[int(member_id)][int(matrix_frame)] = force

            # find highest
            if force > highest:
                highest = force

            # find highest
            if force < lowest:
                lowest = force

    return matrix, highest, lowest

def fill_matrix_chromosomes(matrix, len_chromosome):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]
    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    highest = 0
    lowest = 0

    # append genes (value of shapekey)
    for gene_id in range(len_chromosome):
        for name, individual in individuals.items():
            gene = individual["chromosome"][gene_id]
            matrix[int(name)][int(gene_id)] = gene

            # find highest
            if gene > highest:
                highest = gene

            # find highest
            if gene < lowest:
                lowest = gene

    weakest = 0
    best = 0

    # append fitness
    for name, individual in individuals.items():
        fitness = individual["fitness"]["weighted"]
        matrix[int(name)][int(len_chromosome)] = fitness

        # find highest
        if fitness > weakest:
            weakest = fitness

        # find highest
        if fitness < weakest:
            best = fitness

    return matrix, highest, lowest, weakest, best

def append_head(file, report_type):
    file.write('<html>\n')
    file.write("<head>\n")
    file.write('<title>')
    text = 'Phaenotyp | report ' + str(report_type)
    file.write(text)
    file.write('</title>\n')

    file.write("Phaenotyp | Report <br>\n")
    file.write("<br>\n")

    if report_type in ["frames", "members"]:
        file.write("<a href='axial.html'>axial</a> |\n")
        file.write("<a href='moment_y.html'>moment_y</a> |\n")
        file.write("<a href='moment_z.html'>moment_z</a> |\n")
        file.write("<a href='shear_y.html'>shear_y</a> |\n")
        file.write("<a href='shear_z.html'>shear_z</a> |\n")
        file.write("<a href='torque.html'>torque</a> |\n")
        file.write("<a href='sigma.html'>sigma</a>\n")
        file.write("<br>\n")

        file.write("<a href='max_long_stress.html'>max_long_stress</a> |\n")
        file.write("<a href='max_tau_shear.html'>max_tau_shear</a> |\n")
        file.write("<a href='max_tau_torsion.html'>max_tau_torsion</a> |\n")
        file.write("<a href='max_sum_tau.html'>max_sum_tau</a> |\n")
        file.write("<a href='max_sigmav.html'>max_sigmav</a> |\n")
        file.write("<a href='max_sigma.html'>max_sigma</a>|\n")
        file.write("<a href='utilization.html'>utilization</a>\n")

        file.write("<br>\n")
        file.write("<br>\n")
        file.write("<br>\n")
        file.write("</head>\n")

        file.write("\n")
        file.write("<style>\n")
        file.write("* {font-family: sans-serif;}\n")
        file.write("a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: none;}\n")
        file.write("a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: none;}\n")
        file.write("a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
        file.write("a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
        file.write("</style>\n")

        # from https://www.kryogenix.org/
        # as suggested by smilyface
        # https://stackoverflow.com/questions/10683712/html-table-sort
        file.write('<script src="sorttable.js"></script>')

        file.write('<table class="sortable">')
        file.write('<tr class="item">')

        # empty part in the top-left
        text = '<td height="20" width="20" bgcolor="FFFFFF">Member</td>'
        file.write(text)

    elif report_type == "chromosomes":
        file.write("\n")
        file.write("<style>\n")
        file.write("* {font-family: sans-serif;}\n")
        file.write("a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: none;}\n")
        file.write("a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: none;}\n")
        file.write("a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
        file.write("a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
        file.write("</style>\n")

        # from https://www.kryogenix.org/
        # as suggested by smilyface
        # https://stackoverflow.com/questions/10683712/html-table-sort
        file.write('<script src="sorttable.js"></script>\n')

        file.write('<table class="sortable">\n')
        file.write('<tr class="item">\n')

        # empty part in the top-left
        text = '<td height="20" width="20" bgcolor="FFFFFF">Individual</td>\n'
        file.write(text)

    elif report_type == "tree":
        file.write("<br>\n")

        file.write("<br>\n")
        file.write("<br>\n")
        file.write("<br>\n")
        file.write("</head>\n")
    else:
        pass

def append_headlines(file, names, fill):
    for name in names:
        if fill:
            if type(name) != str:
                name = str(name).zfill(fill)

        text = '<td height="20" width="20" align="right">' + str(name) + '</td>\n'
        file.write(text)

    file.write('</tr>')

def append_matrix_members(file, matrix, frame, highest, lowest, max_diff):
    for member_id, member_entry in enumerate(matrix):
        # start row
        file.write('<tr class="item">')

        # print member name
        text = '<td height="20" width="20" align="left">' + str(member_id).zfill(3) + '</td>\n'
        file.write(text)

        if max_diff:
            # at all positions of member
            for force in member_entry:
                if force > 0:
                    value = int(basics.avoid_div_zero(255, highest) * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                elif force == 0:
                    value = int(basics.avoid_div_zero(255, highest) * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                else:
                    value = int(basics.avoid_div_zero(255, lowest) * force)
                    color = rgb_to_hex((255-value, 255-value, 255))

                text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(force,3)) + '</td>\n'
                file.write(text)

        # otherwiese take first pos only
        else:
            force = member_entry[0] # all entries are the same
            for i in range(11):
                if force > 0:
                    value = int(basics.avoid_div_zero(255, highest) * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                elif force == 0:
                    value = int(basics.avoid_div_zero(255, highest) * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                else:
                    value = int(basics.avoid_div_zero(255, lowest) * force)
                    color = rgb_to_hex((255-value, 255-value, 255))

                text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(force,3)) + '</td>\n'
                file.write(text)

        # end row
        file.write("</tr>\n")

def append_matrix_frames(file, matrix, highest, lowest, max_diff):
    for member_id, member_entry in enumerate(matrix):
        # start row
        file.write('<tr class="item">')

        # print member name
        text = '<td height="20" width="20" align="left">' + str(member_id).zfill(3) + '</td>\n'
        file.write(text)

        for force in member_entry:
            if max_diff:
                value = abs(int(basics.avoid_div_zero(255, highest) * force))

            if force > 0:
                value = int(basics.avoid_div_zero(255, highest) * force)
                color = rgb_to_hex((255, 255-value, 255-value))

            elif force == 0:
                value = int(basics.avoid_div_zero(255, highest) * force)
                color = rgb_to_hex((255, 255-value, 255-value))

            else:
                value = int(basics.avoid_div_zero(255, lowest) * force)
                color = rgb_to_hex((255-value, 255-value, 255))

            text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(force,3)) + '</td>\n'
            file.write(text)

        # end row
        file.write("</tr>\n")

def append_matrix_chromosomes(file, matrix, highest, lowest, weakest, best):
    for name, individual_entry in enumerate(matrix):
        # start row
        file.write('<tr class="item">')

        # print member name
        text = '<td height="20" width="20" align="left">' + str(name).zfill(3) + '</td>\n'
        file.write(text)

        len_entries = len(individual_entry) # to check if gene
        for id, entry in enumerate(individual_entry):
            # if gene
            if id < len_entries-1:
                value = int(basics.avoid_div_zero(255, highest) * entry)
                color = rgb_to_hex((255, 255-value, 255-value))

                text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(entry,3)) + '</td>\n'
                file.write(text)

            # if fitness
            else:
                value = int(basics.avoid_div_zero(255, weakest) * entry)
                color = rgb_to_hex((value, value, 255))

                text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(entry,3)) + '</td>\n'
                file.write(text)

        # end row
        file.write("</tr>\n")

def append_end(file):
    file.write("</table>\n")
    file.write('</html>')
    file.close()

def report_members(directory, frame):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]

    force_types = {}

    # force type with setting max_diff
    force_types["axial"] = True
    force_types["moment_y"] = True
    force_types["moment_z"] = True
    force_types["shear_y"] = True
    force_types["shear_z"] = True
    force_types["torque"] = True
    force_types["sigma"] = True

    force_types["max_long_stress"] = False
    force_types["max_tau_shear"] = False
    force_types["max_tau_torsion"] = False
    force_types["max_sum_tau"] = False
    force_types["max_sigmav"] = False
    force_types["max_sigma"] = False
    force_types["utilization"] = False

    for force_type, max_diff in force_types.items():

        # create file
        filename = directory + str(force_type) + ".html"
        file = open(filename, 'w')
        len_members = (len(members))
        frames_len = len(members["0"][force_type]) # Was wenn start wo anders?

        # create matrix with length of col and row
        result_matrix = create_matrix(11, len_members)

        # fill matrix with, result_matrix, forcetype, max_diff and absolute
        result_matrix, highest, lowest = fill_matrix_members(result_matrix, force_type, frame, max_diff)

        # append start
        append_head(file, "members")

        names = list(range(0,11)) # positions
        append_headlines(file, names, 3)

        # append matrix with or without max_diff
        append_matrix_members(file, result_matrix, frame, highest, lowest, max_diff)

        append_end(file)

def report_frames(directory, start, end):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]

    force_types = {}

    # force type with setting max_diff
    force_types["axial"] = True
    force_types["moment_y"] = True
    force_types["moment_z"] = True
    force_types["shear_y"] = True
    force_types["shear_z"] = True
    force_types["torque"] = True
    force_types["sigma"] = True

    force_types["max_long_stress"] = False
    force_types["max_tau_shear"] = False
    force_types["max_tau_torsion"] = False
    force_types["max_sum_tau"] = False
    force_types["max_sigmav"] = False
    force_types["max_sigma"] = False
    force_types["utilization"] = False

    for force_type, max_diff in force_types.items():
        # create file
        filename = directory + str(force_type) + ".html"
        file = open(filename, 'w')
        len_members = (len(members))
        frames_len = len(members["0"][force_type]) # Was wenn start wo anders?

        # create matrix with length of col and row
        result_matrix = create_matrix(frames_len, len_members)

        # fill matrix with, result_matrix, forcetype, max_diff and absolute
        result_matrix, highest, lowest = fill_matrix_frames(result_matrix, force_type, max_diff)

        # append start
        append_head(file, "frames")

        names = list(range(start, end+1))
        append_headlines(file, names, 3)

        # append matrix with or without max_diff
        append_matrix_frames(file, result_matrix, highest, lowest, max_diff)

        append_end(file)

def report_chromosomes(directory):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]
    individuals = data["ga_individuals"]

    # create file
    filename = directory + "index.html"
    file = open(filename, 'w')
    len_chromosome = len(shape_keys)-1 # without basic
    len_individuals = len(individuals)

    # create matrix with length of col and row
    result_matrix = create_matrix(len_chromosome+1, len_individuals)

    # fill matrix with, result_matrix, forcetype, max_diff and absolute
    result_matrix, highest, lowest, weakest, best = fill_matrix_chromosomes(result_matrix, len_chromosome)

    # append start
    append_head(file, "chromosomes")

    names = list(range(len_chromosome)) # genes
    names.append("fitness") # plus fitness
    append_headlines(file, names, 3)

    # append matrix
    append_matrix_chromosomes(file, result_matrix, highest, lowest, weakest, best)

    append_end(file)

def report_tree(directory):
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    shape_keys = obj.data.shape_keys.key_blocks
    members = data["members"]

    environment = data["ga_environment"]
    individuals = data["ga_individuals"]

    filename = directory + "index.html"
    file = open(filename, 'w')

    # pass
    svg_individuals.len_keys = len(shape_keys)
    svg_individuals.generation_size = environment["generation_size"]
    svg_individuals.generation_amount = environment["generation_amount"]

    # sort by fitness
    list_result = []
    for name, individual in individuals.items():
        list_result.append([name, individual["chromosome"], individual["fitness"]["weighted"]])

    sorted_list = sorted(list_result, key = lambda x: x[2])
    svg_individuals.fitness_best = sorted_list[0][2]
    svg_individuals.fitness_weakest = sorted_list[len(sorted_list)-1][2]

    append_head(file, "tree")
    svg_individuals.setup()
    svg_individuals.start(file)
    svg_individuals.initial_generation(file)
    svg_individuals.other_generations(file)
    svg_individuals.loop_bgs(file)
    svg_individuals.loop_vgs(file)
    svg_individuals.end(file)
