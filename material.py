import warnings # to ignore poly1d or polyfit warnings
warnings.filterwarnings('ignore')

from math import pi, sqrt

# Material properties:
# https://www.johannes-strommer.com/formeln/flaechentraegheitsmoment-widerstandsmoment/
# https://www.maschinenbau-wissen.de/skript3/mechanik/festigkeitslehre/134-knicken-euler

# Knicklinien nach ÖNORM B 4600
kn_lamda = [10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250]

kn235 = [16.5,15.8,15.3,14.8,14.2,13.5,12.7,11.8,10.7,9.5,8.2,6.9,5.9,5.1,4.4,3.9,3.4,3.1,2.7,2.5,2.2,2,1.9,1.7,1.6]
kn275 = [20.5,19.4,18.8,18.0,17.1,16.0,14.8,13.3,11.7,9.9,8.2,6.9,5.9,5.1,4.4,3.9,3.4,3.1,2.7,2.5,2.2,2,1.9,1.7,1.6]
kn355 = [24.5,23.2,22.3,21.2,20.0,18.5,16.7,14.7,12.2,9.9,8.2,6.9,5.9,5.1,4.4,3.9,3.4,3.1,2.7,2.5,2.2,2,1.9,1.7,1.6]
kn460n = [31.7, 30.4, 29.4, 28.4, 27.3, 25.9, 24.4, 22.7, 20.6, 18.3, 15.7, 13.3, 11.3, 9.8, 8.5, 7.5, 6.5, 6, 5.2, 4.8, 4.2, 3.8, 3.7, 3.3, 3.1]
knalu = [10.0,9.6,9.3,9,8.6,8.2,7.7,7.2,6.5,5.8,5.0,4.2,3.6,3.1,2.7,2.4,2.1,1.9,1.6,1.5,1.3,1.2,1.2,1.0,1.0]
knc12_15_rei = [0.80, 0.77, 0.74, 0.72, 0.69, 0.65, 0.62, 0.57, 0.52, 0.46, 0.40, 0.33, 0.29, 0.25, 0.21, 0.19, 0.16, 0.15, 0.13, 0.12, 0.11, 0.10, 0.09, 0.08, 0.08]
knc16_20_rei = [1.07, 1.02, 0.99, 0.96, 0.92, 0.88, 0.82, 0.77, 0.69, 0.62, 0.53, 0.45, 0.38, 0.33, 0.29, 0.25, 0.22, 0.20, 0.18, 0.16, 0.14, 0.13, 0.12, 0.11, 0.10]
knc20_25_rei = [1.33, 1.27, 1.23, 1.19, 1.14, 1.09, 1.02, 0.95, 0.86, 0.77, 0.66, 0.56, 0.48, 0.41, 0.35, 0.31, 0.27, 0.25, 0.22, 0.20, 0.18, 0.16, 0.15, 0.14, 0.13]
knc25_30_rei = [1.67, 1.60, 1.55, 1.50, 1.44, 1.37, 1.29, 1.19, 1.08, 0.96, 0.83, 0.70, 0.60, 0.52, 0.45, 0.39, 0.34, 0.31, 0.27, 0.25, 0.22, 0.20, 0.19, 0.17, 0.16]
knc30_37_rei = [2.00, 1.92, 1.85, 1.79, 1.72, 1.64, 1.54, 1.43, 1.30, 1.15, 0.99, 0.84, 0.72, 0.62, 0.53, 0.47, 0.41, 0.38, 0.33, 0.30, 0.27, 0.24, 0.23, 0.21, 0.19]
knc35_45_rei = [2.33, 2.23, 2.16, 2.09, 2.01, 1.91, 1.79, 1.67, 1.51, 1.34, 1.16, 0.97, 0.83, 0.72, 0.62, 0.55, 0.48, 0.44, 0.38, 0.35, 0.31, 0.28, 0.27, 0.24, 0.23]
knc40_50_rei = [2.67, 2.56, 2.48, 2.39, 2.30, 2.18, 2.06, 1.91, 1.73, 1.54, 1.33, 1.12, 0.95, 0.83, 0.71, 0.63, 0.55, 0.50, 0.44, 0.40, 0.36, 0.32, 0.31, 0.28, 0.26]
knc45_55_rei = [3.00, 2.87, 2.78, 2.69, 2.58, 2.45, 2.31, 2.15, 1.95, 1.73, 1.49, 1.25, 1.07, 0.93, 0.80, 0.71, 0.62, 0.56, 0.49, 0.45, 0.40, 0.36, 0.35, 0.31, 0.29]
knc50_60_rei = [3.33, 3.19, 3.09, 2.99, 2.87, 2.72, 2.56, 2.38, 2.16, 1.92, 1.65, 1.39, 1.19, 1.03, 0.89, 0.79, 0.69, 0.63, 0.54, 0.50, 0.44, 0.40, 0.38, 0.34, 0.32]
knc55_67_rei = [3.67, 3.51, 3.40, 3.29, 3.16, 3.00, 2.82, 2.62, 2.38, 2.11, 1.82, 1.53, 1.31, 1.13, 0.98, 0.87, 0.76, 0.69, 0.60, 0.56, 0.49, 0.44, 0.42, 0.38, 0.36]
knc60_75_rei = [4.00, 3.83, 3.71, 3.59, 3.44, 3.27, 3.08, 2.86, 2.59, 2.30, 1.99, 1.67, 1.43, 1.24, 1.07, 0.95, 0.82, 0.75, 0.65, 0.61, 0.53, 0.48, 0.46, 0.41, 0.39]
knc70_85_rei = [4.67, 4.47, 4.33, 4.19, 4.02, 3.82, 3.59, 3.34, 3.03, 2.69, 2.32, 1.95, 1.67, 1.44, 1.25, 1.10, 0.96, 0.88, 0.76, 0.71, 0.62, 0.57, 0.54, 0.48, 0.45]
knc80_95_rei = [5.33, 5.10, 4.94, 4.78, 4.59, 4.36, 4.10, 3.81, 3.46, 3.07, 2.65, 2.23, 1.91, 1.65, 1.42, 1.26, 1.10, 1.00, 0.87, 0.81, 0.71, 0.65, 0.61, 0.55, 0.52]
knc90_105_rei = [6.0, 5.75, 5.56, 5.38, 5.16, 4.91, 4.62, 4.29, 3.89, 3.45, 2.98, 2.51, 2.15, 1.85, 1.60, 1.42, 1.24, 1.13, 0.98, 0.91, 0.80, 0.73, 0.69, 0.62, 0.58]
knc100_115_rei = [6.67, 6.39, 6.18, 5.98, 5.74, 5.46, 5.13, 4.77, 4.33, 3.84, 3.31, 2.79, 2.39, 2.06, 1.78, 1.58, 1.37, 1.25, 1.09, 1.01, 0.89, 0.81, 0.77, 0.69, 0.65]
uhpc_unreinf = [1.5, 1.44, 1.39, 1.35, 1.29, 1.23, 1.15, 1.07, 0.97, 0.86, 0.75, 0.63, 0.54, 0.46, 0.40, 0.35, 0.31, 0.28, 0.25, 0.23, 0.20, 0.18, 0.17, 0.15, 0.15]
uhpc_fibre_reinforced = [10, 9.58, 9.27, 8.97, 8.61, 8.18, 7.70, 7.15, 6.48, 5.76, 4.97, 4.18, 3.58, 3.09, 2.67, 2.36, 2.06, 1.88, 1.64, 1.52, 1.33, 1.21, 1.15, 1.03, 0.97]
softwood_c16 = [0.86, 0.82, 0.80, 0.77, 0.74, 0.70, 0.66, 0.62, 0.56, 0.50, 0.43, 0.36, 0.31, 0.27, 0.23, 0.20, 0.18, 0.16, 0.14, 0.13, 0.11, 0.10, 0.10, 0.09, 0.08]
softwood_c24 = [1.30, 1.24, 1.21, 1.17, 1.12, 1.06, 1.00, 0.93, 0.84, 0.75, 0.65, 0.54, 0.46, 0.40, 0.35, 0.31, 0.27, 0.24, 0.21, 0.20, 0.17, 0.16, 0.15, 0.13, 0.13]
softwood_c30 = [1.63, 1.56, 1.51, 1.46, 1.40, 1.33, 1.25, 1.17, 1.06, 0.94, 0.81, 0.68, 0.58, 0.50, 0.43, 0.39, 0.34, 0.31, 0.27, 0.25, 0.22, 0.20, 0.19, 0.17, 0.16]
softwood_c35 = [1.89, 1.81, 1.75, 1.70, 1.63, 1.55, 1.45, 1.35, 1.23, 1.09, 0.94, 0.79, 0.68, 0.58, 0.50, 0.45, 0.39, 0.36, 0.31, 0.29, 0.25, 0.23, 0.22, 0.19, 0.18]
softwood_strength = [4, 3.83, 3.71, 3.59, 3.44, 3.27, 3.08, 2.86, 2.59, 2.30, 1.99, 1.67, 1.43, 1.24, 1.07, 0.95, 0.82, 0.75, 0.65, 0.61, 0.53, 0.48, 0.46, 0.41, 0.39]
hardwood_c30 = [1.63, 1.56, 1.51, 1.46, 1.40, 1.33, 1.25, 1.17, 1.06, 0.94, 0.81, 0.68, 0.58, 0.50, 0.43, 0.39, 0.34, 0.31, 0.27, 0.25, 0.22, 0.20, 0.19, 0.17, 0.16]
hardwood_c35 = [1.89, 1.81, 1.75, 1.70, 1.63, 1.55, 1.45, 1.35, 1.23, 1.09, 0.94, 0.79, 0.68, 0.58, 0.50, 0.45, 0.39, 0.36, 0.31, 0.29, 0.25, 0.23, 0.22, 0.19, 0.18]
hardwood_c40 = [2.17, 2.08, 2.01, 1.95, 1.87, 1.78, 1.67, 1.55, 1.41, 1.25, 1.08, 0.91, 0.78, 0.67, 0.58, 0.51, 0.45, 0.41, 0.36, 0.33, 0.29, 0.26, 0.25, 0.22, 0.21]
hardwood_c60 = [3.25, 3.11, 3.01, 2.92, 2.80, 2.66, 2.50, 2.32, 2.11, 1.87, 1.62, 1.36, 1.16, 1.00, 0.87, 0.77, 0.67, 0.61, 0.53, 0.49, 0.43, 0.39, 0.37, 0.33, 0.32]
hardwood_strength = [6, 5.75, 5.56, 5.38, 5.16, 4.91, 4.62, 4.29, 3.89, 3.45, 2.98, 2.51, 2.15, 1.85, 1.60, 1.42, 1.24, 1.13, 0.98, 0.91, 0.80, 0.73, 0.69, 0.62, 0.58]
glulam_24 = [1.30, 1.24, 1.21, 1.17, 1.12, 1.06, 1.00, 0.93, 0.84, 0.75, 0.65, 0.54, 0.46, 0.40, 0.35, 0.31, 0.27, 0.24, 0.21, 0.20, 0.17, 0.16, 0.15, 0.13, 0.13]
glulam_28 = [1.52, 1.46, 1.41, 1.36, 1.31, 1.24, 1.17, 1.09, 0.99, 0.88, 0.76, 0.64, 0.54, 0.47, 0.41, 0.36, 0.31, 0.29, 0.25, 0.23, 0.20, 0.18, 0.18, 0.16, 0.15]
glulam_30 = [1.63, 1.56, 1.51, 1.46, 1.40, 1.33, 1.25, 1.17, 1.06, 0.94, 0.81, 0.68, 0.58, 0.50, 0.43, 0.39, 0.34, 0.31, 0.27, 0.25, 0.22, 0.20, 0.19, 0.17, 0.16]
glulam_32 = [1.73, 1.66, 1.60, 1.55, 1.49, 1.42, 1.33, 1.24, 1.12, 1.00, 0.86, 0.72, 0.62, 0.53, 0.46, 0.41, 0.36, 0.33, 0.28, 0.26, 0.23, 0.21, 0.20, 0.18, 0.17]
masonry_old = [0.4, 0.38, 0.37, 0.36, 0.34, 0.33, 0.31, 0.29, 0.26, 0.23, 0.20, 0.17, 0.14, 0.12, 0.11, 0.09, 0.08, 0.08, 0.07, 0.06, 0.05, 0.05, 0.05, 0.04, 0.04]
masonry_new = [1.0, 0.96, 0.93, 0.90, 0.86, 0.82, 0.77, 0.72, 0.65, 0.58, 0.50, 0.42, 0.36, 0.31, 0.27, 0.24, 0.21, 0.19, 0.16, 0.15, 0.13, 0.12, 0.12, 0.10, 0.10]
kncustom = [16.5,15.8,15.3,14.8,14.2,13.5,12.7,11.8,10.7,9.5,8.2,6.9,5.9,5.1,4.4,3.9,3.4,3.1,2.7,2.5,2.2,2,1.9,1.7,1.6]

library = [
	# name, name in dropdown, E, G, d, acceptable_sigma, acceptable_shear, acceptable_torsion, acceptable_sigmav, knick_model
	# diese gelten nach ÖNORM B 4600 für den Erhöhungsfall und entsprechen 100 % beim Knicken (lamda<20)
	["steel_S235", "Steel S235", 21000, 8100, 7.85, 16.5, 9.5, 10.5, 23.5, kn235],
	["steel_S275", "Steel S275", 21000, 8100, 7.85, 20.5, 11, 12.5, 27.5, kn275],
	["steel_S355", "Steel S355", 21000, 8100, 7.85, 24.5, 13, 15, 35.5, kn355],
	["steel_S460N", "Steel S460N", 21000, 8100, 7.85, 31.7, 16.8, 19.4, 46, kn460n],
	["alu_Al_CU4Ti", "Alu Al-Cu4Ti", 8000, 3000, 2.70, 10, 7, 10.5, 22.0, knalu],
	["concrete_reinf_C12/15", "Concrete-reinforced C12/15", 2700, 1125, 2.5, 0.80, 0.07, 0.07, 1.2, knc12_15_rei],
	["concrete_reinf_C16/20", "Concrete-reinforced C16/20", 2900, 1208, 2.5, 1.07, 0.09, 0.09, 1.6, knc16_20_rei],
	["concrete_reinf_C20/25", "Concrete-reinforced C20/25", 3000, 1250, 2.5, 1.33, 0.105, 0.105, 2.0, knc20_25_rei],
	["concrete_reinf_C25/30", "Concrete-reinforced C25/30", 3100, 1292, 2.5, 1.67, 0.125, 0.125, 2.5, knc25_30_rei],
	["concrete_reinf_C30/37", "Concrete-reinforced C30/37", 3300, 1375, 2.5, 2.00, 0.140, 0.140, 3.0, knc30_37_rei],
	["concrete_reinf_C35/45", "Concrete-reinforced C35/45", 3400, 1417, 2.5, 2.33, 0.155, 0.150, 3.5, knc35_45_rei],
	["concrete_reinf_C40/50", "Concrete-reinforced C40/50", 3500, 1458, 2.5, 2.67, 0.165, 0.165, 4.0, knc40_50_rei],
	["concrete_reinf_C45/55", "Concrete-reinforced C45/55", 3600, 1500, 2.5, 3.00, 0.175, 0.175, 4.5, knc45_55_rei],
	["concrete_reinf_C50/60", "Concrete-reinforced C50/60", 3700, 1542, 2.5, 3.33, 0.194, 0.194, 5.0, knc50_60_rei],
	["concrete_reinf_C55/67", "Concrete-reinforced C55/67", 3800, 1583, 2.5, 3.67, 0.214, 0.214, 5.5, knc55_67_rei],
	["concrete_reinf_C60/75", "Concrete-reinforced C60/75", 3900, 1625, 2.5, 4.00, 0.233, 0.233, 6.0, knc60_75_rei],
	["concrete_reinf_C70/85", "Concrete-reinforced C70/85", 4100, 1708, 2.5, 4.67, 0.272, 0.272, 7.0, knc70_85_rei],
	["concrete_reinf_C80/95", "Concrete-reinforced C80/95", 4200, 1750, 2.5, 5.33, 0.311, 0.311, 8.0, knc80_95_rei],
	["concrete_reinf_C90/105", "Concrete-reinforced C90/105", 4400, 1833, 2.5, 6.00, 0.35, 0.35, 9.0, knc90_105_rei],
	["concrete_reinf_C100/115", "Concrete-reinforced C100/115", 4500, 1875, 2.5, 6.67, 0.389, 0.389, 10, knc100_115_rei],
	["UHPC_unreinforced", "UHPC-unreinforced", 5000, 2083, 2.4, 1.50, 0.5, 0.5, 1.5, uhpc_unreinf],
	["UHPC_fibre_reinforced", "UHPC-fibre reinforced", 5000, 2083, 2.5, 10, 1.5, 1.5, 10, uhpc_fibre_reinforced],

	["softwood_C16", "Softwood C16", 800, 50, 0.37, 0.86, 0.09, 0.09, 0.86, softwood_c16],
	["softwood_C24", "Softwood C24", 1100, 69, 0.42, 1.3, 0.10, 0.10, 1.30, softwood_c24],
	["softwood_C30", "Softwood C30", 1200, 75, 0.46, 1.63, 0.13, 0.13, 1.63, softwood_c30],
	["softwood_C35", "Softwood C35", 1300, 81, 0.47, 1.89, 0.15, 0.15, 1.89, softwood_c35],
	["softwood-strength", "Softwood strength", 1300, 81, 0.47, 4, 0.27, 0.27, 4, softwood_strength],

	["hardwood_C30", "Hardwood C30", 1100, 69, 0.64, 1.63, 0.13, 0.13, 1.63, hardwood_c30],
	["hardwood_C35", "Hardwood C35", 1200, 75, 0.65, 1.89, 0.15, 0.15, 1.89, hardwood_c35],
	["hardwood_C40", "Hardwood C40", 1300, 81, 0.66, 2.17, 0.17, 0.17, 2.17, hardwood_c40],
	["hardwood_C60", "Hardwood C60", 1700, 106, 0.84, 3.25, 0.33, 0.33, 3.25, hardwood_c60],
	["hardwood-strength", "Hardwood strength", 1700, 106, 0.84, 6, 0.41, 0.41, 6, hardwood_strength],

	["glulam_24", "Glulam GL24", 1150, 65, 0.42, 1.30, 0.10, 0.10, 1.30, glulam_24],
	["glulam_28", "Glulam GL28", 1260, 65, 0.46, 1.52, 0.116, 0.116, 1.52, glulam_28],
	["glulam_30", "Glulam GL30", 1360, 65, 0.48, 1.63, 0.16, 0.16, 1.63, glulam_30],
	["glulam_32", "Glulam GL32", 1420, 65, 0.49, 1.73, 0.17, 0.17, 1.73, glulam_32],

	["masonry_old", "Masonry old brick", 120, 48, 1.6, 0.4, 0.01, 0.01, 0.4, masonry_old],
	["masonry_new", "Masonry new brick", 400, 160, 1.6, 1.0, 0.03, 0.03, 1.0, 1.6, masonry_new],
	["custom", "Custom", 21000, 8100, 7.85, 16.0, 9.5, 10.5, 23.5, kncustom]
	]


dropdown = []
for material in library:
	dropdown_entry = (material[0], material[1], "")
	dropdown.append(dropdown_entry)

# current setting passed from gui
# (because a property can not be set in gui)
current = {}

def update():
	profile_type = current["profile_type"]

	if profile_type == "round_hollow":  # okay KD 2025-08-03
		diameter = current["height"]
		wall_thickness = current["wall_thickness"]
		Di = diameter - wall_thickness*2

		# moment of inertia, 32.9376 cm⁴
		current["Iy"] = pi * (diameter**4 - Di**4)/64
		current["Iz"] = current["Iy"]

		# torsional constant, 65.875 cm⁴
		current["J"] = pi * (diameter**4 - Di**4)/32 # gilt auch für vollquerschnitt, wenn Di=0

		# cross-sectional area, 8,64 cm²
		current["A"] = ((pi * (diameter*0.5)**2) - (pi * (Di*0.5)**2))

		# weight of profile, 6.78 kg/m
		current["weight_A"] =  current["A"]*current["rho"] * 0.1

		current["ir_y"] = sqrt(current["Iy"] / current["A"])
		current["ir_z"] = sqrt(current["Iz"] / current["A"])

	if profile_type == "round_solid":  # okay KD 2025-08-03
		diameter = current["height"]
		wall_thickness = current["wall_thickness"]
		current["Iy"] = pi * (diameter**4)/64
		current["Iz"] = current["Iy"]
		current["J"] = pi * (diameter**4)/32
		current["A"] = ((pi * (diameter*0.5)**2))
		current["weight_A"] =  current["A"]*current["rho"] * 0.1
		current["ir_y"] = sqrt(current["Iy"] / current["A"])
		current["ir_z"] = sqrt(current["Iz"] / current["A"])

			# depth auf width geändert
	if profile_type == "rect_hollow":
		height = current["height"]
		width = current["width"]
		t = current["wall_thickness"]

		# Innenmaße
		height_i = height - 2 * t
		width_i = width - 2 * t

		# Flächenträgheitsmomente
		current["Iy"] = (width * height**3 - width_i * height_i**3) / 12
		current["Iz"] = (height * width**3 - height_i * width_i**3) / 12

		# Querschnittsfläche
		current["A"] = height * width - height_i * width_i

		# Gewicht
		current["weight_A"] = current["A"] * current["rho"] * 0.1

		# Radius of gyration
		current["ir_y"] = sqrt(current["Iy"] / current["A"])
		current["ir_z"] = sqrt(current["Iz"] / current["A"])

	if profile_type == "rect_solid":
		height = current["height"]    # Breite (z-Richtung)
		width = current["width"]      # Höhe (y-Richtung)

		# Flächenträgheitsmomente korrigiert 2025-09-26
		current["Iy"] = (width * height**3) / 12  # um y-Achse
		current["Iz"] = (height * width**3) / 12  # um z-Achse

		# Querschnittsfläche
		current["A"] = height * width

		# Gewicht
		current["weight_A"] = current["A"] * current["rho"] * 0.1

		# Radius of gyration
		current["ir_y"] = sqrt(current["Iy"] / current["A"])
		current["ir_z"] = sqrt(current["Iz"] / current["A"])

	if profile_type == "large_steel_hollow":
		height = current["height"]		# Höhe (z-Richtung)
		width = current["width"]		# Breite (y-Richtung)
		f = current["wall_thickness"]	# Flanschdicke, die Stegbreite (beide zusammen) beträgt autom. 0.66 davon
		ss = f*0.33	# Stegdicke, fix

		# Flächenträgheitsmomente
		# Iy um horizontale y-Achse

		current["Iy"] = 2 * (width * f**3) / 12 + (f * width) * 2 * ((height - f) / 2) ** 2 + (height - 2 * f) ** 3 * (2 * ss) / 12
		# 1 Teil eigenträgheit des flansches, 2.Teil Steineranteil Flansch, 3.Teil. Eigen der beiden Stege
		# Iz um vertikale z-Achse
		current["Iz"] = 2 * ss**3 * (height - 2 * f) / 12 + 2 * ss * (height - 2 * f) * ((width - ss) / 2) ** 2 + 2 * width**3 * f * 2 / 12
		# 1 Teil eigenträgheit des Steges, 2.Teil Steineranteil Steg, 3.Teil. Eigen der beiden Flansche
		# Querschnittsfläche
		current["A"] = 2 * width*f + 2*(height-2*f)*ss  #
		# Näherung für Torsionskonstante eines rechteckigen Hohlprofils (nicht exakt!)
		# Für t << b,h, mittlere Dicke, Dicke x A/3
		current["J"] = (2 * f * 0.66) * (2 * width * f + 2 * (height - 2 * f) * ss) / 3
		# Gewicht
		current["weight_A"] = current["A"] * current["rho"] * 0.1

		# Radius of gyration
		current["ir_y"] = sqrt(current["Iy"] / current["A"])
		current["ir_z"] = sqrt(current["Iz"] / current["A"])

	if profile_type == "standard_profile":
		profile_id = current["profile"]
		profile = None
		for profile in profiles:
			if profile[0] == profile_id:
				current_profile = profile

		current["Iy"] = current_profile[8]
		current["Iz"] = current_profile[9]
		current["J"] = current_profile[10]
		current["A"] = current_profile[6]
		current["weight_A"] = current["A"] * current["rho"] * 0.1 # Gewicht vom Material
		current["ir_y"] = sqrt(current["Iy"] / current["A"])
		current["ir_z"] = sqrt(current["Iz"] / current["A"])

		# von Profil übertragen
		current["height"] = current_profile[2]*0.1   # Breite (z-Richtung) mm zu cm
		current["width"] = current_profile[3]*0.1    # Höhe (y-Richtung) mm zu cm

library_quads = [
	# name, name in dropdown, E, G, nu, rho, acceptable_sigma, acceptable_shear, acceptable_sigmav, knick_model
	["steel_S235", "Steel S235", 21000, 8100, 0.32, 7.85, 16.5, 9.5, 23.5, kn235],
	["steel_S275", "Steel S275", 21000, 8100, 0.32, 7.85, 20.5, 11, 27.5, kn275],
	["steel_S355", "Steel S355", 21000, 8100, 0.32, 7.85, 24.5, 13, 35.5, kn355],
	["steel_S460N", "Steel S460N", 21000, 8100, 0.32, 7.85, 31.7, 16.8, 46, kn460n],
	["alu_Al_CU4Ti", "Alu Al-Cu4Ti", 8000, 3000, 0.35, 2.70, 10, 7, 10.5, 22.0, knalu],
	["concrete_reinf_C12/15", "Concrete-reinforced C12/15", 2700, 1125, 0.2, 2.5, 0.80, 0.07, 1.2, knc12_15_rei],
	["concrete_reinf_C16/20", "Concrete-reinforced C16/20", 2900, 1208, 0.2, 2.5, 1.07, 0.09, 1.6, knc16_20_rei],
	["concrete_reinf_C20/25", "Concrete-reinforced C20/25", 3000, 1250, 0.2, 2.5, 1.33, 0.105, 2.0, knc20_25_rei],
	["concrete_reinf_C25/30", "Concrete-reinforced C25/30", 3100, 1292, 0.2, 2.5, 1.67, 0.125, 2.5, knc25_30_rei],
	["concrete_reinf_C30/37", "Concrete-reinforced C30/37", 3300, 1375, 0.2, 2.5, 2.00, 0.140, 3.0, knc30_37_rei],
	["concrete_reinf_C35/45", "Concrete-reinforced C35/45", 3400, 1417, 0.2, 2.5, 2.33, 0.155, 3.5, knc35_45_rei],
	["concrete_reinf_C40/50", "Concrete-reinforced C40/50", 3500, 1458, 0.2, 2.5, 2.67, 0.165, 4.0, knc40_50_rei],
	["concrete_reinf_C45/55", "Concrete-reinforced C45/55", 3600, 1500, 0.2, 2.5, 3.00, 0.175, 4.5, knc45_55_rei],
	["concrete_reinf_C50/60", "Concrete-reinforced C50/60", 3700, 1542, 0.2, 2.5, 3.33, 0.194, 5.0, knc50_60_rei],
	["concrete_reinf_C55/67", "Concrete-reinforced C55/67", 3800, 1583, 0.2, 2.5, 3.67, 0.214, 5.5, knc55_67_rei],
	["concrete_reinf_C60/75", "Concrete-reinforced C60/75", 3900, 1625, 0.2, 2.5, 4.00, 0.233, 6.0, knc60_75_rei],
	["concrete_reinf_C70/85", "Concrete-reinforced C70/85", 4100, 1708, 0.2, 2.5, 4.67, 0.272, 7.0, knc70_85_rei],
	["concrete_reinf_C80/95", "Concrete-reinforced C80/95", 4200, 1750, 0.2, 2.5, 5.33, 0.311, 8.0, knc80_95_rei],
	["concrete_reinf_C90/105", "Concrete-reinforced C90/105", 4400, 1833, 0.2, 2.5, 6.00, 0.35, 9.0, knc90_105_rei],
	["concrete_reinf_C100/115", "Concrete-reinforced C100/115", 4500, 1875, 0.2, 2.5, 6.67, 0.389, 10, knc100_115_rei],
	["UHPC_unreinforced", "UHPC-unreinforced", 5000, 2083, 0.2, 2.4, 1.50, 0.5, 1.5, uhpc_unreinf],
	["UHPC_fibre_reinforced", "UHPC-fibre reinforced", 5000, 2083, 0.2, 2.5, 10, 1.5, 10, uhpc_fibre_reinforced],

	["softwood_C16", "Softwood C16", 800, 50, 0.30, 0.37, 0.86, 0.09, 0.86, softwood_c16],
	["softwood_C24", "Softwood C24", 1100, 69, 0.30, 0.42, 1.3, 0.10, 1.30, softwood_c24],
	["softwood_C30", "Softwood C30", 1200, 75, 0.30, 0.46, 1.63, 0.13, 1.63, softwood_c30],
	["softwood_C35", "Softwood C35", 1300, 81, 0.30, 0.47, 1.89, 0.15, 1.89, softwood_c35],
	["softwood-strength", "Softwood strength", 1300, 81, 0.30, 0.47, 4, 0.27, 4, softwood_strength],

	["hardwood_C30", "Hardwood C30", 1100, 69, 0.30, 0.64, 1.63, 0.13, 1.63, hardwood_c30],
	["hardwood_C35", "Hardwood C35", 1200, 75, 0.30, 0.65, 1.89, 0.15, 1.89, hardwood_c35],
	["hardwood_C40", "Hardwood C40", 1300, 81, 0.30, 0.66, 2.17, 0.17, 2.17, hardwood_c40],
	["hardwood_C60", "Hardwood C60", 1700, 106, 0.30, 0.84, 3.25, 0.33, 3.25, hardwood_c60],
	["hardwood-strength", "Hardwood strength", 1700, 106, 0.30, 0.84, 6, 0.41, 6, hardwood_strength],

	["glulam_24", "Glulam GL24", 1150, 65, 0.30, 0.42, 1.30, 0.10, 1.30, glulam_24],
	["glulam_28", "Glulam GL28", 1260, 65, 0.30, 0.46, 1.52, 0.116, 1.52, glulam_28],
	["glulam_30", "Glulam GL30", 1360, 65, 0.30, 0.48, 1.63, 0.16, 1.63, glulam_30],
	["glulam_32", "Glulam GL32", 1420, 65, 0.30, 0.49, 1.73, 0.17, 1.73, glulam_32],

	["masonry_old", "Masonry old brick", 120, 48, 0.20, 1.6, 0.4, 0.01, 0.4, masonry_old],
	["masonry_new", "Masonry new brick", 400, 160, 0.20, 1.6, 1.0, 0.03, 1.0, masonry_new],
	["custom", "Custom", 21000, 8100, 0.30, 7.85, 16.0, 9.5, 16.0, kncustom]
	]


dropdown_quads = []
for material in library_quads:
	dropdown_entry = (material[0], material[1], "")
	dropdown_quads.append(dropdown_entry)

# current setting passed from gui
# (because a property can not be set in gui)
current_quads = {}

profiles = [
	#  0 = ID
	#  1 = Name
	#  2 = Höhe
	#  3 = Breite
	#  4 = Stegdicke
	#  5 = Flanschdicke
	#  6 = Querschnittsfläche
	#  7 = Masse
	#  8 = Trägheitsmoment I-y
	#  9 = Trägheitsmoment I-z
	# 10 = Trägheitsmoment I-T
	# 11 = i-y Trägheitsradius
	# 12 = i-z Trägheitsradius
	# 13 = I-y/A
	# 14 = I-z/A

	["IPE_80", "IPE 80", 80, 46, 3.8, 5.2, 7.6, 6, 80.1, 8.49, 0.698, 3.25, 1.06, 10.5, 1.12],
	["IPE_100", "IPE 100", 100, 55, 4.1, 5.7, 10.3, 8.1, 171, 15.9, 1.2, 4.07, 1.24, 16.6, 1.54],
	["IPE_120", "IPE 120", 120, 64, 4.4, 6.3, 13.2, 10.4, 318, 27.7, 1.74, 4.91, 1.45, 24.1, 2.10],
	["IPE_140", "IPE 140", 140, 73, 4.7, 6.9, 16.4, 12.9, 541, 44.9, 2.45, 5.74, 1.65, 33.0, 2.74],
	["IPE_160", "IPE 160", 160, 82, 5, 7.4, 20.1, 15.8, 869, 68.3, 3.6, 6.58, 1.84, 43.2, 3.40],
	["IPE_180", "IPE 180", 180, 91, 5.3, 8, 23.9, 18.8, 1320, 101, 4.79, 7.43, 2.06, 55.2, 4.23],
	["IPE_200", "IPE 200", 200, 100, 5.6, 8.5, 28.5, 22.4, 1940, 142, 6.98, 8.25, 2.23, 68.1, 4.98],
	["IPE_220", "IPE 220", 220, 110, 5.9, 9.2, 33.4, 26.2, 2770, 205, 9.07, 9.11, 2.48, 82.9, 6.14],
	["IPE_240", "IPE 240", 240, 120, 6.2, 9.8, 39.1, 30.7, 3890, 284, 12.9, 9.97, 2.70, 99.5, 7.26],
	["IPE_270", "IPE 270", 270, 135, 6.6, 10.2, 45.9, 36.1, 5790, 420, 15.9, 11.23, 3.02, 126.1, 9.15],
	["IPE_300", "IPE 300", 300, 150, 7.1, 10.7, 53.8, 42.2, 8360, 604, 20.1, 12.47, 3.35, 155.4, 11.23],
	["IPE_330", "IPE 330", 330, 160, 7.5, 11.5, 62.6, 49.1, 11770, 788, 28.1, 13.71, 3.55, 188.0, 12.59],
	["IPE_360", "IPE 360", 360, 170, 8, 12.7, 72.7, 57.1, 16270, 1040, 37.3, 14.96, 3.78, 223.8, 14.31],
	["IPE_400", "IPE 400", 400, 180, 8.6, 13.5, 84.5, 66.3, 23130, 1320, 51.1, 16.54, 3.95, 273.7, 15.62],
	["IPE_450", "IPE 450", 450, 190, 9.4, 14.6, 98.8, 77.6, 33740, 1680, 66.9, 18.48, 4.12, 341.5, 17.00],
	["IPE_500", "IPE 500", 500, 200, 10.2, 16, 115.5, 90.7, 48200, 2140, 89.3, 20.43, 4.30, 417.3, 18.53],
	["IPE_550", "IPE 550", 550, 210, 11.1, 17.2, 134.4, 105.5, 67120, 2670, 123, 22.35, 4.46, 499.4, 19.87],
	["IPE_600", "IPE 600", 600, 220, 12, 19, 156, 122.1, 92080, 3390, 165, 24.30, 4.66, 590.3, 21.73],
	["HEA_100", "HEA 100", 96, 100, 5, 8, 21.2, 16.7, 349, 134, 5.24, 4.06, 2.51, 16.5, 6.32],
	["HEA_120", "HEA 120", 114, 120, 5, 8, 25.3, 19.9, 606, 231, 5.99, 4.89, 3.02, 24.0, 9.13],
	["HEA_140", "HEA 140", 133, 140, 5.5, 8.5, 31.4, 24.7, 1030, 389, 8.13, 5.73, 3.52, 32.8, 12.39],
	["HEA_160", "HEA 160", 152, 160, 6, 9, 39.8, 30.4, 1670, 616, 12.2, 6.48, 3.98, 42.0, 15.48],
	["HEA_180", "HEA 180", 171, 180, 6, 9.5, 45.3, 35.5, 2510, 925, 14.8, 7.44, 4.52, 55.4, 20.42],
	["HEA_200", "HEA 200", 190, 200, 6.5, 10, 53.8, 42.3, 3690, 1340, 21, 8.28, 4.98, 68.6, 24.91],
	["HEA_220", "HEA 220", 210, 220, 7, 11, 64.3, 50.5, 5410, 1950, 28.5, 9.17, 5.51, 84.1, 30.33],
	["HEA_240", "HEA 240", 230, 240, 7.5, 12, 76.8, 60.3, 7760, 2770, 41.6, 10.05, 6, 101.0, 36.07],
	["HEA_260", "HEA 260", 250, 260, 7.5, 12.5, 86.8, 68.2, 10450, 3670, 52.4, 10.97, 6.5, 120.4, 42.28],
	["HEA_280", "HEA 280", 270, 280, 8, 13, 97.3, 76.4, 13670, 4760, 61.1, 11.85, 7, 140.5, 48.92],
	["HEA_300", "HEA 300", 290, 300, 8.5, 14, 112.5, 88.3, 18260, 6310, 85.2, 12.74, 7.49, 162.3, 56.09],
	["HEA_320", "HEA 320", 310, 300, 9, 15.5, 124.4, 97.6, 22930, 6990, 108, 13.58, 7.49, 184.3, 56.19],
	["HEA_340", "HEA 340", 330, 300, 9.5, 16.5, 133.5, 104.8, 27690, 7440, 127, 14.40, 7.46, 207.4, 55.73],
	["HEA_360", "HEA 360", 350, 300, 10, 17.5, 142.8, 112.1, 33090, 7890, 149, 15.22, 7.43, 231.7, 55.25],
	["HEA_400", "HEA 400", 390, 300, 11, 19, 159, 124.8, 45070, 8560, 189, 16.84, 7.34, 283.5, 53.84],
	["HEA_450", "HEA 450", 440, 300, 11.5, 21, 178, 139.8, 63720, 9470, 244, 18.92, 7.29, 358.0, 53.20],
	["HEA_500", "HEA 500", 490, 300, 12, 23, 197.5, 155.1, 86970, 10370, 309, 20.98, 7.24, 440.4, 52.51],
	["HEA_550", "HEA 550", 540, 300, 12.5, 24, 211.7, 166.2, 111900, 10820, 352, 22.99, 7.15, 528.6, 51.11],
	["HEA_600", "HEA 600", 590, 300, 13, 25, 226.5, 177.8, 141200, 11270, 398, 24.97, 7.05, 623.4, 49.76],
	["HEA_650", "HEA 650", 640, 300, 13.5, 26, 241.6, 189.7, 175200, 11720, 448, 26.93, 6.97, 725.2, 48.51],
	["HEA_700", "HEA 700", 690, 300, 14.5, 27, 260.5, 204.5, 215300, 12180, 514, 28.75, 6.84, 826.5, 46.76],
	["HEA_800", "HEA 800", 790, 300, 15, 28, 285.8, 224.4, 303400, 12640, 897, 32.58, 6.65, 1061.6, 44.23],
	["HEA_900", "HEA 900", 890, 300, 16, 30, 320.5, 251.6, 422100, 13550, 737, 36.29, 6.5, 1317.0, 42.28],
	["HEA_1000", "HEA 1000", 990, 300, 16.5, 31, 346.8, 272.3, 553800, 14000, 822, 39.96, 6.35, 1596.9, 40.37],
	["HEB_100", "HEB 100", 100, 100, 6, 10, 26, 20.1, 450, 167, 9.25, 4.160, 2.534, 17.3, 6.4],
	["HEB_120", "HEB 120", 120, 120, 6.5, 11, 34, 26.7, 864, 318, 13.8, 5.041, 3.058, 25.4, 9.4],
	["HEB_140", "HEB 140", 140, 140, 7, 12, 43, 33.7, 1510, 550, 20.1, 5.926, 3.576, 35.1, 12.8],
	["HEB_160", "HEB 160", 160, 160, 8, 13, 54.3, 42.6, 2490, 889, 31.2, 6.772, 4.046, 45.9, 16.4],
	["HEB_180", "HEB 180", 180, 180, 8.5, 14, 65.3, 51.2, 3830, 1360, 42.2, 7.658, 4.564, 58.7, 20.8],
	["HEB_200", "HEB 200", 200, 200, 9, 15, 78.1, 61.3, 5700, 2000, 59.3, 8.543, 5.060, 73.0, 25.6],
	["HEB_220", "HEB 220", 220, 220, 9.5, 16, 90, 71.5, 8090, 2840, 76.6, 9.481, 5.617, 89.9, 31.6],
	["HEB_240", "HEB 240", 240, 240, 10, 17, 106, 83.2, 11260, 3920, 103, 10.307, 6.081, 106.2, 37.0],
	["HEB_260", "HEB 260", 260, 260, 10, 17.5, 118.4, 93, 14920, 5130, 124, 11.226, 6.582, 126.0, 43.3],
	["HEB_280", "HEB 280", 280, 280, 10.5, 1, 131.4, 103.1, 19270, 6590, 144, 12.110, 7.082, 146.7, 50.2],
	["HEB_300", "HEB 300", 300, 300, 11, 19, 149.1, 117, 25170, 8560, 185, 12.993, 7.577, 168.8, 57.4],
	["HEB_320", "HEB 320", 320, 300, 11.5, 20.5, 161.3, 126.7, 30820, 9240, 225, 13.823, 7.569, 191.1, 57.3],
	["HEB_340", "HEB 340", 340, 300, 12, 21.5, 170.9, 134.2, 36660, 9690, 257, 14.646, 7.530, 214.5, 56.7],
	["HEB_360", "HEB 360", 360, 300, 12.5, 22.5, 180.6, 141.8, 43190, 10140, 292, 15.464, 7.493, 239.1, 56.1],
	["HEB_400", "HEB 400", 400, 300, 13.5, 24, 197.8, 155.3, 57680, 10820, 356, 17.077, 7.396, 291.6, 54.7],
	["HEB_450", "HEB 450", 450, 300, 14, 26, 218, 171.1, 79890, 11720, 440, 19.143, 7.332, 366.5, 53.8],
	["HEB_500", "HEB 500", 500, 300, 14.5, 28, 238.6, 187.3, 107200, 12620, 538, 21.196, 7.273, 449.3, 52.9],
	["HEB_550", "HEB 550", 550, 300, 15, 29, 254.1, 199.4, 136700, 13080, 600, 23.194, 7.175, 538.0, 51.5],
	["HEB_600", "HEB 600", 600, 300, 15.5, 30, 270, 211.9, 171000, 13530, 667, 25.166, 7.079, 633.3, 50.1],
	["HEB_650", "HEB 650", 650, 300, 16, 31, 286.3, 224.8, 210600, 13980, 739, 27.122, 6.988, 735.6, 48.8],
	["HEB_700", "HEB 700", 700, 300, 17, 32, 306.4, 240.5, 259900, 14440, 831, 29.125, 6.865, 848.2, 47.1],
	["HEB_800", "HEB 800", 800, 300, 17.5, 33, 334.2, 262.3, 359100, 14900, 946, 32.780, 6.677, 1074.5, 44.6],
	["HEB_900", "HEB 900", 900, 300, 18.5, 35, 371.3, 291.5, 494100, 15820, 1140, 36.479, 6.527, 1330.7, 42.6],
	["HEB_1000", "HEB 1000", 1000, 300, 19, 36, 400, 314, 644700, 16280, 1250, 40.147, 6.380, 1611.8, 40.7]
]

dropdown_profiles = []
for profile in profiles:
	dropdown_entry = (profile[0], profile[1], "")
	dropdown_profiles.append(dropdown_entry)
