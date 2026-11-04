"""Focused checks for the Blender-side multiprocessing handoff."""
import ast
import os
import pickle
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ast.parse((ROOT / "calculation.py").read_text())
FUNCTIONS = {node.name: node for node in SOURCE.body if isinstance(node, ast.FunctionDef)}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = "/tmp"
        self.return_path = "/tmp/Phaenotyp-return_mp.p"
        self.export_path = "/tmp/Phaenotyp-export_mp.p"
        self.popups = []
        self.basics = SimpleNamespace(feas={"old": 1}, jobs=[[lambda: None]],
                                      popup=lambda **kwargs: self.popups.append(kwargs),
                                      log_exception=Mock())
        self.settings = SimpleNamespace(use_scipy=False, calculation_type="first_order_linear")
        class Scene(dict):
            pass
        scene = Scene({"<Phaenotyp>": {"scipy_available": True}})
        scene.phaenotyp = self.settings
        self.bpy = SimpleNamespace(data=SimpleNamespace(filepath="/tmp/test.blend"),
                                   path=SimpleNamespace(basename=os.path.basename),
                                   context=SimpleNamespace(scene=scene))
        self.process = Mock(returncode=0)
        self.process.communicate.return_value = (None, b"")
        self.popen = Mock(return_value=self.process)
        self.models = {"1": "model"}
        self.results = {"1": "calculated"}
        self.removed = []
        self.files = {}

        class MemoryFile:
            def __init__(inner, path, mode):
                inner.path, inner.mode = path, mode
                if "w" in mode:
                    self.files[path] = bytearray()
                inner.offset = 0

            def write(inner, data):
                self.files[inner.path].extend(data)

            def read(inner, size=-1):
                data = self.files[inner.path]
                result = bytes(data[inner.offset:] if size < 0 else data[inner.offset:inner.offset + size])
                inner.offset += len(result)
                return result

            def readline(inner):
                data = self.files[inner.path]
                end = data.find(b"\n", inner.offset)
                return inner.read(len(data) - inner.offset if end < 0 else end + 1 - inner.offset)

            def __enter__(inner):
                return inner

            def __exit__(inner, *args):
                pass

            def close(inner):
                pass

        self.files[self.return_path] = bytearray(pickle.dumps(self.results))
        paths = SimpleNamespace(dirname=os.path.dirname, basename=os.path.basename,
                                exists=lambda path: path in self.files)
        self.env = dict(__file__=str(ROOT / "calculation.py"), bpy=self.bpy, basics=self.basics, os=SimpleNamespace(path=paths,
                        remove=lambda path: (self.removed.append(path), self.files.pop(path, None)),
                        ), sys=SimpleNamespace(executable="python"), pickle=pickle,
                        Popen=self.popen, PIPE=-1, DEVNULL=-3,
                        open=MemoryFile)
        exec(compile(ast.Module(body=[FUNCTIONS["run_mp"]], type_ignores=[]),
                     str(ROOT / "calculation.py"), "exec"), self.env)

    def run_handoff(self):
        self.popen.side_effect = lambda *args, **kwargs: self.write_result_and_return()
        self.env["run_mp"](self.models)

    def write_result_and_return(self):
        if self.process.returncode == 0 and self.process.communicate.return_value[1] == b"":
            self.files[self.return_path] = bytearray(pickle.dumps(self.results))
        return self.process

    def test_unsaved_file_stops_before_export(self):
        self.bpy.data.filepath = ""
        self.env["run_mp"](self.models)
        self.assertFalse(self.popen.called)
        self.assertFalse(self.basics.jobs)
        self.assertEqual(self.basics.feas, {})
        self.assertIn("speichern", self.popups[0]["lines"][0])

    def test_success_uses_dense_solver_and_new_results(self):
        self.run_handoff()
        self.assertEqual(self.popen.call_args.args[0][3], "False")
        self.assertEqual(self.basics.feas, self.results)
        self.assertEqual(self.removed, [self.return_path])

    def test_worker_failure_discards_old_result(self):
        self.process.returncode = 1
        self.process.communicate.return_value = (None, b"worker failed")
        self.run_handoff()
        self.assertEqual(self.basics.feas, {})
        self.assertFalse(self.basics.jobs)
        self.assertTrue(self.popups)
        self.assertNotIn(self.return_path, self.files)

    def test_incomplete_result_is_rejected(self):
        self.results = {}
        self.run_handoff()
        self.assertEqual(self.basics.feas, {})
        self.assertFalse(self.basics.jobs)
        self.assertTrue(self.popups)


if __name__ == "__main__":
    unittest.main()
