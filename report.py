import bpy
from phaenotyp import basics
import shutil
import os.path
from mathutils import Color, Vector
c = Color()

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

		environment = data["environment"]
		individuals = data["individuals"]

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

		environment = data["environment"]
		individuals = data["individuals"]

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
	path_addons = os.path.dirname(__file__) # path to the folder of addons
	source = path_addons + "/sorttable/sorttable.js"
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

def fill_matrix_members(matrix, result_type, frame, length):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]

	highest = 0
	lowest = 0
	for member_id, member in members.items():
		forces = member[result_type][str(frame)]

		if length > 1:
			for pos_id, force in enumerate(forces):
				# force, overstress and utilization
				overstress = member["overstress"][str(frame)]
				utilization = False # utilization is always one value
				
				index_in_list = list(members).index(member_id)
				matrix[index_in_list][int(pos_id)] = [force, overstress, utilization]

				# find highest
				if force > highest:
					highest = force

				# find highest
				if force < lowest:
					lowest = force

		else:
			force = forces # only one
			# force, overstress and utilization
			overstress = member["overstress"][str(frame)]
			if result_type == "utilization":
				utilization = True
			else:
				utilization = False
			matrix[int(list(members)[member_id])] = [force, overstress, utilization]

			# find highest
			if force > highest:
				highest = force

			# find highest
			if force < lowest:
				lowest = force

	return matrix, highest, lowest

def fill_matrix_frames(matrix, result_type, length):
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
			if length > 1:
				force_list = []
				for force_pos in force:
					force_list.append(force_pos)

				force = basics.return_max_diff_to_zero(force_list)

			# force, overstress and utilization
			overstress = member["overstress"][str(frame_id)]
			if result_type == "utilization":
				utilization = True
			else:
				utilization = False
			
			index_in_list = list(members).index(member_id)
			matrix[index_in_list][int(matrix_frame)] = [force, overstress, utilization]

			# find highest
			if force > highest:
				highest = force

			# find highest
			if force < lowest:
				lowest = force

	return matrix, highest, lowest

def fill_matrix_quads(matrix, result_type, length):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	quads = data["quads"]

	highest = 0
	lowest = 0
	for quad_id, quad in quads.items():
		# get sorted frames
		sorted_frames = basics.sorted_keys(quad[result_type])

		# matrix_frame is the index of the matrix
		# the matrix starts with 0
		# the frame_id of the member can start anywhere
		# if the user is changing the start of the animation
		for matrix_quad, frame_id in enumerate(sorted_frames):
			force = quad[result_type][str(frame_id)]
			if length > 1:
				force_list = []
				for force_pos in force:
					force_list.append(force_pos)

				force = basics.return_max_diff_to_zero(force_list)

			# force, overstress and utilization
			overstress = quad["overstress"][str(frame_id)]
			if result_type == "utilization":
				utilization = True
			else:
				utilization = False
			
			index_in_list = list(quads).index(quad_id)
			matrix[index_in_list][int(matrix_quad)] = [force, overstress, utilization]

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
	environment = data["environment"]
	individuals = data["individuals"]

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
	fitness_types = ["volume", "area", "weight", "rise", "span", "cantilever"]

	if phaenotyp.calculation_type != "geometrical":
		if phaenotyp.calculation_type == "force_distribution":
			fitness_types.append("average_sigma")
		if phaenotyp.calculation_type != "force_distribution":
			fitness_types.append("deflection_members")
			fitness_types.append("deflection_quads")
			fitness_types.append("average_sigma_members")
			fitness_types.append("average_sigmav_quads")
			fitness_types.append("average_strain_energy")

	fitness_types.append("weighted")

	for fitness_id, fitness_type in enumerate(fitness_types):
		for name, individual in individuals.items():
			fitness = individual["fitness"][fitness_type]
			matrix[int(name)][int(len_chromosome)+fitness_id] = fitness

			# find highest
			if fitness > weakest:
				weakest = fitness

			# find highest
			if fitness < weakest:
				best = fitness

	return matrix, highest, lowest, weakest, best

def append_head(file, report_type, name, unit):
	file.write('<html>\n')
	file.write("<head>\n")
	file.write('<title>')
	text = 'Phaenotyp | report ' + str(report_type) + " | " + name
	
	file.write(text)
	file.write('</title>\n')
	
	file.write('<font size="+2">' + text + '</font>')
	file.write("<br>\n")
	file.write("<br>\n")

	if report_type == "members":
		file.write("<a href='axial.html'>axial</a> |\n")
		file.write("<a href='moment_y.html'>moment_y</a> |\n")
		file.write("<a href='moment_z.html'>moment_z</a> |\n")
		file.write("<a href='moment_h.html'>moment_h</a> |\n")
		file.write("<a href='shear_y.html'>shear_y</a> |\n")
		file.write("<a href='shear_z.html'>shear_z</a> |\n")
		file.write("<a href='shear_h.html'>shear_h</a> |\n")
		file.write("<a href='torque.html'>torque</a> |\n")
		file.write("<a href='sigma.html'>sigma</a>\n")
		file.write("<br>\n")

		file.write("<a href='normal_energy.html'>normal_energy</a>|\n")
		file.write("<a href='moment_energy.html'>moment_energy</a>|\n")
		file.write("<a href='strain_energy.html'>strain_energy</a>\n")

		file.write("<br>\n")
		file.write("<br>\n")
		file.write("</head>\n")

		file.write("\n")
		file.write("<style>\n")
		file.write("* {font-family: sans-serif;}\n")
		file.write("a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("</style>\n")
		file.write("\n")
		
		if unit:
			file.write("\n")
			file.write("all values in unit: " + unit)
			file.write("<br>\n")
			file.write("<br>\n")
			file.write("\n")
		
		# from https://www.kryogenix.org/
		# as suggested by smilyface
		# https://stackoverflow.com/questions/10683712/html-table-sort
		file.write('<script src="sorttable.js"></script>\n')
		file.write("\n")
		
		# based on the answer of Niente0
		# https://stackoverflow.com/questions/26053004/copy-whole-html-table-to-clipboard-javascript
		file.write('<script type="text/javascript">\n')
		file.write('function copytable(el) {\n')
		file.write('var urlField = document.getElementById(el)\n')
		file.write('var range = document.createRange()\n')
		file.write('range.selectNode(urlField)\n')
		file.write('window.getSelection().addRange(range)\n')
		file.write('document.execCommand("copy")\n')
		file.write('}\n')
		file.write('</script>\n')
		file.write("\n")
		
		file.write('<a onClick="copytable(')
		file.write("'stats')")
		file.write('">copy to clipboard</a>\n')
		file.write('<br>\n')
		file.write('<br>\n')
		
		file.write('<table class="sortable" id=stats>\n')
		file.write('<tr class="item">')

		# empty part in the top-left
		text = '<td height="20" width="20" bgcolor="FFFFFF">Member</td>'
		file.write(text)

	elif report_type == "frames":
		file.write("<a href='max_sigma.html'>max_sigma</a> |\n")
		file.write("<a href='max_tau_shear.html'>max_tau_shear</a> |\n")
		file.write("<a href='max_tau_torsion.html'>max_tau_torsion</a> |\n")
		file.write("<a href='max_sum_tau.html'>max_sum_tau</a> |\n")
		file.write("<a href='max_sigmav.html'>max_sigmav</a>\n")
		file.write("<br>\n")

		file.write("<a href='utilization.html'>utilization</a> |\n")
		file.write("<a href='acceptable_sigma_buckling.html'>acceptable_sigma_buckling</a>\n")
		file.write("<br>\n")
		
		file.write("<a href='Do.html'>Do</a> |\n")
		file.write("<a href='Di.html'>Di</a> |\n")		
		file.write("<a href='weight.html'>weight</a> |\n")
		file.write("<a href='length.html'>length</a>\n")

		file.write("<br>\n")
		file.write("<br>\n")
		file.write("</head>\n")

		file.write("\n")
		file.write("<style>\n")
		file.write("* {font-family: sans-serif;}\n")
		file.write("a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("</style>\n")
		file.write("\n")

		if unit:
			file.write("\n")
			file.write("all values in unit: " + unit)
			file.write("<br>\n")
			file.write("<br>\n")
			file.write("\n")
		
		# from https://www.kryogenix.org/
		# as suggested by smilyface
		# https://stackoverflow.com/questions/10683712/html-table-sort
		file.write('<script src="sorttable.js"></script>\n')
		file.write("\n")
		
		# based on the answer of Niente0
		# https://stackoverflow.com/questions/26053004/copy-whole-html-table-to-clipboard-javascript
		file.write('<script type="text/javascript">\n')
		file.write('function copytable(el) {\n')
		file.write('var urlField = document.getElementById(el)\n')
		file.write('var range = document.createRange()\n')
		file.write('range.selectNode(urlField)\n')
		file.write('window.getSelection().addRange(range)\n')
		file.write('document.execCommand("copy")\n')
		file.write('}\n')
		file.write('</script>\n')
		file.write("\n")
		
		file.write('<a onClick="copytable(')
		file.write("'stats')")
		file.write('">copy to clipboard</a>\n')
		file.write('<br>\n')
		file.write('<br>\n')
		
		file.write('<table class="sortable" id=stats>\n')
		file.write('<tr class="item">')

		# empty part in the top-left
		text = '<td height="20" width="20" bgcolor="FFFFFF">Member</td>'
		file.write(text)

	elif report_type == "quads":
		file.write("<a href='membrane_xy.html'>membrane_xy</a> |\n")
		file.write("<a href='membrane_x.html'>membrane_x</a> |\n")
		file.write("<a href='membrane_y.html'>membrane_y</a> |\n")
		
		file.write("<a href='moment_xy.html'>moment_xy</a> |\n")
		file.write("<a href='moment_x.html'>moment_x</a> |\n")
		file.write("<a href='moment_y.html'>moment_y</a> |\n")
		
		file.write("<a href='shear_x.html'>shear_x</a> |\n")
		file.write("<a href='shear_y.html'>shear_y</a>\n")
		file.write("<br>\n")

		file.write("<a href='length_x.html'>length_x</a> |\n")
		file.write("<a href='length_y.html'>length_y</a> |\n")
		file.write("<a href='thickness.html'>thickness</a> |\n")
		file.write("<a href='weight.html'>weight</a> |\n")
		file.write("<a href='area.html'>area</a>\n")
		file.write("<br>\n")

		#file.write("<a href='moment_h.html'>moment_h</a> |\n")
		#file.write("<a href='shear_h.html'>shear_h</a> |\n")
		#file.write("<a href='tau_shear.html'>tau_shear |</a>\n")
		#file.write("<a href='sigmav.html'>sigmav</a> |\n")
		#file.write("<a href='sigma.html'>sigma</a>\n")
		#file.write("<br>\n")
		
		file.write("<a href='s_x_1.html'>s_x_1</a> |\n")
		file.write("<a href='s_x_2.html'>s_x_2</a> |\n")
		file.write("<a href='s_y_1.html'>s_y_1</a> |\n")
		file.write("<a href='s_y_2.html'>s_y_2</a> |\n")
		file.write("<a href='T_xy_1.html'>T_xy_1</a> |\n")
		file.write("<a href='T_xy_2.html'>T_xy_2</a>\n")
		file.write("<br>\n")

		file.write("<a href='s_1_1.html'>s_1_1</a> |\n")
		file.write("<a href='s_1_2.html'>s_1_2</a> |\n")
		file.write("<a href='s_2_1.html'>s_2_1</a> |\n")
		file.write("<a href='s_2_2.html'>s_2_2</a>\n")
		file.write("<br>\n")
		
		file.write("<a href='alpha_1.html'>alpha_1</a> |\n")
		file.write("<a href='alpha_2.html'>alpha_2</a>\n")
		file.write("<br>\n")

		file.write("<a href='utilization.html'>utilization</a>\n")
		file.write("<br>\n")
		
		#file.write("<a href='strain_energy.html'>strain_energy</a> |\n")
		#file.write("<a href='normal_energy.html'>normal_energy</a> |\n")
		#file.write("<a href='moment_energy.html'>moment_energy</a>\n")
		
		file.write("<br>\n")
	
		# utilization?

		file.write("<br>\n")
		file.write("<br>\n")
		file.write("</head>\n")

		file.write("\n")
		file.write("<style>\n")
		file.write("* {font-family: sans-serif;}\n")
		file.write("a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("</style>\n")
		file.write("\n")

		if unit:
			file.write("\n")
			file.write("all values in unit: " + unit)
			file.write("<br>\n")
			file.write("<br>\n")
			file.write("\n")
		
		# from https://www.kryogenix.org/
		# as suggested by smilyface
		# https://stackoverflow.com/questions/10683712/html-table-sort
		file.write('<script src="sorttable.js"></script>\n')
		file.write("\n")
		
		# based on the answer of Niente0
		# https://stackoverflow.com/questions/26053004/copy-whole-html-table-to-clipboard-javascript
		file.write('<script type="text/javascript">\n')
		file.write('function copytable(el) {\n')
		file.write('var urlField = document.getElementById(el)\n')
		file.write('var range = document.createRange()\n')
		file.write('range.selectNode(urlField)\n')
		file.write('window.getSelection().addRange(range)\n')
		file.write('document.execCommand("copy")\n')
		file.write('}\n')
		file.write('</script>\n')
		file.write("\n")
		
		file.write('<a onClick="copytable(')
		file.write("'stats')")
		file.write('">copy to clipboard</a>\n')
		file.write('<br>\n')
		file.write('<br>\n')
		
		file.write('<table class="sortable" id=stats>\n')
		file.write('<tr class="item">')

		# empty part in the top-left
		text = '<td height="20" width="20" bgcolor="FFFFFF">Quad</td>'
		file.write(text)
	
	elif report_type == "combined":
		file.write("<a href='axial.html'>axial</a> |\n")
		file.write("<a href='sigma.html'>sigma</a> |\n")
		file.write("<a href='Do.html'>Do</a> |\n")
		file.write("<a href='Di.html'>Di</a> |\n")
		file.write("<a href='utilization.html'>utilization</a> |\n")
		file.write("<a href='weight.html'>weight</a> |\n")
		file.write("<a href='length.html'>length</a>\n")

		file.write("<br>\n")
		file.write("<br>\n")
		file.write("</head>\n")

		file.write("\n")
		file.write("<style>\n")
		file.write("* {font-family: sans-serif;}\n")
		file.write("a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("</style>\n")
		file.write("\n")

		if unit:
			file.write("\n")
			file.write("all values in unit: " + unit)
			file.write("<br>\n")
			file.write("<br>\n")
			file.write("\n")
		
		# from https://www.kryogenix.org/
		# as suggested by smilyface
		# https://stackoverflow.com/questions/10683712/html-table-sort
		file.write('<script src="sorttable.js"></script>\n')
		file.write("\n")
		
		# based on the answer of Niente0
		# https://stackoverflow.com/questions/26053004/copy-whole-html-table-to-clipboard-javascript
		file.write('<script type="text/javascript">\n')
		file.write('function copytable(el) {\n')
		file.write('var urlField = document.getElementById(el)\n')
		file.write('var range = document.createRange()\n')
		file.write('range.selectNode(urlField)\n')
		file.write('window.getSelection().addRange(range)\n')
		file.write('document.execCommand("copy")\n')
		file.write('}\n')
		file.write('</script>\n')
		file.write("\n")
		
		file.write('<a onClick="copytable(')
		file.write("'stats')")
		file.write('">copy to clipboard</a>\n')
		file.write('<br>\n')
		file.write('<br>\n')
		
		file.write('<table class="sortable" id=stats>\n')
		file.write('<tr class="item">')

		# empty part in the top-left
		text = '<td height="20" width="20" bgcolor="FFFFFF">Member</td>'
		file.write(text)

	elif report_type == "chromosomes":
		file.write("\n")
		file.write("<style>\n")
		file.write("* {font-family: sans-serif;}\n")
		file.write("a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: None;}\n")
		file.write("a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}\n")
		file.write("</style>\n")
		file.write("\n")

		# from https://www.kryogenix.org/
		# as suggested by smilyface
		# https://stackoverflow.com/questions/10683712/html-table-sort
		file.write('<script src="sorttable.js"></script>\n')
		file.write("\n")
		
		# based on the answer of Niente0
		# https://stackoverflow.com/questions/26053004/copy-whole-html-table-to-clipboard-javascript
		file.write('<script type="text/javascript">\n')
		file.write('function copytable(el) {\n')
		file.write('var urlField = document.getElementById(el)\n')
		file.write('var range = document.createRange()\n')
		file.write('range.selectNode(urlField)\n')
		file.write('window.getSelection().addRange(range)\n')
		file.write('document.execCommand("copy")\n')
		file.write('}\n')
		file.write('</script>\n')
		file.write("\n")
		
		file.write('<a onClick="copytable(')
		file.write("'stats')")
		file.write('">copy to clipboard</a>\n')
		file.write('<br>\n')
		file.write('<br>\n')
		
		file.write('<table class="sortable" id=stats>\n')
		file.write('<tr class="item">')

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

def append_matrix_members(file, matrix, frame, highest, lowest, length):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	members = data["members"]
	
	for id_in_list, member_entry in enumerate(matrix):
		# start row
		file.write('<tr class="item">')

		# print member name
		member_id = list(members)[id_in_list]
		text = '<td height="20" width="20" align="left">' + str(member_id).zfill(3) + '</td>\n'
		file.write(text)

		# at all positions of member
		if length > 1:
			for entry in member_entry:
				force, overstress, utilization = entry
				value = force
				"""
				# red or blue?
				if value > 0:
					h = 0
				else:
					h = 0.666

				# saturation
				max_diff = basics.return_max_diff_to_zero([lowest, highest])
				s = abs(basics.avoid_div_zero(1, max_diff) * value)

				# define v
				if overstress:
					# like in update_post put not so strong
					# to make it readable in html
					v = 0.75
				else:
					v = 1.0
				"""
				max_diff = basics.return_max_diff_to_zero([lowest, highest])
				if max_diff != 0:
					h = 0.333/max_diff*force + 0.333
				else:
					h = 0 # white
				
				s = 1

				if overstress == True:
					v = 0.75
				else:
					v = 1.0

				c.hsv = h,s,v
				r = int(c.r*255)
				g = int(c.g*255)
				b = int(c.b*255)
				color = rgb_to_hex((r,g,b))

				text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' + "{:10.3f}".format(force) + '</td>\n'
				file.write(text)

		else:
			force, overstress, utilization = member_entry
			# -1 to show utilization in blue and red
			# utilization is always one
			if utilization:
				value = force -1
			else:
				value = force
			"""
			# red or blue?
			if value > 0:
				h = 0
			else:
				h = 0.666

			# saturation
			max_diff = basics.return_max_diff_to_zero([lowest, highest])
			s = abs(basics.avoid_div_zero(1, max_diff) * value)

			# define v
			if overstress:
				# like in update_post put not so strong
				# to make it readable in html
				v = 0.75
			else:
				v = 1.0
			"""
			
			max_diff = basics.return_max_diff_to_zero([lowest, highest])
			if max_diff != 0:
				h = 0.333/max_diff*force + 0.333
			else:
				h = 0 # white
			
			s = 1

			if overstress == True:
				v = 0.25
			else:
				v = 1.0
			
			c.hsv = h,s,v
			r = int(c.r*255)
			g = int(c.g*255)
			b = int(c.b*255)
			color = rgb_to_hex((r,g,b))
			text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' + "{:10.3f}".format(force) + '</td>\n'
			file.write(text)

		# end row
		file.write("</tr>\n")

def append_matrix_frames(file, matrix, highest, lowest, length):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	members = data["members"]
	
	for id_in_list, member_entry in enumerate(matrix):
		# start row
		file.write('<tr class="item">')

		# print member name
		member_id = list(members)[id_in_list]
		text = '<td height="20" width="20" align="left">' + str(member_id).zfill(3) + '</td>\n'
		file.write(text)

		for entry in member_entry:
			force, overstress, utilization = entry

			if utilization:
				value = force-1

			else:
				value = force
			
			max_diff = basics.return_max_diff_to_zero([lowest, highest])
			if max_diff != 0:
				h = 0.333/max_diff*force + 0.333
			else:
				h = 0 # white

			s = 1
			if overstress == True:
				v = 0.75
			else:
				v = 1.0

			c.hsv = h,s,v
			r = int(c.r*255)
			g = int(c.g*255)
			b = int(c.b*255)
			color = rgb_to_hex((r,g,b))

			c.hsv = h,s,v
			r = int(c.r*255)
			g = int(c.g*255)
			b = int(c.b*255)
			color = rgb_to_hex((r,g,b))
			text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' + "{:10.3f}".format(force) + '</td>\n'
			file.write(text)

		# end row
		file.write("</tr>\n")

def append_matrix_quads(file, matrix, highest, lowest, length):
	scene = bpy.context.scene
	data = scene["<Phaenotyp>"]
	quads = data["quads"]
	
	for id_in_list, quad_entry in enumerate(matrix):
		# start row
		file.write('<tr class="item">')

		# print member name
		quad_id = list(quads)[id_in_list]
		text = '<td height="20" width="20" align="left">' + str(quad_id).zfill(3) + '</td>\n'
		file.write(text)

		for entry in quad_entry:
			force, overstress, utilization = entry

			if utilization:
				value = force-1

			else:
				value = force
			
			max_diff = basics.return_max_diff_to_zero([lowest, highest])
			if max_diff != 0:
				h = 0.333/max_diff*force + 0.333
			else:
				h = 0 # white

			s = 1
			if overstress == True:
				v = 0.75
			else:
				v = 1.0

			c.hsv = h,s,v
			r = int(c.r*255)
			g = int(c.g*255)
			b = int(c.b*255)
			color = rgb_to_hex((r,g,b))

			c.hsv = h,s,v
			r = int(c.r*255)
			g = int(c.g*255)
			b = int(c.b*255)
			color = rgb_to_hex((r,g,b))
			text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' + "{:10.3f}".format(force) + '</td>\n'
			file.write(text)

		# end row
		file.write("</tr>\n")

def append_matrix_chromosomes(file, matrix, highest, lowest, weakest, best, len_fitness_functions):
	for name, individual_entry in enumerate(matrix):
		# start row
		file.write('<tr class="item">')

		# print member name
		text = '<td height="20" width="20" align="left">' + str(name).zfill(3) + '</td>\n'
		file.write(text)

		len_entries = len(individual_entry) # to check if gene
		for id, entry in enumerate(individual_entry):
			# if gene - amount of fitness_functions
			if id < len_entries - len_fitness_functions:
				value = int(basics.avoid_div_zero(255, highest) * entry)
				color = rgb_to_hex((255, 255-value, 255-value))

				text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' + "{:10.3f}".format(entry) + '</td>\n'
				file.write(text)

			# if fitness
			else:
				#value = int(basics.avoid_div_zero(255, weakest) * entry)
				#color = rgb_to_hex((value, value, 255))
				color = rgb_to_hex((255, 255, 255)) # always white?

				text = '<td height="20" width="20" align="right" bgcolor=' + color + '>' + "{:10.3f}".format(entry)  + '</td>\n'
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

	# force type with length of entry
	force_types["axial"] = [11, "kN"]
	force_types["moment_y"] = [11, "kNcm"]
	force_types["moment_z"] = [11, "kNcm"]
	force_types["moment_h"] = [11, "kNcm"]
	force_types["shear_y"] = [11, "kN"]
	force_types["shear_z"] = [11, "kN"]
	force_types["shear_h"] = [11, "kN"]
	force_types["torque"] = [11, "kNcm"]
	force_types["sigma"] = [11, "kN/cm²"]

	force_types["normal_energy"] = [10, "kNcm"]
	force_types["moment_energy"] = [10, "kNcm"]
	force_types["strain_energy"] = [10, "kNcm"]

	for force_type, entries in force_types.items():
		length = entries[0]
		unit = entries[1]
		
		# create file
		filename = directory + str(force_type) + ".html"
		file = open(filename, 'w')
		len_members = (len(members))
		frames_len = len(members[list(members)[0]][force_type]) # len of entries from first existing member

		# create matrix with length of col and row
		result_matrix = create_matrix(length, len_members)

		# fill matrix with, result_matrix, forcetype, length and absolute
		result_matrix, highest, lowest = fill_matrix_members(result_matrix, force_type, frame, length)

		# append start
		append_head(file, "members", force_type, unit)

		# create headlines
		if length > 1:
			names = list(range(0,length)) # positions
			append_headlines(file, names, 3)

		else:
			append_headlines(file, ["max"], False)

		# append matrix with or without length
		append_matrix_members(file, result_matrix, frame, highest, lowest, length)

		append_end(file)

def report_frames(directory, start, end):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]

	force_types = {}

	force_types["max_sigma"] = [1, "kN/cm²"]
	force_types["max_tau_shear"] = [1, "kN/cm²"]
	force_types["max_tau_torsion"] = [1, "kN/cm²"]
	force_types["max_sum_tau"] = [1, "kN/cm²"]
	force_types["max_sigmav"] = [1, "kN/cm²"]

	force_types["Do"] = [1, "cm"]
	force_types["Di"] = [1, "cm"]
	force_types["utilization"] = [1, ""]
	force_types["acceptable_sigma_buckling"] = [1, "kN/cm²"]

	force_types["weight"] = [1, "kg"]
	force_types["length"] = [1, "cm"]

	for force_type, entries in force_types.items():
		length = entries[0]
		unit = entries[1]
		
		# create file
		filename = directory + str(force_type) + ".html"
		file = open(filename, 'w')
		len_members = (len(members))
		frames_len = len(members[list(members)[0]][force_type]) # Was wenn start wo anders?

		# create matrix with length of col and row
		result_matrix = create_matrix(frames_len, len_members)

		# fill matrix with, result_matrix, forcetype, length and absolute
		result_matrix, highest, lowest = fill_matrix_frames(result_matrix, force_type, length)

		# append start
		append_head(file, "frames", force_type, unit)

		names = list(range(start, end+1))
		append_headlines(file, names, 3)

		# append matrix with or without
		append_matrix_frames(file, result_matrix, highest, lowest, length)

		append_end(file)

def report_quads(directory, start, end):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	quads = data["quads"]

	force_types = {}

	force_types["membrane_xy"] = [1, None]
	force_types["membrane_x"] = [1, None]
	force_types["membrane_y"] = [1, None]
	
	force_types["moment_xy"] = [1, None]
	force_types["moment_x"] = [1, None]
	force_types["moment_y"] = [1, None]

	force_types["shear_x"] = [1, None]
	force_types["shear_y"] = [1, None]

	force_types["length_x"] = [1, "cm"]
	force_types["length_y"] = [1, "cm"]
	force_types["thickness"] = [1, "cm"]
	force_types["weight"] = [1, "kg"]
	force_types["area"] = [1, "m²"]
	
	#force_types["moment_h"] = [1, "kNcm"]
	#force_types["shear_h"] = [1, "kNcm"]
	#force_types["tau_shear"] = [1, "kNcm"]
	#force_types["sigmav"] = [1, "kNcm"]
	#force_types["sigma"] = [1, "kNcm"]
	
	force_types["s_x_1"] = [1, None]
	force_types["s_x_2"] = [1, None]
	force_types["s_y_1"] = [1, None]
	force_types["s_y_2"] = [1, None]
	force_types["T_xy_1"] = [1, None]
	force_types["T_xy_2"] = [1, None]

	force_types["s_1_1"] = [1, None]
	force_types["s_1_2"] = [1, None]
	force_types["s_2_1"] = [1, None]
	force_types["s_2_2"] = [1, None]
	
	force_types["alpha_1"] = [1, None]
	force_types["alpha_2"] = [1, None]
	
	force_types["utilization"] = [1, None]
	
	#force_types["strain_energy"] = [1, "kNcm"]
	#force_types["normal_energy"] = [1, "kNcm"]
	#force_types["moment_energy"] = [1, "kNcm"]

	for force_type, entries in force_types.items():
		length = entries[0]
		unit = entries[1]
		
		# create file
		filename = directory + str(force_type) + ".html"
		file = open(filename, 'w')
		len_quads = (len(quads))
		frames_len = len(quads[list(quads)[0]][force_type]) # Was wenn start wo anders?

		# create matrix with length of col and row
		result_matrix = create_matrix(frames_len, len_quads)

		# fill matrix with, result_matrix, forcetype, length and absolute
		result_matrix, highest, lowest = fill_matrix_quads(result_matrix, force_type, length)

		# append start
		append_head(file, "quads", force_type, unit)

		names = list(range(start, end+1))
		append_headlines(file, names, 3)

		# append matrix with or without
		append_matrix_quads(file, result_matrix, highest, lowest, length)

		append_end(file)

# is working like report_frames but for force distribution
def report_combined(directory, start, end):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	members = data["members"]

	force_types = {}

	force_types["axial"] = 1 # kN
	force_types["sigma"] = 1 # kN/cm²

	force_types["Do"] = 1 # cm
	force_types["Di"] = 1 # cm
	force_types["utilization"] = 1

	force_types["weight"] = 1 # kg
	force_types["length"] = 1 # cm

	for force_type, entries in force_types.items():
		length = entries[0]
		unit = entries[1]
		
		# create file
		filename = directory + str(force_type) + ".html"
		file = open(filename, 'w')
		len_members = (len(members))
		frames_len = len(members[list(members)[0]][force_type]) # Was wenn start wo anders?

		# create matrix with length of col and row
		result_matrix = create_matrix(frames_len, len_members)

		# fill matrix with, result_matrix, forcetype, length and absolute
		result_matrix, highest, lowest = fill_matrix_frames(result_matrix, force_type, length)

		# append start
		append_head(file, "combined", force_type)

		names = list(range(start, end+1))
		append_headlines(file, names, 3)

		# append matrix with or without
		append_matrix_frames(file, result_matrix, highest, lowest, length)

		append_end(file)

def report_chromosomes(directory):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]
	individuals = data["individuals"]

	# create file
	filename = directory + "index.html"
	file = open(filename, 'w')
	len_chromosome = len(shape_keys)-1 # without basic
	len_individuals = len(individuals)

	# len_fitness_functions
	if phaenotyp.calculation_type != "geometrical":
		if phaenotyp.calculation_type == "force_distribution":
			len_fitness_functions = 9
		else:
			len_fitness_functions = 12
	else:
		len_fitness_functions = 8

	# create matrix with length of col and row
	# len = genes + amount of fitness
	result_matrix = create_matrix(len_chromosome+len_fitness_functions, len_individuals)

	# fill matrix with, result_matrix, forcetype, length and absolute
	result_matrix, highest, lowest, weakest, best = fill_matrix_chromosomes(result_matrix, len_chromosome)

	# append start
	append_head(file, "chromosomes", "", False)

	# genes
	names = list(range(len_chromosome))

	# plus fitness
	names.append("volume") # m³
	names.append("area") # m²
	names.append("weight") # kg
	names.append("rise") # m
	names.append("span") # m
	names.append("cantilever") # m

	if phaenotyp.calculation_type != "geometrical":
		names.append("deflection_members")
		names.append("deflection_quads")
		names.append("average_sigma_members")
		names.append("average_sigmav_quads")
		if phaenotyp.calculation_type != "force_distribution":
			names.append("average_strain_energy")
	names.append("weighted")

	append_headlines(file, names, 3)

	# append matrix
	append_matrix_chromosomes(file, result_matrix, highest, lowest, weakest, best, len_fitness_functions)

	append_end(file)

def report_tree(directory):
	scene = bpy.context.scene
	phaenotyp = scene.phaenotyp
	data = scene["<Phaenotyp>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	members = data["members"]

	environment = data["environment"]
	individuals = data["individuals"]

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

	append_head(file, "tree", "fitness", False)
	svg_individuals.setup()
	svg_individuals.start(file)
	svg_individuals.initial_generation(file)
	svg_individuals.other_generations(file)
	svg_individuals.loop_bgs(file)
	svg_individuals.loop_vgs(file)
	svg_individuals.end(file)
