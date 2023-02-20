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
        kg_A = member["kg_A"][str(frame)]
        kN = kg_A * -0.0000981

        # add self weight as distributed load
        truss.add_member_dist_load(name, "FZ", kN, kN)

        # calculate lenght of parts (maybe usefull later ...)
        length = (v_0 - v_1).length
        frame_length += length

        # calculate and add weight to overall weight of structure
        kg = length * kg_A
        frame_kg += kg

        # store in member
        member["kg"][str(frame)] = kg
        member["length"][str(frame)] = length

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

    end = bpy.context.scene.frame_end

    for frame, truss in feas.items():
        for id, member in members.items():
            name = "member_" + str(id)
            truss_member = truss.Members[name]
            L = truss_member.L() # Member length
            T = truss_member.T() # Member local transformation matrix

            axial = []
            moment_y = []
            moment_z = []
            shear_y = []
            shear_z = []
            torque = []

            for i in range(11): # get the forces at 11 positions and
                x = L/10*i

                axial_pos = truss_member.axial(x) * (-1) # Druckkraft minus
                axial.append(axial_pos)

                moment_y_pos = truss_member.moment("My", x)
                moment_y.append(moment_y_pos)

                moment_z_pos = truss_member.moment("Mz", x)
                moment_z.append(moment_z_pos)

                shear_y_pos = truss_member.shear("Fy", x)
                shear_y.append(shear_y_pos)

                shear_z_pos = truss_member.shear("Fz", x)
                shear_z.append(shear_z_pos)

                torque_pos = truss_member.torque(x)
                torque.append(torque_pos)

            member["axial"][frame] = axial
            member["moment_y"][frame] = moment_y
            member["moment_z"][frame] = moment_z
            member["shear_y"][frame] = shear_y
            member["shear_z"][frame] = shear_z
            member["torque"][frame] = torque

            # shorten and accessing once
            A = member["A"][frame]
            J = member["J"][frame]
            Do = member["Do"][frame]

            # buckling
            member["ir"][frame] = sqrt(J/A) # für runde Querschnitte in  cm

            # modulus from the moments of area
            #(Wy and Wz are the same within a pipe)
            member["Wy"][frame] = member["Iy"][frame]/(Do/2)

            # polar modulus of torsion
            member["WJ"][frame] = J/(Do/2)

            # calculation of the longitudinal stresses
            long_stress = []
            for i in range(11): # get the stresses at 11 positions and
                moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)
                if axial[i] > 0:
                    s = axial[i]/A + moment_h/member["Wy"][frame]
                else:
                    s = axial[i]/A - moment_h/member["Wy"][frame]
                long_stress.append(s)

            # get max stress of the beam
            # (can be positive or negative)
            member["long_stress"][frame] = long_stress
            member["max_long_stress"][frame] = basics.return_max_diff_to_zero(long_stress) #  -> is working as fitness

            # calculation of the shear stresses from shear force
            # (always positive)
            tau_shear = []
            shear_h = []
            for i in range(11): # get the stresses at 11 positions and
                # shear_h
                s_h = sqrt(shear_y[i]**2+shear_z[i]**2)
                shear_h.append(s_h)

                tau = 1.333 * s_h/A # for pipes
                tau_shear.append(tau)

            member["shear_h"][frame] = shear_h

            # get max shear stress of shear force of the beam
            # shear stress is mostly small compared to longitudinal
            # in common architectural usage and only importand with short beam lenght
            member["tau_shear"][frame] = tau_shear
            member["max_tau_shear"][frame] = max(tau_shear)

            # Calculation of the torsion stresses
            # (always positiv)
            tau_torsion = []
            for i in range(11): # get the stresses at 11 positions and
                tau = abs(torque[i]/member["WJ"][frame])
                tau_torsion.append(tau)

            # get max torsion stress of the beam
            member["tau_torsion"][frame] = tau_torsion
            member["max_tau_torsion"][frame] = max(tau_torsion)

            # torsion stress is mostly small compared to longitudinal
            # in common architectural usage

            # calculation of the shear stresses form shear force and torsion
            # (always positiv)
            sum_tau = []
            for i in range(11): # get the stresses at 11 positions and
                tau = tau_shear[0] + tau_torsion[0]
                sum_tau.append(tau)

            member["sum_tau"][frame] = sum_tau
            member["max_sum_tau"][frame] = max(sum_tau)

            # combine shear and torque
            sigmav = []
            for i in range(11): # get the stresses at 11 positions and
                sv = sqrt(long_stress[0]**2 + 3*sum_tau[0]**2)
                sigmav.append(sv)

            member["sigmav"][frame] = sigmav
            member["max_sigmav"][frame] = max(sigmav)
            # check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

            member["sigma"][frame] = member["long_stress"][frame]
            member["max_sigma"][frame] = member["max_long_stress"][frame]

            # overstress
            member["overstress"][frame] = False

            # check overstress and add 1.05 savety factor
            safety_factor = 1.05
            if abs(member["max_tau_shear"][frame]) > safety_factor*member["acceptable_shear"]:
                member["overstress"][frame] = True

            if abs(member["max_tau_torsion"][frame]) > safety_factor*member["acceptable_torsion"]:
                member["overstress"][frame] = True

            if abs(member["max_sigmav"][frame]) > safety_factor*member["acceptable_sigmav"]:
                member["overstress"][frame] = True

            # buckling
            if member["axial"][frame][0] < 0: # nur für Druckstäbe, axial kann nicht flippen?
                member["lamda"][frame] = L*0.5/member["ir"][frame] # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
                if member["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
                    kn = member["knick_model"]
                    function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
                    member["acceptable_sigma_buckling"][frame] = function_to_run(member["lamda"][frame])
                    if member["lamda"][frame] > 250: # Schlankheit zu schlank
                        member["overstress"][frame] = True
                    if safety_factor*abs(member["acceptable_sigma_buckling"][frame]) > abs(member["max_sigma"][frame]): # Sigma
                        member["overstress"][frame] = True

                else:
                    member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]

            # without buckling
            else:
                member["acceptable_sigma_buckling"][frame] = member["acceptable_sigma"]
                member["lamda"][frame] = None # to avoid missing KeyError


            if abs(member["max_sigma"][frame]) > safety_factor*member["acceptable_sigma"]:
                member["overstress"][frame] = True

            # lever_arm
            lever_arm = []
            moment_h = []
            for i in range(11):
                # moment_h
                m_h = sqrt(moment_y[i]**2+moment_z[i]**2)
                moment_h.append(m_h)

                # to avoid division by zero
                if member["axial"][frame][i] < 0.1:
                    lv = m_h / 0.1
                else:
                    lv = m_h / member["axial"][frame][i]

                lv = abs(lv) # absolute highest value within member
                lever_arm.append(lv)

            member["moment_h"][frame] = moment_h
            member["lever_arm"][frame] = lever_arm
            member["max_lever_arm"][frame] = max(lever_arm)

            # Ausnutzungsgrad
            member["utilization"][frame] = abs(member["max_long_stress"][frame] / member["acceptable_sigma_buckling"][frame])

            # Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
            normalkraft_energie=[]
            moment_energie=[]
            strain_energy = []

            for i in range(10): # get the energie at 10 positions for 10 section
                # Berechnung der strain_energy für Normalkraft
                ne = (axial[i]**2)*(L/10)/(2*member["E"]*A)
                normalkraft_energie.append(ne)

                # Berechnung der strain_energy für Moment
                moment_hq = moment_y[i]**2+moment_z[i]**2
                me = (moment_hq * L/10) / (member["E"] * member["Wy"][frame] * Do)
                moment_energie.append(me)

                # Summe von Normalkraft und Moment-Verzerrunsenergie
                value = ne + me
                strain_energy.append(value)

            member["strain_energy"][frame] = strain_energy
            member["normal_energy"][frame] = normalkraft_energie
            member["moment_energy"][frame] = moment_energie

            # deflection
            deflection = []

            # --> taken from pyNite VisDeformedMember: https://github.com/JWock82/PyNite
            scale_factor = 10.0

            cos_x = array([T[0,0:3]]) # Direction cosines of local x-axis
            cos_y = array([T[1,0:3]]) # Direction cosines of local y-axis
            cos_z = array([T[2,0:3]]) # Direction cosines of local z-axis

            DY_plot = empty((0, 3))
            DZ_plot = empty((0, 3))

            for i in range(11):
                # Calculate the local y-direction displacement
                dy_tot = truss_member.deflection('dy', L/10*i)

                # Calculate the scaled displacement in global coordinates
                DY_plot = append(DY_plot, dy_tot*cos_y*scale_factor, axis=0)

                # Calculate the local z-direction displacement
                dz_tot = truss_member.deflection('dz', L/10*i)

                # Calculate the scaled displacement in global coordinates
                DZ_plot = append(DZ_plot, dz_tot*cos_z*scale_factor, axis=0)

            # Calculate the local x-axis displacements at 20 points along the member's length
            DX_plot = empty((0, 3))

            Xi = truss_member.i_node.X
            Yi = truss_member.i_node.Y
            Zi = truss_member.i_node.Z

            for i in range(11):
                # Displacements in local coordinates
                dx_tot = [[Xi, Yi, Zi]] + (L/10*i + truss_member.deflection('dx', L/10*i)*scale_factor)*cos_x

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

            member["deflection"][frame] = deflection

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
