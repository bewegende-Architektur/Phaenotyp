import bpy
from math import sqrt, pi
from mathutils import Color, Vector
c = Color()

def create_supports(structure_obj, supports):
    mesh = bpy.data.meshes.new("<Phaenotyp>support")
    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("<Phaenotyp>")
    col.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    verts = []
    edges = []
    faces = []

    structure_obj_vertices = structure_obj.data.vertices
    len_verts = 0

    for id, support in supports.items():
        id = int(id)

        # transfer parameters
        loc_x = support[0]
        loc_y = support[1]
        loc_z = support[2]

        rot_x = support[3]
        rot_y = support[4]
        rot_z = support[5]

        x = structure_obj_vertices[id].co[0]
        y = structure_obj_vertices[id].co[1]
        z = structure_obj_vertices[id].co[2]

        # to set position
        offset = Vector((x, y, z))

        # pyramide floor
        v_0 = Vector((-0.1, 0.1,-0.1)) + offset
        v_1 = Vector(( 0.1, 0.1,-0.1)) + offset
        v_2 = Vector(( 0.1,-0.1,-0.1)) + offset
        v_3 = Vector((-0.1,-0.1,-0.1)) + offset
        v_4 = Vector(( 0.0, 0.0, 0.0)) + offset

        verts.append(v_0)
        verts.append(v_1)
        verts.append(v_2)
        verts.append(v_3)
        verts.append(v_4)

        edges.append([0+len_verts, 1+len_verts])
        edges.append([1+len_verts, 2+len_verts])
        edges.append([2+len_verts, 3+len_verts])
        edges.append([3+len_verts, 0+len_verts])

        edges.append([0+len_verts, 4+len_verts])
        edges.append([1+len_verts, 4+len_verts])
        edges.append([2+len_verts, 4+len_verts])
        edges.append([3+len_verts, 4+len_verts])

        # loc_x
        lx = 1 if loc_x == True else 0
        v_5 = Vector(( 0.0*lx, 0.0,-0.2*lx)) + offset
        v_6 = Vector(( 0.2*lx, 0.0,-0.2*lx)) + offset

        verts.append(v_5)
        verts.append(v_6)

        edges.append([5+len_verts, 6+len_verts])

        # loc_y
        ly = 1 if loc_y == True else 0
        v_7 = Vector(( 0.0, 0.0*ly,-0.2*ly)) + offset
        v_8 = Vector(( 0.0, 0.2*ly,-0.2*ly)) + offset

        verts.append(v_7)
        verts.append(v_8)

        edges.append([7+len_verts, 8+len_verts])

        # loc_z
        lz = 1 if loc_z == True else 0
        v_9 = Vector(( 0.0, 0.0,-0.2*lz)) + offset
        v_10 = Vector(( 0.0, 0.0,-0.4*lz)) + offset

        verts.append(v_9)
        verts.append(v_10)

        edges.append([9+len_verts, 10+len_verts])

        # rot_x
        rx = 1 if rot_x == True else 0
        v_11 = Vector(( 0.20*rx, 0.02*rx,-0.22*rx)) + offset
        v_12 = Vector(( 0.20*rx,-0.02*rx,-0.22*rx)) + offset
        v_13 = Vector(( 0.20*rx,-0.02*rx,-0.18*rx)) + offset
        v_14 = Vector(( 0.20*rx, 0.02*rx,-0.18*rx)) + offset

        verts.append(v_11)
        verts.append(v_12)
        verts.append(v_13)
        verts.append(v_14)

        edges.append([11+len_verts, 12+len_verts])
        edges.append([12+len_verts, 13+len_verts])
        edges.append([13+len_verts, 14+len_verts])
        edges.append([14+len_verts, 11+len_verts])

        # rot_y
        ry = 1 if rot_y == True else 0
        v_15 = Vector(( 0.02*ry, 0.20*ry,-0.22*ry)) + offset
        v_16 = Vector((-0.02*ry, 0.20*ry,-0.22*ry)) + offset
        v_17 = Vector((-0.02*ry, 0.20*ry,-0.18*ry)) + offset
        v_18 = Vector(( 0.02*ry, 0.20*ry,-0.18*ry)) + offset

        verts.append(v_15)
        verts.append(v_16)
        verts.append(v_17)
        verts.append(v_18)

        edges.append([15+len_verts, 16+len_verts])
        edges.append([16+len_verts, 17+len_verts])
        edges.append([17+len_verts, 18+len_verts])
        edges.append([18+len_verts, 15+len_verts])

        # rot_z
        rz = 1 if rot_z == True else 0
        v_19 = Vector(( 0.02*rz, 0.02*rz,-0.40*rz)) + offset
        v_20 = Vector((-0.02*rz, 0.02*rz,-0.40*rz)) + offset
        v_21 = Vector((-0.02*rz,-0.02*rz,-0.40*rz)) + offset
        v_22 = Vector(( 0.02*rz,-0.02*rz,-0.40*rz)) + offset

        verts.append(v_19)
        verts.append(v_20)
        verts.append(v_21)
        verts.append(v_22)

        edges.append([19+len_verts, 20+len_verts])
        edges.append([20+len_verts, 21+len_verts])
        edges.append([21+len_verts, 22+len_verts])
        edges.append([22+len_verts, 19+len_verts])

        len_verts += 23

    mesh.from_pydata(verts, edges, faces)

def create_members(structure_obj, members):
    # create mesh and object
    mesh = bpy.data.meshes.new("<Phaenotyp>member")
    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("<Phaenotyp>")
    col.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    frame = bpy.context.scene.frame_current

    verts = []
    edges = []
    faces = []

    structure_obj_vertices = structure_obj.data.vertices

    len_verts = 0

    for id, member in members.items():
        member["mesh_vertex_ids"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        id = int(id)

        vertex_0_id = member["vertex_0_id"]
        vertex_1_id = member["vertex_1_id"]

        vertex_0_co = structure_obj_vertices[vertex_0_id].co
        vertex_1_co = structure_obj_vertices[vertex_1_id].co

        # create vertices
        for i in range(11):
            pos = (vertex_0_co*(i) + vertex_1_co*(10-i))*0.1

            v = Vector(pos)
            verts.append(v)

            member["mesh_vertex_ids"][i] = len_verts+i

        # add edges
        edges.append([0 + len_verts, 1 + len_verts])
        edges.append([1 + len_verts, 2 + len_verts])
        edges.append([2 + len_verts, 3 + len_verts])
        edges.append([3 + len_verts, 4 + len_verts])
        edges.append([4 + len_verts, 5 + len_verts])
        edges.append([5 + len_verts, 6 + len_verts])
        edges.append([6 + len_verts, 7 + len_verts])
        edges.append([7 + len_verts, 8 + len_verts])
        edges.append([8 + len_verts, 9 + len_verts])
        edges.append([9 + len_verts, 10 + len_verts])

        # update counter
        len_verts += 11

    mesh.from_pydata(verts, edges, faces)

    # create modifiere if not existing
    modifier = obj.modifiers.get('<Phaenotyp>')
    if modifier:
        text = "existing modifier:" + str(modifiers)
    else:
        modifier_nodes = obj.modifiers.new(name="<Phaenotyp>", type='NODES')
        bpy.ops.node.new_geometry_node_group_assign()
        nodes = obj.modifiers['<Phaenotyp>'].node_group

        # set name to group
        if nodes.name == "<Phaenotyp>Nodes":
            node_group = bpy.data.node_groups['<Phaenotyp>Nodes']
        else:
            nodes.name = "<Phaenotyp>Nodes"
            node_group = bpy.data.node_groups['<Phaenotyp>Nodes']

        # mesh to curve
        node_group.nodes.new(type="GeometryNodeMeshToCurve")
        input = node_group.nodes['Mesh to Curve'].inputs['Mesh']
        output = node_group.nodes['Group Input'].outputs['Geometry']
        node_group.links.new(input, output)

        # curve to mesh
        node_group.nodes.new(type="GeometryNodeCurveToMesh")
        input = node_group.nodes['Mesh to Curve'].outputs['Curve']
        output = node_group.nodes['Curve to Mesh'].inputs['Curve']
        node_group.links.new(input, output)

        # profile to curve
        node_group.nodes.new(type="GeometryNodeCurvePrimitiveCircle")
        input = node_group.nodes['Curve to Mesh'].inputs['Profile Curve']
        output = node_group.nodes['Curve Circle'].outputs['Curve']
        node_group.links.new(input, output)

        # link to output
        input = node_group.nodes['Curve to Mesh'].outputs['Mesh']
        output = node_group.nodes['Group Output'].inputs['Geometry']
        node_group.links.new(input, output)


    # create vertex_group for radius
    # radius is automatically choosen by geometry nodes for radius-input
    bpy.ops.object.mode_set(mode = 'OBJECT')
    radius_group = obj.vertex_groups.get("radius")
    if not radius_group:
        radius_group = obj.vertex_groups.new(name="radius")

    # assign to group
    for id, member in members.items():
        id = str(id)
        vertex_ids = member["mesh_vertex_ids"]

        # copy Do and Di if not set by optimization
        # or the user changed the frame during optimization
        if str(frame) not in member["Do"]:
            member["Do"][str(frame)] = member["Do"]["first"]

        radius = member["Do"][str(frame)]*0.01
        radius_group.add(vertex_ids, radius, 'REPLACE')

    # create vertex_color
    attribute = obj.data.attributes.get("force")
    if attribute:
        text = "existing attribute:" + str(attribute)
    else:
        bpy.ops.geometry.color_attribute_add(name="force", domain='POINT', data_type='FLOAT_COLOR', color=(255, 0, 255, 1))

def update_members_pre():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]
    structure_obj_vertices = data["structure"]
    frame = bpy.context.scene.frame_current
    mesh_for_viz = bpy.data.objects["<Phaenotyp>member"] # <------------------------- oder in data speichern?
    vertices = mesh_for_viz.data.vertices

    radius_group = mesh_for_viz.vertex_groups.get("radius")
    attribute = mesh_for_viz.data.attributes.get("force")

    for id, member in members.items():
        id = int(id)

        # copy properties if not set by optimization
        # or the user changed the frame during optimization
        if str(frame) not in member["Do"]:
            member["Do"][str(frame)] = member["Do"]["first"]
            member["Di"][str(frame)] = member["Di"]["first"]
        if str(frame) not in member["ir"]:
            member["Iy"][str(frame)] = member["Iy"]["first"]
            member["Iz"][str(frame)] = member["Iz"]["first"]
            member["J"][str(frame)] = member["J"]["first"]
            member["A"][str(frame)] = member["A"]["first"]
            member["kg"][str(frame)] = member["kg"]["first"]
            member["ir"][str(frame)] = member["ir"]["first"]

        # update material (like updated when passed from gui in material.py)
        member["Iy"][str(frame)] = pi * (member["Do"][str(frame)]**4 - member["Di"][str(frame)]**4)/64
        member["Iz"][str(frame)] = member["Iy"][str(frame)]
        member["J"][str(frame)]  = pi * (member["Do"][str(frame)]**4 - member["Di"][str(frame)]**4)/(32)
        member["A"][str(frame)]  = ((pi * (member["Do"][str(frame)]*0.5)**2) - (pi * (member["Di"][str(frame)]*0.5)**2))
        member["kg"][str(frame)] =  member["A"][str(frame)]*member["d"] * 0.1
        member["ir"][str(frame)] = sqrt(member["Iy"][str(frame)]/member["A"][str(frame)])

def update_members_post():
    scene = bpy.context.scene
    phaenotyp = scene.phaenotyp
    data = scene["<Phaenotyp>"]
    members = data["members"]
    structure_obj_vertices = data["structure"]
    frame = bpy.context.scene.frame_current
    mesh_for_viz = bpy.data.objects["<Phaenotyp>member"] # <------------------------- oder in data speichern?
    vertices = mesh_for_viz.data.vertices

    radius_group = mesh_for_viz.vertex_groups.get("radius")
    attribute = mesh_for_viz.data.attributes.get("force")

    for id, member in members.items():
        id = int(id)

        mesh_vertex_ids = member["mesh_vertex_ids"]

        # update radius
        vertex_ids = member["mesh_vertex_ids"]
        radius = member["Do"][str(frame)]*0.01
        radius_group.add(vertex_ids, radius, 'REPLACE')

        # get forcetyp and force
        result = member[phaenotyp.forces]

        # move vertices and apply color
        for i in range(11):
            position = member["deflection"][str(frame)][i]
            f = phaenotyp.viz_deflection * 0.01
            x = position[0]*(1-f) + member["initial_positions"][str(frame)][10-i][0]*f
            y = position[1]*(1-f) + member["initial_positions"][str(frame)][10-i][1]*f
            z = position[2]*(1-f) + member["initial_positions"][str(frame)][10-i][2]*f
            vertices[mesh_vertex_ids[i]].co = (x,y,z)

            if result[str(frame)][i] > 0:
                h = 0
            else:
                h = 0.666

            # define s
            s = 1 * abs(result[str(frame)][i]) * phaenotyp.viz_scale * 0.01

            # define v
            if member["overstress"][str(frame)] == True:
                v = 0.1
            else:
                v = 1.0

            c.hsv = h,s,v
            attribute.data[mesh_vertex_ids[i]].color = [c.r, c.g, c.b, 1.0]

def create_loads(structure_obj, loads_v, loads_e, loads_f):
    for id, load in loads_v.items():
        id = int(id)
        x = structure_obj.data.vertices[id].co[0] # text pos x
        y = structure_obj.data.vertices[id].co[1] # text pos y
        z = structure_obj.data.vertices[id].co[2] # text pos z

        name = "<Phaenotyp>support_" + str(id)
        font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>load_text")

        text = "" + "\n"

        text = text + "type: vertices\n"
        text = text + "x: " + str(load[0]) + "\n"
        text = text + "y: " + str(load[1]) + "\n"
        text = text + "z: " + str(load[2]) + "\n"

        font_curve.body = text
        obj = bpy.data.objects.new(name="<Phaenotyp>load", object_data=font_curve)

        # set scale and position
        obj.location = x, y, z
        obj.scale = 0.1, 0.1, 0.1

        # link object to collection
        bpy.data.collections["<Phaenotyp>"].objects.link(obj)

    for id, load in loads_e.items():
        id = int(id)
        vertex_0_id = structure_obj.data.edges[id].vertices[0]
        vertex_1_id = structure_obj.data.edges[id].vertices[1]

        vertex_0 = structure_obj.data.vertices[vertex_0_id]
        vertex_1 = structure_obj.data.vertices[vertex_1_id]

        mid = (vertex_0.co + vertex_1.co) / 2

        x = mid[0] # text pos x
        y = mid[1] # text pos y
        z = mid[2] # text pos z

        name = "<Phaenotyp>support_" + str(id)
        font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>load_text")

        text = "" + "\n"

        text = text + "type: edges\n"
        text = text + "x: " + str(load[0]) + "\n"
        text = text + "y: " + str(load[1]) + "\n"
        text = text + "z: " + str(load[2]) + "\n"

        font_curve.body = text
        obj = bpy.data.objects.new(name="<Phaenotyp>load", object_data=font_curve)

        # set scale and position
        obj.location = x, y, z
        obj.scale = 0.1, 0.1, 0.1

        # link object to collection
        bpy.data.collections["<Phaenotyp>"].objects.link(obj)

    for id, load in loads_f.items():
        id = int(id)

        face = structure_obj.data.polygons[id]

        x = face.center[0] # text pos x
        y = face.center[1] # text pos y
        z = face.center[2] # text pos z

        name = "<Phaenotyp>support_" + str(id)
        font_curve = bpy.data.curves.new(type="FONT", name="<Phaenotyp>load_text")

        text = "" + "\n"

        text = text + "type: faces\n"
        text = text + "n: " + str(load[0]) + "\n"
        text = text + "p: " + str(load[1]) + "\n"
        text = text + "z: " + str(load[2]) + "\n"

        font_curve.body = text
        obj = bpy.data.objects.new(name="<Phaenotyp>load", object_data=font_curve)

        # set scale and position
        obj.location = x, y, z
        obj.scale = 0.1, 0.1, 0.1

        # link object to collection
        bpy.data.collections["<Phaenotyp>"].objects.link(obj)
