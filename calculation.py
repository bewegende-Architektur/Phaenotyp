import bpy
import bmesh
from PyNite import FEModel3D
from numpy import array, empty, append, poly1d, polyfit
from phaenotyp import basics, material, progress
from math import sqrt
from math import tanh

from subprocess import Popen, PIPE
import sys
import os
import pickle

def print_data(text):
    print("Phaenotyp |", text)

def check_scipy():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]

    try:
        import scipy
        data["scipy_available"] = True

    except:
        data["scipy_available"] = False

def prepare_fea():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    frame = bpy.context.scene.frame_current
    truss = FEModel3D()

    # apply chromosome if available
    try:
        for id, key in enumerate(data.shape_keys):
            v = data.chromosome[str(frame)][id]
            key.value = v
    except:
        pass

    # get absolute position of vertex (when using shape-keys, animation et cetera)
    dg = bpy.context.evaluated_depsgraph_get()
    obj = data["structure"].evaluated_get(dg)

    mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
    vertices = mesh.vertices
    edges = mesh.edges
    faces = mesh.polygons

    # like suggested here by Gorgious and CodeManX:
    # https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
    mat = obj.matrix_world
    
    # to be collected:
    data["frames"][str(frame)] = {}
    frame_volume = 0
    frame_area = 0
    frame_length = 0
    frame_kg = 0
    
    # get volume of this frame
    bm = bmesh.new()
    bm.from_mesh(mesh)
    frame_volume = bm.calc_volume()
    
    # get area of the frame
    # overall sum of faces
    # user can delete faces to influence this as fitness in ga
    for face in faces:
        frame_area += face.area
    
    # add nodes from vertices
    for vertex in vertices:
        vertex_id = vertex.index
        name = "node_" + str(vertex_id)

        # like suggested here by Gorgious and CodeManX:
        # https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
        v = mat @ vertex.co

        x = v[0] * 100 # convert to cm for calculation
        y = v[1] * 100 # convert to cm for calculation
        z = v[2] * 100 # convert to cm for calculation

        truss.add_node(name, x,y,z)

    # define support
    supports = data["supports"]
    for id, support in supports.items():
        name = "node_" + str(id)
        truss.def_support(name, support[0], support[1], support[2], support[3], support[4], support[5])

    # create members
    members = data["members"]
    for id, member in members.items():
        name = "member_" + str(id)
        vertex_0_id = member["vertex_0_id"]
        vertex_1_id = member["vertex_1_id"]

        # like suggested here by Gorgious and CodeManX:
        # https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
        v_0 = mat @ vertices[vertex_0_id].co
        v_1 = mat @ vertices[vertex_1_id].co

        # save initial_positions to mix with deflection
        initial_positions = []
        for i in range(11):
            position = (v_0*(i) + v_1*(10-i))*0.1
            x = position[0]
            y = position[1]
            z = position[2]
            initial_positions.append([x,y,z])
        member["initial_positions"][str(frame)] = initial_positions

        node_0 = str("node_") + str(vertex_0_id)
        node_1 = str("node_") + str(vertex_1_id)

        truss.add_member(name, node_0, node_1, member["E"], member["G"], member["Iy"][str(frame)], member["Iz"][str(frame)], member["J"][str(frame)], member["A"][str(frame)])

        # add self weight
        kg = member["kg"][str(frame)]
        kN = kg * -0.0000981

        # add self weight as distributed load
        truss.add_member_dist_load(name, "FZ", kN, kN)
        
        # calculate lenght of parts (maybe usefull later ...)
        length = (v_0 - v_1).length
        frame_length += length
        
        # calculate and add weight to overall weight of structure
        frame_kg += length*kg

    # add loads
    loads_v = data["loads_v"]
    for id, load in loads_v.items():
        name = "node_" + str(id)
        truss.add_node_load(name, 'FX', load[0])
        truss.add_node_load(name, 'FY', load[1])
        truss.add_node_load(name, 'FZ', load[2])

    loads_e = data["loads_e"]
    for id, load in loads_e.items():
        name = "member_" + str(id)
        truss.add_member_dist_load(name, 'FX', load[0]*0.01, load[0]*0.01) # m to cm
        truss.add_member_dist_load(name, 'FY', load[1]*0.01, load[1]*0.01) # m to cm
        truss.add_member_dist_load(name, 'FZ', load[2]*0.01, load[2]*0.01) # m to cm

    loads_f = data["loads_f"]
    for id, load in loads_f.items():
        # int(id), otherwise crashing Speicherzugriffsfehler
        face = data["structure"].data.polygons[int(id)]
        org_normal = face.normal

        # apply matrix
        # like suggested here by Gorgious and CodeManX:
        # https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
        normal = mat @ org_normal

        edge_keys = face.edge_keys
        area = face.area

        load_normal = load[0]
        load_projected = load[1]
        load_area_z = load[2]

        # get projected area
        # based on answer from Nikos Athanasiou:
        # https://stackoverflow.com/questions/24467972/calculate-area-of-polygon-given-x-y-coordinates
        vertex_ids = face.vertices
        vertices_temp = []
        for vertex_id in vertex_ids:
            vertex = vertices[vertex_id]

            # like suggested here by Gorgious and CodeManX:
            # https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
            v = mat @ vertex.co

            vertices_temp.append(v)

        n = len(vertices_temp)
        a = 0.0
        for i in range(n):
            j = (i + 1) % n
            v_i = vertices_temp[i]
            v_j = vertices_temp[j]

            a += v_i[0] * v_j[1]
            a -= v_j[0] * v_i[1]

        area_projected = abs(a) / 2.0

        # get distances and perimeter
        distances = []
        for edge_key in edge_keys:
            vertex_0_id = edge_key[0]
            vertex_1_id = edge_key[1]

            # like suggested here by Gorgious and CodeManX:
            # https://blender.stackexchange.com/questions/6155/how-to-convert-coordinates-from-vertex-to-world-space
            vertex_0_co = mat @ vertices[vertex_0_id].co
            vertex_1_co = mat @ vertices[vertex_1_id].co

            dist_vector = vertex_0_co - vertex_1_co
            dist = dist_vector.length
            distances.append(dist)

        perimeter = sum(distances)

        # define loads for each edge
        edge_load_normal = []
        edge_load_projected = []
        edge_load_area_z = []

        ratio = 1 / len(edge_keys)
        for edge_id, dist in enumerate(distances):
            # load_normal
            area_load = load_normal * area
            edge_load = area_load * ratio / dist * 0.01 # m to cm
            edge_load_normal.append(edge_load)

            # load projected
            area_load = load_projected * area_projected
            edge_load = area_load * ratio / dist * 0.01 # m to cm
            edge_load_projected.append(edge_load)

            # load projected
            area_load = load_area_z * area
            edge_load = area_load * ratio / dist * 0.01 # m to cm
            edge_load_area_z.append(edge_load)

        # i is the id within the class (0, 1, 3 and maybe more)
        # edge_id is the id of the edge in the mesh -> the member
        for i, edge_key in enumerate(edge_keys):
            # get name <---------------------------------------- maybe better method?
            for edge in edges:
                if edge.vertices[0] in edge_key:
                    if edge.vertices[1] in edge_key:
                        name = "member_" + str(edge.index)

            # edge_load_normal <--------------------------------- to be tested / checked
            x = edge_load_normal[i] * normal[0]
            y = edge_load_normal[i] * normal[1]
            z = edge_load_normal[i] * normal[2]

            truss.add_member_dist_load(name, 'FX', x, x)
            truss.add_member_dist_load(name, 'FY', y, y)
            truss.add_member_dist_load(name, 'FZ', z, z)

            # edge_load_projected
            z = edge_load_projected[i]
            truss.add_member_dist_load(name, 'FZ', z, z)

            # edge_load_area_z
            z = edge_load_area_z[i]
            truss.add_member_dist_load(name, 'FZ', z, z)
    
    # store frame based data
    data["frames"][str(frame)]["volume"] = frame_volume
    data["frames"][str(frame)]["area"] = frame_area
    data["frames"][str(frame)]["length"] = frame_length
    data["frames"][str(frame)]["kg"] = frame_kg
    
    return truss

# run a singlethread calculation
def run_st(truss, frame):
    # scipy_available to pass forward
    if bpy.context.scene["<Phaenotyp>"]["scipy_available"]:
        truss.analyze(check_statics=False, sparse=True)
    else:
        truss.analyze(check_statics=False, sparse=False)
    
    feas = {}
    feas[str(frame)] = truss

    text = "singlethread job for frame " + str(frame) + " done"
    print_data(text)

    return feas

def run_mp(trusses):
    # get pathes
    path_addons = os.path.dirname(__file__) # path to the folder of addons
    path_script = path_addons + "/mp.py"
    path_python = sys.executable # path to bundled python
    path_blend = bpy.data.filepath # path to stored blender file
    directory_blend = os.path.dirname(path_blend) # directory of blender file
    name_blend = bpy.path.basename(path_blend) # name of file

    # pickle trusses to file
    path_export = directory_blend + "/Phaenotyp-export_mp.p"
    export_trusses = open(path_export, 'wb')
    pickle.dump(trusses, export_trusses)
    export_trusses.close()

    # scipy_available to pass forward
    if bpy.context.scene["<Phaenotyp>"]["scipy_available"]:
        scipy_available = "True" # as string
    else:
        scipy_available = "False" # as string

    task = [path_python, path_script, directory_blend, scipy_available]
    # feedback from python like suggested from Markus Amalthea Magnuson and user3759376 here
    # https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
    p = Popen(task, stdout=PIPE, bufsize=1)
    c = bpy.context.scene.frame_start
    end = bpy.context.scene.frame_end

    lines_iterator = iter(p.stdout.readline, b"")
    while p.poll() is None:
        for line in lines_iterator:
            nline = line.rstrip()
            print(nline.decode("utf8"), end = "\r\n",flush =True) # yield line
            progress.http.c = [c, end]
            c = c+1

    print("done")

    # get trusses back from mp
    path_import = directory_blend + "/Phaenotyp-return_mp.p"
    file = open(path_import, 'rb')
    imported_trusses = pickle.load(file)
    file.close()

    return imported_trusses

def interweave_results(feas, members):
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    members = scene["<Phaenotyp>"]["members"]

    end = bpy.context.scene.frame_end

    for frame, truss in feas.items():
        for id, member in members.items():
            name = "member_" + str(id)
            L = truss.Members[name].L() # Member length
            T = truss.Members[name].T() # Member local transformation matrix

            axial = []
            for i in range(11): # get the forces at 11 positions and
                axial_pos = truss.Members[name].axial(x=L/10*i)
                axial_pos = axial_pos * (-1) # Druckkraft gleich minus
                axial.append(axial_pos)
            member["axial"][str(frame)] = axial

            # buckling
            member["ir"][str(frame)] = sqrt(member["J"][str(frame)]/member["A"][str(frame)]) # für runde Querschnitte in  cm

            moment_y = []
            for i in range(11): # get the forces at 11 positions and
                moment_y_pos = truss.Members[name].moment("My", x=L/10*i)
                moment_y.append(moment_y_pos)
            member["moment_y"][str(frame)] = moment_y

            moment_z = []
            for i in range(11): # get the forces at 11 positions and
                moment_z_pos = truss.Members[name].moment("Mz", x=L/10*i)
                moment_z.append(moment_z_pos)
            member["moment_z"][str(frame)] = moment_z

            shear_y = []
            for i in range(11): # get the forces at 11 positions and
                shear_y_pos = truss.Members[name].shear("Fy", x=L/10*i)
                shear_y.append(shear_y_pos)
            member["shear_y"][str(frame)] = shear_y

            shear_z = []
            for i in range(11): # get the forces at 11 positions and
                shear_z_pos = truss.Members[name].shear("Fz", x=L/10*i)
                shear_z.append(shear_z_pos)
            member["shear_z"][str(frame)] = shear_z

            torque = []
            for i in range(11): # get the forces at 11 positions and
                torque_pos = truss.Members[name].torque(x=L/10*i)
                torque.append(torque_pos)
            member["torque"][str(frame)] = torque

            # modulus from the moments of area
            #(Wy and Wz are the same within a pipe)
            member["Wy"][str(frame)] = member["Iy"][str(frame)]/(member["Do"][str(frame)]/2)

            # polar modulus of torsion
            member["WJ"][str(frame)] = member["J"][str(frame)]/(member["Do"][str(frame)]/2)

            # calculation of the longitudinal stresses
            long_stress = []
            for i in range(11): # get the stresses at 11 positions and
                moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)
                if axial[i] > 0:
                    s = axial[i]/member["A"][str(frame)] + moment_h/member["Wy"][str(frame)]
                else:
                    s = axial[i]/member["A"][str(frame)] - moment_h/member["Wy"][str(frame)]
                long_stress.append(s)

            # get max stress of the beam
            # (can be positive or negative)
            member["long_stress"][str(frame)] = long_stress
            member["max_long_stress"][str(frame)] = basics.return_max_diff_to_zero(long_stress) #  -> is working as fitness

            # calculation of the shear stresses from shear force
            # (always positive)
            tau_shear = []
            shear_h = []
            for i in range(11): # get the stresses at 11 positions and
                # shear_h
                s_h = sqrt(shear_y[i]**2+shear_z[i]**2)
                shear_h.append(s_h)

                tau = 1.333 * s_h/member["A"][str(frame)] # for pipes
                tau_shear.append(tau)
            
            member["shear_h"][str(frame)] = shear_h

            # get max shear stress of shear force of the beam
            # shear stress is mostly small compared to longitudinal
            # in common architectural usage and only importand with short beam lenght
            member["tau_shear"][str(frame)] = tau_shear
            member["max_tau_shear"][str(frame)] = max(tau_shear)

            # Calculation of the torsion stresses
            # (always positiv)
            tau_torsion = []
            for i in range(11): # get the stresses at 11 positions and
                tau = abs(torque[i]/member["WJ"][str(frame)])
                tau_torsion.append(tau)

            # get max torsion stress of the beam
            member["tau_torsion"][str(frame)] = tau_torsion
            member["max_tau_torsion"][str(frame)] = max(tau_torsion)

            # torsion stress is mostly small compared to longitudinal
            # in common architectural usage

            # calculation of the shear stresses form shear force and torsion
            # (always positiv)
            sum_tau = []
            for i in range(11): # get the stresses at 11 positions and
                tau = tau_shear[0] + tau_torsion[0]
                sum_tau.append(tau)

            member["sum_tau"][str(frame)] = sum_tau
            member["max_sum_tau"][str(frame)] = max(sum_tau)

            # combine shear and torque
            sigmav = []
            for i in range(11): # get the stresses at 11 positions and
                sv = sqrt(long_stress[0]**2 + 3*sum_tau[0]**2)
                sigmav.append(sv)

            member["sigmav"][str(frame)] = sigmav
            member["max_sigmav"][str(frame)] = max(sigmav)
            # check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

            member["sigma"][str(frame)] = member["long_stress"][str(frame)]
            member["max_sigma"][str(frame)] = member["max_long_stress"][str(frame)]

            # for the definition of the fitness criteria prepared
            # max longitudinal stress for steel St360 in kN/cm²
            # tensile strength: 36 kN/cm², yield point 23.5 kN/cm²
            member["overstress"][str(frame)] = False

            # for example ["steel_S235", "steel S235", 21000, 8100, 7.85, 16.0, 9.5, 10.5, 23.5, knick_model235],
            #if abs(member["max_sigma"][str(frame)]) > member["acceptable_sigma"]:
            #    member["overstress"][str(frame)] = True

            # check overstress and add 1.05 savety factor
            safety_factor = 1.05
            if abs(member["max_tau_shear"][str(frame)]) > safety_factor*member["acceptable_shear"]:
                member["overstress"][str(frame)] = True

            if abs(member["max_tau_torsion"][str(frame)]) > safety_factor*member["acceptable_torsion"]:
                member["overstress"][str(frame)] = True

            if abs(member["max_sigmav"][str(frame)]) > safety_factor*member["acceptable_sigmav"]:
                member["overstress"][str(frame)] = True

            # buckling
            if member["axial"][str(frame)][0] < 0: # nur für Druckstäbe, axial kann nicht flippen?
                member["lamda"][str(frame)] = L*0.5/member["ir"][str(frame)] # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
                if member["lamda"][str(frame)] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
                    kn = member["knick_model"]
                    function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
                    member["acceptable_sigma_buckling"][str(frame)] = function_to_run(member["lamda"][str(frame)])
                    if member["lamda"][str(frame)] > 250: # Schlankheit zu schlank
                        member["overstress"][str(frame)] = True
                    if safety_factor*abs(member["acceptable_sigma_buckling"][str(frame)]) > abs(member["max_sigma"][str(frame)]): # Sigma
                        member["overstress"][str(frame)] = True

                else:
                    member["acceptable_sigma_buckling"][str(frame)] = member["acceptable_sigma"]

            # without buckling
            else:
                member["acceptable_sigma_buckling"][str(frame)] = member["acceptable_sigma"]
                member["lamda"][str(frame)] = None # to avoid missing KeyError


            if abs(member["max_sigma"][str(frame)]) > safety_factor*member["acceptable_sigma"]:
                member["overstress"][str(frame)] = True

            # lever_arm
            lever_arm = []
            moment_h = []
            for i in range(11):
                # moment_h
                m_h = sqrt(moment_y[i]**2+moment_z[i]**2)
                moment_h.append(m_h)

                # to avoid division by zero
                if member["axial"][str(frame)][i] < 0.1:
                    lv = m_h / 0.1
                else:
                    lv = m_h / member["axial"][str(frame)][i]

                lv = abs(lv) # absolute highest value within member
                lever_arm.append(lv)
            
            member["moment_h"][str(frame)] = moment_h
            member["lever_arm"][str(frame)] = lever_arm
            member["max_lever_arm"][str(frame)] = max(lever_arm)

            # Ausnutzungsgrad
            member["utilization"][str(frame)] = abs(member["max_long_stress"][str(frame)] / member["acceptable_sigma_buckling"][str(frame)])
            
            # Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
            # Berechnung der strain_energy für Normalkraft

            normalkraft_energie=[]
            for i in range(10): # get the energie at 10 positions for 10 section
                ne = (axial[i]**2)*(L/10)/(2*member["E"]*member["A"][str(frame)])
                normalkraft_energie.append(ne)
            member["normal_energy"][str(frame)] = normalkraft_energie

            # Berechnung der strain_energy für Moment
            moment_energie=[]
            for i in range(10): # get the energie at 10 positions for 10 section
                moment_hq = moment_y[i]**2+moment_z[i]**2
                me = (moment_hq * L/10) / (member["E"] * member["Wy"][str(frame)] * member["Do"][str(frame)])
                moment_energie.append(me)
            member["moment_energy"][str(frame)] = moment_energie

            # Summe von Normalkraft und Moment-Verzerrunsenergie
            strain_energy = []
            for i in range(10):
                value = normalkraft_energie[i] + moment_energie[i]
                strain_energy.append(value)
            member["strain_energy"][str(frame)] = strain_energy
            
            # deflection
            deflection = []

            # --> taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite
            scale_factor = 10.0

            cos_x = array([T[0,0:3]]) # Direction cosines of local x-axis
            cos_y = array([T[1,0:3]]) # Direction cosines of local y-axis
            cos_z = array([T[2,0:3]]) # Direction cosines of local z-axis

            DY_plot = empty((0, 3))
            for i in range(11):
                # Calculate the local y-direction displacement
                dy_tot = truss.Members[name].deflection('dy', L/10*i)

                # Calculate the scaled displacement in global coordinates
                DY_plot = append(DY_plot, dy_tot*cos_y*scale_factor, axis=0)

            # Calculate the local z-axis displacements at 20 points along the member's length
            DZ_plot = empty((0, 3))
            for i in range(11):
                # Calculate the local z-direction displacement
                dz_tot = truss.Members[name].deflection('dz', L/10*i)

                # Calculate the scaled displacement in global coordinates
                DZ_plot = append(DZ_plot, dz_tot*cos_z*scale_factor, axis=0)

            # Calculate the local x-axis displacements at 20 points along the member's length
            DX_plot = empty((0, 3))

            Xi = truss.Members[name].i_node.X
            Yi = truss.Members[name].i_node.Y
            Zi = truss.Members[name].i_node.Z

            for i in range(11):
                # Displacements in local coordinates
                dx_tot = [[Xi, Yi, Zi]] + (L/10*i + truss.Members[name].deflection('dx', L/10*i)*scale_factor)*cos_x

                # Magnified displacements in global coordinates
                DX_plot = append(DX_plot, dx_tot, axis=0)

            # Sum the component displacements to obtain overall displacement
            D_plot = DY_plot + DZ_plot + DX_plot

            # <-- taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite

            # add to results
            for i in range(11):
                x = D_plot[i, 0] * 0.01
                y = D_plot[i, 1] * 0.01
                z = D_plot[i, 2] * 0.01

                deflection.append([x,y,z])

            member["deflection"][str(frame)] = deflection
    
        # update progress
        progress.http.i = [int(frame), end]

def simple_sectional():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]
    frame = bpy.context.scene.frame_current

    for id, member in members.items():
        if abs(member["max_long_stress"][str(frame)]/member["acceptable_sigma_buckling"][str(frame)]) > 1:
            member["Do"][str(frame)] = member["Do"][str(frame)] * 1.2
            member["Di"][str(frame)] = member["Di"][str(frame)] * 1.2

        else:
            member["Do"][str(frame)] = member["Do"][str(frame)] * 0.8
            member["Di"][str(frame)] = member["Di"][str(frame)] * 0.8

        # set miminum size of Do and Di to avoid division by zero
        Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
        if member["Di"][str(frame)] < 0.1:
            member["Di"][str(frame)] = 0.1
            member["Do"][str(frame)] = member["Di"][str(frame)] * Do_Di_ratio

def utilization_sectional():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]
    frame = bpy.context.scene.frame_current

    for id, member in members.items():
        ang = member["utilization"][str(frame)]

        # bei Fachwerkstäben
        #faktor_d = sqrt(abs(ang))
        
        # bei Biegestäben
        faktor_d= (abs(ang))**(1/3)

        Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
        member["Do"][str(frame)] = member["Do"][str(frame)] * faktor_d
        member["Di"][str(frame)] = member["Di"][str(frame)] * faktor_d

        # set miminum size of Do and Di to avoid division by zero
        Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
        if member["Di"][str(frame)] < 0.1:
            member["Di"][str(frame)] = 0.1
            member["Do"][str(frame)] = member["Di"][str(frame)] * Do_Di_ratio

def complex_sectional():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]
    frame = bpy.context.scene.frame_current

    for id, member in members.items():
        #treshhold bei Prüfung!
        # without buckling (Zugstab)

        if abs(member["max_long_stress"][str(frame)]/member["acceptable_sigma_buckling"][str(frame)]) > 1:
            faktor_a = 1+(abs(member["max_long_stress"][str(frame)])/member["acceptable_sigma_buckling"][str(frame)]-1)*0.36

        else:
            faktor_a = 0.5 + 0.6*(tanh((abs(member["max_long_stress"][str(frame)])/member["acceptable_sigma_buckling"][str(frame)] -0.5)*2.4))

        # bei Fachwerkstäben
        #faktor_d = sqrt(abs(faktor_a))

        # bei Biegestäben
        faktor_d = (abs(faktor_a))**(1/3)

        member["Do"][str(frame)] = member["Do"][str(frame)]*faktor_d
        member["Di"][str(frame)] = member["Di"][str(frame)]*faktor_d

        # set miminum size of Do and Di to avoid division by zero
        Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
        if member["Di"][str(frame)] < 0.1:
            member["Di"][str(frame)] = 0.1
            member["Do"][str(frame)] = member["Di"][str(frame)] * Do_Di_ratio

def decimate_topology():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]
    obj = data["structure"] # applied to structure
    frame = bpy.context.scene.frame_current

    bpy.context.view_layer.objects.active = obj

    # create vertex-group if not existing
    bpy.ops.object.mode_set(mode = 'OBJECT')
    decimate_group = obj.vertex_groups.get("<Phaenotyp>decimate")
    if not decimate_group:
        decimate_group = obj.vertex_groups.new(name="<Phaenotyp>decimate")

    # create factor-list
    weights = []
    for vertex in obj.data.vertices:
        weights.append([])

    # create factors for nodes from members
    for id, member in members.items():
        factor = abs(member["max_long_stress"][str(frame)]/member["acceptable_sigma_buckling"][str(frame)])
        # first node
        vertex_0_id = member["vertex_0_id"]
        weights[vertex_0_id].append(factor)

        # second node
        vertex_1_id = member["vertex_1_id"]
        weights[vertex_1_id].append(factor)

    # sum up forces of each node and get highest value
    sums = []
    highest_sum = 0
    for id, weights_per_node in enumerate(weights):
        sum = 0
        if len(weights_per_node) > 0:
            for weight in weights_per_node:
                sum = sum + weight
                if sum > highest_sum:
                    highest_sum = sum

        sums.append(sum)


    for id, sum in enumerate(sums):
        weight = 1 / highest_sum * sum
        decimate_group.add([id], weight, 'REPLACE')


    # delete modifiere if existing
    try:
        bpy.ops.object.modifier_remove(modifier="<Phaenotyp>decimate")
    except:
        pass

    # create decimate modifiere
    mod = obj.modifiers.new("<Phaenotyp>decimate", "DECIMATE")
    mod.ratio = 0.1
    mod.vertex_group = "<Phaenotyp>decimate"
