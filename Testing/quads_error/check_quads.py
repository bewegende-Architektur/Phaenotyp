"""Run the quad regression in Blender 5.2 without changing the source blend file.

Usage: python3 Testing/quads_error/check_quads.py [path-to-blender]
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

if "bpy" not in sys.modules:
    import shutil
    import subprocess
    import tempfile

    blender = sys.argv[1] if len(sys.argv) > 1 else shutil.which("blender")
    if not blender:
        raise SystemExit("Blender executable not found")
    with tempfile.TemporaryDirectory(prefix="phaenotyp-quads-") as directory:
        blend = Path(directory) / "test_quads.blend"
        shutil.copy2(HERE / "test_quads.blend", blend)
        subprocess.run(
            [blender, "--factory-startup", "-b", str(blend), "--python", str(__file__)],
            check=True,
        )
else:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "phaenotyp", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    phaenotyp = importlib.util.module_from_spec(spec)
    sys.modules["phaenotyp"] = phaenotyp
    spec.loader.exec_module(phaenotyp)
    phaenotyp.register()

    import bpy
    from phaenotyp import basics, calculation, geometry

    scene = bpy.context.scene
    frame = scene.frame_current
    data = scene["<Phaenotyp>"]
    basics.models = {}
    basics.feas = {}
    basics.popup = lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError(f"Calculation failed: {kwargs}")
    )

    calculation.prepare_fea_pn(frame)
    assert set(basics.models) == {str(frame)}
    calculation.run_mp(basics.models)
    assert set(basics.feas) == {str(frame)}
    calculation.interweave_results_pn(frame)
    geometry.update_geometry_post()

    assert data["done"][str(frame)]
    assert len(data["quads"]) == 64
    for quad in data["quads"].values():
        assert quad["length_x"][str(frame)] > 0
        assert quad["length_y"][str(frame)] > 0
    print("Quad regression passed: 64 quads calculated and results stored")
