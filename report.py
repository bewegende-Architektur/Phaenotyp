import bpy
from phaenotyp import basics
import shutil
import os.path

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

def fill_matrix_frame(matrix, result_type, max_diff):
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

def fill_matrix_pos(matrix, result_type, frame, max_diff):
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
                matrix[int(member_id)][int(pos_id)-1] = force

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
                matrix[int(member_id)][int(pos_id)-1] = force

                # find highest
                if force > highest:
                    highest = force

                # find highest
                if force < lowest:
                    lowest = force

    return matrix, highest, lowest

def append_start(file, report_type):
    file.write('<html>\n')
    file.write("<head>\n")
    file.write('<title>')
    file.write(str(report_type))
    file.write('</title>')

    file.write("Phaenotyp | Report <br>\n")
    file.write("<br>\n")

    file.write("<a href='axial.html'>axial</a> |\n")
    file.write("<a href='moment_y.html'>moment_y</a> |\n")
    file.write("<a href='moment_z.html'>moment_z</a> |\n")
    file.write("<a href='shear_y.html'>shear_y</a> |\n")
    file.write("<a href='shear_z.html'>shear_z</a> |\n")
    file.write("<a href='torque.html'>torque</a>\n")
    file.write("<br>\n")

    file.write("<a href='max_long_stress.html'>max_long_stress</a> |\n")
    file.write("<a href='max_tau_shear.html'>max_tau_shear</a> |\n")
    file.write("<a href='max_tau_torsion.html'>max_tau_torsion</a> |\n")
    file.write("<a href='max_sum_tau.html'>max_sum_tau</a> |\n")
    file.write("<a href='max_sigmav.html'>max_sigmav</a> |\n")
    file.write("<a href='max_sigma.html'>max_sigma</a>\n")

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

def append_headlines(file, names, fill):
    for name in names:
        if fill:
            name = str(name).zfill(fill)

        text = '<td height="20" width="20" align="right">' + str(name) + '</td>'
        file.write(text)

    file.write('</tr>')

def append_matrix_frame(file, matrix, highest, lowest, max_diff):
    for member_id, member_entry in enumerate(matrix):
        # start row
        file.write('<tr class="item">')

        # print member name
        text = '<td height="20" width="20" align="left">' + str(member_id).zfill(3) + '</td>'
        file.write(text)

        for force in member_entry:
            if max_diff:
                value = abs(int(255 / highest * force))

            if force > 0:
                value = int(255 / highest * force)
                color = rgb_to_hex((255, 255-value, 255-value))

            elif force == 0:
                value = int(255 / highest * force)
                color = rgb_to_hex((255, 255-value, 255-value))

            else:
                value = int(255 / lowest * force)
                color = rgb_to_hex((255-value, 255-value, 255))

            text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(force,3)) + '</td>'
            file.write(text)

        # end row
        file.write("</tr>\n")

def append_matrix_pos(file, matrix, frame, highest, lowest, max_diff):
    for member_id, member_entry in enumerate(matrix):
        # start row
        file.write('<tr class="item">')

        # print member name
        text = '<td height="20" width="20" align="left">' + str(member_id).zfill(3) + '</td>'
        file.write(text)

        if max_diff:
            # at all positions of member
            for force in member_entry:
                if force > 0:
                    value = int(255 / highest * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                elif force == 0:
                    value = int(255 / highest * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                else:
                    value = int(255 / lowest * force)
                    color = rgb_to_hex((255-value, 255-value, 255))

                text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(force,3)) + '</td>'
                file.write(text)

        # otherwiese take first pos only
        else:
            force = member_entry[0] # all entries are the same
            for i in range(11):
                if force > 0:
                    value = int(255 / highest * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                elif force == 0:
                    value = int(255 / highest * force)
                    color = rgb_to_hex((255, 255-value, 255-value))

                else:
                    value = int(255 / lowest * force)
                    color = rgb_to_hex((255-value, 255-value, 255))

                text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' +str(round(force,3)) + '</td>'
                file.write(text)

        # end row
        file.write("</tr>\n")

def append_end(file):
    file.write("</table>\n")
    file.write('</html>')
    file.close()

def report_overview(directory, start, end):
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

    force_types["max_long_stress"] = False
    force_types["max_tau_shear"] = False
    force_types["max_tau_torsion"] = False
    force_types["max_sum_tau"] = False
    force_types["max_sigmav"] = False
    force_types["max_sigma"] = False

    for force_type, max_diff in force_types.items():

        # create file
        filename = directory + str(force_type) + ".html"
        file = open(filename, 'w')
        members_len = (len(members))
        frames_len = len(members["0"][force_type]) # Was wenn start wo anders?

        # create matrix with length of col and row
        result_matrix = create_matrix(frames_len, members_len)

        # fill matrix with, result_matrix, forcetype, max_diff and absolute
        result_matrix, highest, lowest = fill_matrix_frame(result_matrix, force_type, max_diff)

        # append start
        append_start(file, "Phaenotyp | report frame")

        names = list(range(start, end+1))
        append_headlines(file, names, 3)

        # append matrix with or without max_diff
        append_matrix_frame(file, result_matrix, highest, lowest, max_diff)

        append_end(file)

def report_frame(directory, frame):
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

    force_types["max_long_stress"] = False
    force_types["max_tau_shear"] = False
    force_types["max_tau_torsion"] = False
    force_types["max_sum_tau"] = False
    force_types["max_sigmav"] = False
    force_types["max_sigma"] = False

    for force_type, max_diff in force_types.items():

        # create file
        filename = directory + str(force_type) + ".html"
        file = open(filename, 'w')
        members_len = (len(members))
        frames_len = len(members["0"][force_type]) # Was wenn start wo anders?

        # create matrix with length of col and row
        result_matrix = create_matrix(11, members_len)

        # fill matrix with, result_matrix, forcetype, max_diff and absolute
        result_matrix, highest, lowest = fill_matrix_pos(result_matrix, force_type, frame, max_diff)

        # append start
        append_start(file, "Phaenotyp | report frame")

        names = list(range(0,11)) # positions
        append_headlines(file, names, 3)

        # append matrix with or without max_diff
        append_matrix_pos(file, result_matrix, frame, highest, lowest, max_diff)

        append_end(file)
