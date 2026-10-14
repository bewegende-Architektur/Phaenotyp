"""Run with: python -m unittest discover -s tests -p 'test_deformation.py'."""
import math
from pathlib import Path
from types import SimpleNamespace
import textwrap
import unittest

import numpy as np
from Pynite import FEModel3D

ROOT = Path(__file__).resolve().parents[1]


class DeformationTests(unittest.TestCase):
    def setUp(self):
        self.model = FEModel3D()
        self.model.add_material('acryl', 310, 115, 310 / 230 - 1, 1.19)
        self.model.add_section('section', 1, .1, .1, .2)
        for name, xyz in [('a', (0, 0, 0)), ('b', (100, 20, 30)), ('c', (180, 80, 10))]:
            self.model.add_node(name, *xyz)
        self.model.def_support('a', True, True, True, True, True, True)
        for name, i, j in [('ab', 'a', 'b'), ('bc', 'b', 'c')]:
            self.model.add_member(name, i, j, 'acryl', 'section', rotation=30)
        self.model.add_node_load('c', 'FY', -.0001)
        self.model.analyze_linear(sparse=False)

    def stored_member(self, name, ui_scale):
        # Execute the production extraction block without Blender imports.
        source = (ROOT / 'calculation.py').read_text()
        block = source[source.index('\t\t# deflection\n'):source.index('\n\tnodes = model.nodes', source.index('\t\t# deflection\n'))]
        result = {'deflection': {}}
        m = self.model.members[name]
        env = dict(array=np.array, empty=np.empty, append=np.append,
                   phaenotyp=SimpleNamespace(viz_deflection_scale=ui_scale),
                   model_member=m, member=result, L=m.L(), T=m.T(), frame='1')
        exec(textwrap.dedent(block), env)
        return result

    def test_physical_results_do_not_depend_on_ui_scale(self):
        np.testing.assert_allclose(self.stored_member('ab', 1)['deflection']['1'],
                                   self.stored_member('ab', 20)['deflection']['1'])
        self.assertEqual(self.stored_member('ab', 20)['deflection_scale']['1'], 1)

    def test_connected_ends_follow_shared_node_even_if_member_inactive(self):
        for inactive in [False, True]:
            self.model.members['bc'].active['Combo 1'] = not inactive
            ab = self.stored_member('ab', 1)['deflection']['1']
            bc = self.stored_member('bc', 10)['deflection']['1']
            np.testing.assert_allclose(ab[10], bc[0], atol=1e-12)
            b = self.model.nodes['b']
            expected = np.array([b.X + b.DX['Combo 1'], b.Z + b.DZ['Combo 1'], b.Y + b.DY['Combo 1']]) * .01
            np.testing.assert_allclose(ab[10], expected)

    def test_inactive_member_is_straight_between_displaced_nodes(self):
        self.model.members['bc'].active['Combo 1'] = False
        points = np.array(self.stored_member('bc', 1)['deflection']['1'])
        np.testing.assert_allclose(points, np.linspace(points[0], points[-1], 11))

    def test_pdelta_correction_is_distributed_over_entire_curve(self):
        self.model.add_node_load('c', 'FX', -.001)
        self.model.analyze_PDelta(sparse=False)
        for name, m in self.model.members.items():
            origin = np.array([m.i_node.X, m.i_node.Y, m.i_node.Z])
            rotation = m.T()[:3, :3]
            raw = []
            for i in range(11):
                x = m.L() * i / 10
                local = np.array([x + m.deflection('dx', x),
                                  m.deflection('dy', x), m.deflection('dz', x)])
                raw.append((origin + local @ rotation)[[0, 2, 1]] * .01)
            raw = np.array(raw)
            points = np.array(self.stored_member(name, 1)['deflection']['1'])
            correction = points - raw
            self.assertGreater(np.linalg.norm(correction[-1]), 1e-4)
            # Every interval receives the same chord correction. Snapping only
            # the endpoint fails this check and introduces a last-segment kink.
            np.testing.assert_allclose(np.diff(correction, axis=0),
                                       np.tile((correction[-1] - correction[0]) / 10, (10, 1)), atol=1e-12)
        np.testing.assert_allclose(self.stored_member('ab', 1)['deflection']['1'][-1],
                                   self.stored_member('bc', 1)['deflection']['1'][0])

    def test_quad_display_current_and_legacy_scales(self):
        source = (ROOT / 'geometry.py').read_text()
        start = source.index('\t\t\t\tinitial = quad["initial_positions"]')
        end = source.index('\n\t\t\t\t\n', start)
        block = textwrap.dedent(source[start:end])
        initial = np.array([1., 2., 3.])
        displacement = np.array([.01, -.02, .03])
        for legacy in [False, True]:
            quad = {'initial_positions': {'1': [initial]}}
            if not legacy:
                quad['deflection_scale'] = {'1': 1.}
            for scale, blend in [(1, 0), (10, 0), (1, .5), (10, 1)]:
                env = dict(quad=quad, frame=1, i=0, position=initial + displacement * (10 if legacy else 1),
                           viz_deflection_scale=scale, viz_deflection=blend)
                exec(block, env)
                np.testing.assert_allclose([env[k] for k in ('x', 'y', 'z')],
                                           initial + displacement * scale * (1 - blend))

    def test_quad_extraction_converts_cm_to_m(self):
        source = (ROOT / 'calculation.py').read_text()
        start = source.index('\t\t# get deflection\n', source.index('\n\tnodes = model.nodes'))
        end = source.index('\n\t\t# get average lengthes', start)
        quad = {'vertices_ids_structure': ['b'] * 4, 'initial_positions': {'1': [[1, .3, .2]] * 4}}
        env = dict(quad=quad, nodes=self.model.nodes, frame='1')
        exec(textwrap.dedent(source[start:end]), env)
        b = self.model.nodes['b']
        expected = np.array([1, .3, .2]) + np.array([b.DX['Combo 1'], b.DZ['Combo 1'], b.DY['Combo 1']]) * .01
        np.testing.assert_allclose(env['deflection'], [expected] * 4)


if __name__ == '__main__':
    unittest.main()
