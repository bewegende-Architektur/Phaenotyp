# coding-utf8
from multiprocessing import Manager, Value, cpu_count, Pool
from math import sqrt
from math import tanh

import sys
from time import time

# import python from parent directory like pointed out here:
# https://stackoverflow.com/questions/714063/importing-modules-from-parent-folder
import os
import sys
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from PyNite import FEModel3D

import pickle

def print_data(text):
    print("Phaenotyp |", text)

# get arguments
directory_blend = sys.argv[1]
path_import = directory_blend + "/Phaenotyp-export_mp.p"
scipy_available = sys.argv[2]

# start timer
start_time = time()

def import_trusses():
    # get trusses stored as dict with frame as key
    file = open(path_import, 'rb')
    imported_trusses = pickle.load(file)
    file.close()

    return imported_trusses

# run one single fea and save result into feas (multiprocessing manager dict)
def run_fea(scipy_available, feas, truss, frame):
    # the variables truss, and frame are passed to mp
    # this variables can not be returned with multiprocessing
    # instead of this a dict with multiprocessing.Manager is created
    # the dict feas stores one anlysis for each frame
    # the dict fea is created temporarily in run_fea and is wirrten to feas
    # analyze the model
    if scipy_available == "True":
        truss.analyze(check_statics=False, sparse=True)
    if scipy_available == "False":
        truss.analyze(check_statics=False, sparse=False)

    feas[str(frame)] = truss

    text = "multiprocessing job for frame " + str(frame) + " done"
    print_data(text)

def mp_pool():
    global scipy_available

    manager = Manager() # needed for mp
    feas = manager.dict() # is saving all calculations by frame

    cores = cpu_count()
    text = "rendering with " + str(cores) + " cores."
    print_data(text)

    pool = Pool(processes=cores)
    for frame, truss in imported_trusses.items():
        pool.apply_async(run_fea, args=(scipy_available, feas, truss, frame,))

    pool.close()
    pool.join()

    return feas

def export_trusses():
    # export back to blender
    path_export = directory_blend + "/Phaenotyp-return_mp.p"
    file = open(path_export, 'wb')
    pickle.dump(dict(feas), file) # use dict() to convert mp_dict to dict
    file.close()

if __name__ == "__main__":
    imported_trusses = import_trusses()
    feas = mp_pool()
    export_trusses()
    # give feedback to user
    end_time = time()
    elapsed_time = end_time - start_time
    text = "time elapsed: " + str(elapsed_time) + " s"
    print_data(text)

    # exit
    sys.exit()
