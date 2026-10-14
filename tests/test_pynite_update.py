"""Compatibility checks for the vendored PyNite release and Phaenotyp APIs."""
import importlib.util
import pickle
from pathlib import Path
import textwrap
import unittest
import numpy as np
import Pynite
from Pynite import FEModel3D
from Pynite.Section import Section
import material


class PyniteUpdateTests(unittest.TestCase):
    def beam(self):
        m = FEModel3D()
        for mat in material.library:
            m.add_material(mat[0], mat[2], mat[3], None, mat[4])
        props = {'material_name': 'custom', 'E': 310, 'G': 115, 'rho': 1.19}
        key = material.ensure_pynite_member_material(m, props)
        m.sections['s'] = Section(m, 's', A=1, Iy=.1, Iz=.1, J=.2)
        m.add_node('a', 0, 0, 0)
        m.add_node('b', 100, 0, 0)
        m.def_support('a', True, True, True, True, True, True)
        m.add_member('ab', 'a', 'b', key, 's', 0, tension_only=False, comp_only=False)
        m.add_node_load('b', 'FY', -.0001)
        return m

    def test_version_and_analytical_cantilever(self):
        self.assertEqual(Pynite.__version__, '3.2.0')
        for method in ['analyze_linear', 'analyze', 'analyze_PDelta']:
            m = self.beam()
            getattr(m, method)(sparse=False)
            self.assertAlmostEqual(m.nodes['b'].DY['Combo 1'], -.0001 * 100**3 / (3 * 310 * .1))
            self.assertAlmostEqual(m.nodes['a'].RxnFY['Combo 1'], .0001)
            b = m.members['ab']
            for method, args in [('axial', (50,)), ('moment', ('Mz', 50)),
                                 ('shear', ('Fy', 50)), ('torque', (50,)),
                                 ('deflection', ('dy', 50))]:
                self.assertTrue(np.isfinite(getattr(b, method)(*args)))
            # Multiprocessing communicates models via pickle.
            restored = pickle.loads(pickle.dumps({'1': m}))['1']
            self.assertAlmostEqual(restored.nodes['b'].DY['Combo 1'], m.nodes['b'].DY['Combo 1'])

    def test_quad_pressure_equilibrium_and_result_api(self):
        m = FEModel3D()
        m.add_material('a', 310, 115, .35, 1.19)
        for name, xyz in [('a', (0, 0, 0)), ('b', (100, 0, 0)),
                          ('c', (100, 100, 0)), ('d', (0, 100, 0))]:
            m.add_node(name, *xyz)
            m.def_support(name, True, True, True, True, True, True)
        m.add_quad('q', 'a', 'b', 'c', 'd', 1, 'a', kx_mod=1., ky_mod=1.)
        m.add_quad_surface_pressure('q', -.0001)
        m.analyze_linear(sparse=False)
        self.assertAlmostEqual(abs(sum(n.RxnFZ['Combo 1'] for n in m.nodes.values())), 1.)
        for method in ['shear', 'moment', 'membrane']:
            result = getattr(m.quads['q'], method)()
            self.assertTrue(np.isfinite(result).all())
            self.assertEqual(result.shape, (2, 1) if method == 'shear' else (3, 1))
        # Execute Phaenotyp's scalar result extraction under current NumPy.
        source = (Path(__file__).resolve().parents[1] / 'calculation.py').read_text()
        start = source.index('\t\t# from PyNite\n', source.index('\n\tnodes = model.nodes'))
        end = source.index('\n\t\t# get deflection', start)
        env = {key: getattr(m.quads['q'], key)() for key in ['shear', 'moment', 'membrane']}
        exec(textwrap.dedent(source[start:end]), env)
        self.assertTrue(all(isinstance(env[k], float) for k in ['Qx', 'Qy', 'Mx', 'My', 'Mxy', 'Sx', 'Sy', 'Txy']))


    @unittest.skipUnless(importlib.util.find_spec('scipy'), 'SciPy is optional in Blender')
    def test_sparse_and_dense_agree(self):
        for method in ['analyze_linear', 'analyze', 'analyze_PDelta']:
            dense, sparse = self.beam(), self.beam()
            getattr(dense, method)(sparse=False)
            getattr(sparse, method)(sparse=True)
            self.assertAlmostEqual(dense.nodes['b'].DY['Combo 1'], sparse.nodes['b'].DY['Combo 1'])


if __name__ == '__main__':
    unittest.main()
