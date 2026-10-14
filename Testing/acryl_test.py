import bpy
from phaenotyp import material

# Geometrie: Skalierungsfaktoren der Ebenen (bei Ausgangsgröße 1 m).
ebene_0 = 0.30
ebene_1 = 0.25
ebene_2 = 0.15
ebene_3 = 0.15

# Rohrmaße in cm, entsprechend den Phänotyp-Eingabefeldern.
diamter_mid = 1.2
wallthickness_mid = 0.1
diamter_rest = 0.5
wallthickness_rest = 0.1

# Kraft in kN pro Punkt. Positiv wirkt in +Z; für Gewicht nach unten
# hier ein negatives Vorzeichen verwenden.
point_load_z = 0.005 / 4

support_sides = [0, 1, 2]
support_mid = [12]
point_loads = [9, 10, 11, 15]
pipes_mid = [21, 22, 23]
structure_name = "Basis"

def select_elements(structure, indices, selection_type):
    """Auswahl vollständig ersetzen, damit keine alten Lasten mitgesetzt werden."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    structure.select_set(True)
    bpy.context.view_layer.objects.active = structure
    bpy.context.tool_settings.mesh_select_mode = (
        selection_type == 'VERT', selection_type == 'EDGE', False
    )
    for elements in (structure.data.vertices, structure.data.edges,
                     structure.data.polygons):
        for element in elements:
            element.select = False
    elements = (structure.data.vertices if selection_type == 'VERT'
                else structure.data.edges)
    for index in indices:
        elements[index].select = True
    bpy.ops.object.mode_set(mode='EDIT')


def set_pipe_section(settings, diameter, thickness, acrylic):
    """Materialdaten wie im Panel setzen, ohne einen UI-Neuaufbau abzuwarten."""
    settings.profile_type = 'round_hollow'
    settings.material = 'acrylic_PMMA'
    settings.height = diameter
    settings.width = diameter
    settings.wall_thickness = thickness
    material.current.clear()
    material.current.update(dict(zip(
        ('material_name', 'E', 'G', 'rho', 'acceptable_sigma',
         'acceptable_shear', 'acceptable_torsion', 'acceptable_sigmav',
         'knick_model'),
        (acrylic[0], *acrylic[2:]),
    )))
    material.current.update(
        profile_type=settings.profile_type, height=settings.height,
        width=settings.height, wall_thickness=settings.wall_thickness,
        profile=None, angle=settings.member_angle,
    )
    material.update()


def main():
    scene = bpy.context.scene
    if not hasattr(scene, 'phaenotyp'):
        raise RuntimeError('Bitte zuerst das Phänotyp-Add-on aktivieren.')
    obj = bpy.data.objects
    required = [structure_name, 'Ebene_0', 'Ebene_1', 'Ebene_2', 'Ebene_3']
    missing = [name for name in required if name not in scene.objects]
    if missing:
        raise RuntimeError('Fehlende Objekte: ' + ', '.join(missing))
    structure = obj[structure_name]
    if structure.type != 'MESH':
        raise RuntimeError('Basis muss ein Mesh sein.')
    for indices, elements in (
        (support_sides + support_mid + point_loads, structure.data.vertices),
        (pipes_mid, structure.data.edges),
    ):
        if any(index < 0 or index >= len(elements) for index in indices):
            raise RuntimeError('Vertex-/Edge-Indizes passen nicht zum Basis-Mesh.')
    for diameter, thickness in ((diamter_mid, wallthickness_mid),
                                (diamter_rest, wallthickness_rest)):
        if not (0.1 <= diameter <= 100 and 0.1 <= thickness <= 50
                and 2 * thickness < diameter):
            raise ValueError('Ungültige Rohrmaße in cm: Durchmesser/Wandstärke.')
    acrylic = next((entry for entry in material.library
                    if entry[0] == 'acrylic_PMMA'), None)
    if acrylic is None:
        raise RuntimeError('Das Add-on benötigt das Material acrylic_PMMA.')
    area = next((area for area in bpy.context.screen.areas
                 if area.type == 'VIEW_3D'), None) if bpy.context.screen else None
    if area is None:
        raise RuntimeError('Für die Phänotyp-Operatoren muss eine 3D-Ansicht offen sein.')
    region = next(region for region in area.regions if region.type == 'WINDOW')

    # set_structure greift auf space_data.shading zu: 3D-Kontext bereitstellen.
    with bpy.context.temp_override(area=area, region=region):
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.wm.reset()
        for name, scale in zip(required[1:],
                               (ebene_0, ebene_1, ebene_2, ebene_3)):
            obj[name].scale = (scale, scale, scale)
        bpy.context.view_layer.update()
        select_elements(structure, [], 'VERT')
        bpy.ops.wm.set_structure()
        if scene['<Phaenotyp>'].get('structure') != structure:
            raise RuntimeError('Basis wurde nicht übernommen; Mesh im Panel prüfen.')

        settings = scene.phaenotyp
        settings.calculation_type = 'second_order'
        settings.type_of_joints = 'fixed_joints'
        for indices, rotations in ((support_sides, False), (support_mid, True)):
            settings.loc_x = settings.loc_y = settings.loc_z = True
            settings.rot_x = settings.rot_y = settings.rot_z = rotations
            select_elements(structure, indices, 'VERT')
            bpy.ops.wm.set_support()

        settings.member_type = 'full'
        settings.member_orientation = 'z_up'
        settings.member_angle = 0
        settings.buckling_resolution = 1
        set_pipe_section(settings, diamter_rest, wallthickness_rest, acrylic)
        select_elements(structure, range(len(structure.data.edges)), 'EDGE')
        bpy.ops.wm.set_member()
        set_pipe_section(settings, diamter_mid, wallthickness_mid, acrylic)
        select_elements(structure, pipes_mid, 'EDGE')
        bpy.ops.wm.set_member()

        settings.load_type = 'vertices'
        settings.load_FX = settings.load_FY = 0
        settings.load_FZ = point_load_z
        settings.load_MX = settings.load_MY = settings.load_MZ = 0
        select_elements(structure, point_loads, 'VERT')
        bpy.ops.wm.set_load()
        settings.mode = 'animation'
        bpy.ops.object.mode_set(mode='OBJECT')
    print('Acryl-Test eingerichtet. Animation im Phänotyp-Panel starten.')


if __name__ == '__main__':
    main()
