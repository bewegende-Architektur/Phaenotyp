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
knalu = [10.0,9.6,9.3,9,8.6,8.2,7.7,7.2,6.5,5.8,5.0,4.2,3.6,3.1,2.7,2.4,2.1,1.9,1.6,1.5,1.3,1.2,1.2,1.0,1.0]
knholz = [1.60,1.33,1.28,1.20,1.11,1,0.86,0.71,0.56,0.46,0.38,0.32,0.27,0.23,0.2,0.18,0.16,0.14,0.127,0.114,0.114,0.114,0.114,0.114,0.114]
kncustom = [16.5,15.8,15.3,14.8,14.2,13.5,12.7,11.8,10.7,9.5,8.2,6.9,5.9,5.1,4.4,3.9,3.4,3.1,2.7,2.5,2.2,2,1.9,1.7,1.6]

library = [
    # name, name in dropdown, E, G, d, acceptable_sigma, acceptable_shear, acceptable_torsion, acceptable_sigmav, knick_model
    # diese gelten nach ÖNORM B 4600 für den Erhöhungsfall und entsprechen 100 % beim Knicken (lamda<20)
    ["steel_S235", "steel S235", 21000, 8100, 7.85, 16.5, 9.5, 10.5, 23.5, kn235],
    ["steel_S275", "steel S275", 21000, 8100, 7.85, 20.5, 11, 12.5, 27.5, kn275],
    ["steel_S355", "steel S355", 21000, 8100, 7.85, 24.5, 13, 15, 35.5, kn355],
    ["alu_EN_AC_Al_CU4Ti", "alu EN-AC Al Cu4Ti", 8000, 3000, 2.70, 10, 7, 10.5, 22.0, knalu],
    ["wood", "wood", 1000, 55, 0.35, 1.6, 0.1, 0.1, 2, knholz],
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
    # moment of inertia, 32.9376 cm⁴
    current["Iy"] = pi * (current["Do"]**4 - current["Di"]**4)/64
    current["Iz"] = current["Iy"]

    # torsional constant, 65.875 cm⁴
    current["J"] = pi * (current["Do"]**4 - current["Di"]**4)/(32)

    # cross-sectional area, 8,64 cm²
    current["A"] = ((pi * (current["Do"]*0.5)**2) - (pi * (current["Di"]*0.5)**2))

    # weight of profile, 6.79 kg/m
    current["kg_A"] =  current["A"]*current["d"] * 0.1

    current["ir"] = sqrt(current["Iy"]/current["A"])
