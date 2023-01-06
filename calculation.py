import bpy
from PyNite import FEModel3D
from numpy import array, empty, append, poly1d, polyfit
from phaenotyp import basics, material
from math import sqrt
from math import tanh

import multiprocessing
manager = multiprocessing.Manager() # needed for mp
feas = manager.dict() # is saving all calculations accesables by frame
fea_jobs = [] # to store jobs


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

    # add nodes from vertices
    for vertex in vertices:
        vertex_id = vertex.index
        name = "node_" + str(vertex_id)
        x = vertex.co[0] * 100 # convert to cm for calculation
        y = vertex.co[1] * 100 # convert to cm for calculation
        z = vertex.co[2] * 100 # convert to cm for calculation

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

        # save initial_positions to mix with deflection
        initial_positions = []
        for i in range(11):
            position = (vertices[vertex_0_id].co*(i) + vertices[vertex_1_id].co*(10-i))*0.1
            x = position[0]
            y = position[1]
            z = position[2]
            initial_positions.append([x,y,z])
        member["initial_positions"][str(frame)] = initial_positions

        node_0 = str("node_") + str(vertex_0_id)
        node_1 = str("node_") + str(vertex_1_id)

        truss.add_member(name, node_0, node_1, member["E"], member["G"], member["Iy"][str(frame)], member["Iz"][str(frame)], member["J"][str(frame)], member["A"][str(frame)])

        # add self weight
        kN = member["kg"][str(frame)] * -0.0000981

        # add self weight
        truss.add_member_dist_load(name, "FZ", kN, kN)


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
        truss.add_member_dist_load(name, 'FX', load[0], load[0])
        truss.add_member_dist_load(name, 'FY', load[1], load[1])
        truss.add_member_dist_load(name, 'FZ', load[2], load[2])

    loads_f = data["loads_f"]
    for id, load in loads_f.items():
        face = data["structure"].data.polygons[id]
        edge_keys = face.edge_keys
        normal = face.normal
        area = face.area

        load_normal = load[0]
        load_projected = load[1]
        load_area_z = load[2]

        # get projected area
        # based on: https://stackoverflow.com/questions/24467972/calculate-area-of-polygon-given-x-y-coordinates
        vertex_ids = face.vertices
        vertices_temp = []
        for vertex_id in vertex_ids:
            vertex = vertices[vertex_id]
            vertices_temp.append(vertex)

        n = len(vertices_temp)
        a = 0.0
        for i in range(n):
            j = (i + 1) % n
            a += vertices[i].co[0] * vertices[j].co[1]
            a -= vertices[j].co[0] * vertices[i].co[1]

        area_projected = abs(a) / 2.0

        # get distances and perimeter
        distances = []
        for edge_key in load.edge_keys:
            vertex_0_id = edge_key[0]
            vertex_1_id = edge_key[1]

            vertex_0_co = vertices[vertex_0_id].co
            vertex_1_co = vertices[vertex_1_id].co

            dist_vector = vertex_0_co - vertex_1_co
            dist = dist_vector.length
            distances.append(dist)

        perimeter = sum(distances)

        # define loads for each edge
        edge_load_normal = []
        edge_load_projected = []
        edge_load_area_z = []

        for edge_id, dist in enumerate(distances):
            ratio = 1 / perimeter * dist

            # load_normal
            area_load = load_normal * area
            edge_load = area_load * ratio
            edge_load_normal.append(edge_load)

            # load projected
            area_load = load_projected * area_projected
            edge_load = area_load * ratio
            edge_load_projected.append(edge_load)

            # load projected
            area_load = load_area_z * area
            edge_load = area_load * ratio
            edge_load_area_z.append(edge_load)

        # i is the id within the class (0, 1, 3 and maybe more)
        # edge_id is the id of the edge in the mesh -> the member
        for edge_key in load.edge_keys:
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

    return truss

def run_fea(feas, truss, members, frame):
    # the variables turss, members and frame are passed to mp
    # this variables can not be returned with multiprocessing
    # instead of this a dict with multiprocessing.Manager is created
    # the dict feas stores one anlysis for each frame
    # the dict fea is created temporarily in run_fea and is wirrten to feas

    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]

    # analyze the model
    if data["scipy_available"] and phaenotyp.use_scipy:
        truss.analyze(check_statics=False, sparse=True)
    else:
        truss.analyze(check_statics=False, sparse=False)

    fea = {}

    # get forces
    for id, member in members.items():
        result = {} # stores result for one member

        result["axial"] = {}
        result["moment_y"] = {}
        result["moment_z"] = {}
        result["shear_y"] = {}
        result["shear_z"] = {}
        result["torque"] = {}
        result["sigma"] = {}

        result["ir"] = {}
        result["Wy"] = {}
        result["WJ"] = {}

        result["long_stress"] = {}
        result["tau_shear"] = {}
        result["tau_torsion"] = {}
        result["sum_tau"] = {}
        result["sigmav"] = {}
        result["sigma"] = {}
        result["max_long_stress"] = {}
        result["max_tau_shear"] = {}
        result["max_tau_torsion"] = {}
        result["max_sum_tau"] = {}
        result["max_sigmav"] = {}
        result["max_sigma"] = {}
        result["acceptable_sigma_buckling"] = {}
        result["lamda"] = {}
        result["lever_arm"] = {}
        result["max_lever_arm"] = {}
        member["initial_positions"] = {} # <----------------- nicht verwendet?
        result["deflection"] = {}
        result["overstress"] = {}

        id = str(id)
        name = "member_" + str(id)
        L = truss.Members[name].L() # Member length
        T = truss.Members[name].T() # Member local transformation matrix

        axial = []
        for i in range(11): # get the forces at 11 positions and
            axial_pos = truss.Members[name].axial(x=L/10*i)
            axial_pos = axial_pos * (-1) # Druckkraft gleich minus
            axial.append(axial_pos)
        result["axial"][str(frame)] = axial

        # buckling
        result["ir"][str(frame)] = sqrt(member["J"][str(frame)]/member["A"][str(frame)]) # für runde Querschnitte in  cm

        moment_y = []
        for i in range(11): # get the forces at 11 positions and
            moment_y_pos = truss.Members[name].moment("My", x=L/10*i)
            moment_y.append(moment_y_pos)
        result["moment_y"][str(frame)] = moment_y

        moment_z = []
        for i in range(11): # get the forces at 11 positions and
            moment_z_pos = truss.Members[name].moment("Mz", x=L/10*i)
            moment_z.append(moment_z_pos)
        result["moment_z"][str(frame)] = moment_z

        shear_y = []
        for i in range(11): # get the forces at 11 positions and
            shear_y_pos = truss.Members[name].shear("Fy", x=L/10*i)
            shear_y.append(shear_y_pos)
        result["shear_y"][str(frame)] = shear_y

        shear_z = []
        for i in range(11): # get the forces at 11 positions and
            shear_z_pos = truss.Members[name].shear("Fz", x=L/10*i)
            shear_z.append(shear_z_pos)
        result["shear_z"][str(frame)] = shear_z

        torque = []
        for i in range(11): # get the forces at 11 positions and
            torque_pos = truss.Members[name].torque(x=L/10*i)
            torque.append(torque_pos)
        result["torque"][str(frame)] = torque

        # modulus from the moments of area
        #(Wy and Wz are the same within a pipe)
        result["Wy"][str(frame)] = member["Iy"][str(frame)]/(member["Do"][str(frame)]/2)

        # polar modulus of torsion
        result["WJ"][str(frame)] = member["J"][str(frame)]/(member["Do"][str(frame)]/2)

        # calculation of the longitudinal stresses
        long_stress = []
        for i in range(11): # get the stresses at 11 positions and
            moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)
            if axial[i] > 0:
                s = axial[i]/member["A"][str(frame)] + moment_h/result["Wy"][str(frame)]
            else:
                s = axial[i]/member["A"][str(frame)] - moment_h/result["Wy"][str(frame)]
            long_stress.append(s)

        # get max stress of the beam
        # (can be positive or negative)
        result["long_stress"][str(frame)] = long_stress
        result["max_long_stress"][str(frame)] = basics.return_max_diff_to_zero(long_stress) #  -> is working as fitness

        # calculation of the shear stresses from shear force
        # (always positive)
        tau_shear = []
        for i in range(11): # get the stresses at 11 positions and
            shear_h = sqrt(shear_y[i]**2+shear_z[i]**2)
            tau = 1.333 * shear_h/member["A"][str(frame)] # for pipes
            tau_shear.append(tau)

        # get max shear stress of shear force of the beam
        # shear stress is mostly small compared to longitudinal
        # in common architectural usage and only importand with short beam lenght
        result["tau_shear"][str(frame)] = tau_shear
        result["max_tau_shear"][str(frame)] = max(tau_shear)

        # Calculation of the torsion stresses
        # (always positiv)
        tau_torsion = []
        for i in range(11): # get the stresses at 11 positions and
            tau = abs(torque[i]/result["WJ"][str(frame)])
            tau_torsion.append(tau)

        # get max torsion stress of the beam
        result["tau_torsion"][str(frame)] = tau_torsion
        result["max_tau_torsion"][str(frame)] = max(tau_torsion)

        # torsion stress is mostly small compared to longitudinal
        # in common architectural usage

        # calculation of the shear stresses form shear force and torsion
        # (always positiv)
        sum_tau = []
        for i in range(11): # get the stresses at 11 positions and
            tau = tau_shear[0] + tau_torsion[0]
            sum_tau.append(tau)

        result["sum_tau"][str(frame)] = sum_tau
        result["max_sum_tau"][str(frame)] = max(sum_tau)

        # combine shear and torque
        sigmav = []
        for i in range(11): # get the stresses at 11 positions and
            sv = sqrt(long_stress[0]**2 + 3*sum_tau[0]**2)
            sigmav.append(sv)

        result["sigmav"][str(frame)] = sigmav
        result["max_sigmav"][str(frame)] = max(sigmav)
        # check out: http://www.bs-wiki.de/mediawiki/index.php?title=Festigkeitsberechnung

        result["sigma"][str(frame)] = result["long_stress"][str(frame)]
        result["max_sigma"][str(frame)] = result["max_long_stress"][str(frame)]

        # for the definition of the fitness criteria prepared
        # max longitudinal stress for steel St360 in kN/cm²
        # tensile strength: 36 kN/cm², yield point 23.5 kN/cm²
        result["overstress"][str(frame)] = False

        # for example ["steel_S235", "steel S235", 21000, 8100, 7.85, 16.0, 9.5, 10.5, 23.5, knick_model235],
        if abs(result["max_sigma"][str(frame)]) > member["acceptable_sigma"]:
            result["overstress"][str(frame)] = True

        if abs(result["max_tau_shear"][str(frame)]) > member["acceptable_shear"]:
            result["overstress"][str(frame)] = True

        if abs(result["max_tau_torsion"][str(frame)]) > member["acceptable_torsion"]:
            result["overstress"][str(frame)] = True

        if abs(result["max_sigmav"][str(frame)]) > member["acceptable_sigmav"]:
            result["overstress"][str(frame)] = True

        # buckling
        if result["axial"][str(frame)][0] < 0: # nur für Druckstäbe - axial ist überall im Stab gleich?
            result["lamda"][str(frame)] = L*0.5/result["ir"][str(frame)] # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
            if result["lamda"][str(frame)] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
                kn = member["knick_model"]
                function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
                result["acceptable_sigma_buckling"][str(frame)] = function_to_run(result["lamda"][str(frame)])
                if result["lamda"][str(frame)] > 250: # Schlankheit zu schlank
                    result["overstress"][str(frame)] = True
                if abs(result["acceptable_sigma_buckling"][str(frame)]) > abs(result["max_sigma"][str(frame)]): # Sigma
                    result["overstress"][str(frame)] = True

            else:
                result["acceptable_sigma_buckling"][str(frame)] = member["acceptable_sigma"]

        # without buckling
        else:
            result["acceptable_sigma_buckling"][str(frame)] = member["acceptable_sigma"]
            result["lamda"][str(frame)] = None # to avoid missing KeyError

        # lever_arm
        lever_arm = []
        for i in range(11):
            moment_h = sqrt(moment_y[i]**2+moment_z[i]**2)

            # to avoid division by zero
            if result["axial"][str(frame)][i] < 0.1:
                lv = moment_h / 0.1
            else:
                lv = moment_h / result["axial"][str(frame)][i]

            lv = abs(lv) # absolute highest value within member
            lever_arm.append(lv)

        result["lever_arm"][str(frame)] = lever_arm
        result["max_lever_arm"][str(frame)] = max(lever_arm)

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

        result["deflection"][str(frame)] = deflection

        fea[str(id)] = result

    feas[str(frame)] = fea

    text = "multiprocessing job: " + str(frame) + " done"
    print_data(text)

def start_job():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    members = scene["<Phaenotyp>"]["members"]
    frame = scene.frame_current

    # append task to mp
    # every calculation is one frame! (not every frame has a calculation)
    # every calculation can be redone at the frame
    fea_data = prepare_fea()
    #calculation.run_fea(fea, frame)
    # pass fea to job instead:
    job = multiprocessing.Process(target=run_fea, args=(feas, fea_data, members, frame,))
    fea_jobs.append(job)
    job.start()

def join_jobs():
    # wait for all jobs to be done
    for job in fea_jobs:
        job.join()

def interweave_results():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    members = scene["<Phaenotyp>"]["members"]

    # retrieve result and weave into data
    # retrieve result and weave into data
    for fea_id, fea in feas.items():
        for member_id, member in fea.items():
            for result_name, result in member.items():
                members[member_id][result_name][str(fea_id)] = result[str(fea_id)]

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
        if member["Di"][str(frame)] < 0.001:
            member["Di"][str(frame)] = 0.001
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

        faktor_d = sqrt(abs(faktor_a))
        member["Do"][str(frame)] = member["Do"][str(frame)]*faktor_d
        member["Di"][str(frame)] = member["Di"][str(frame)]*faktor_d

        # set miminum size of Do and Di to avoid division by zero
        Do_Di_ratio = member["Do"][str(frame)]/member["Di"][str(frame)]
        if member["Di"][str(frame)] < 0.001:
            member["Di"][str(frame)] = 0.001
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
