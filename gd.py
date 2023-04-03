import bpy
from phaenotyp import operators, geometry, calculation, ga
import numpy as np

# Funktionen für gradient decent
def create_individual(keys, frame):
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    members = data["members"]
    shape_keys = obj.data.shape_keys.key_blocks
    frame = bpy.context.scene.frame_current
    phaenotyp = scene.phaenotyp

    environment = data["environment"]
    individuals = data["individuals"]

    bpy.context.scene.frame_current = frame

    # Das Chromosome ist eine Liste der Shapekeys
    ga.create_indivdual(keys, None, None)


    # for PyNite
    if phaenotyp.calculation_type != "force_distribution":
        prepare_fea = calculation.prepare_fea_pn
        run_st = calculation.run_st_pn
        interweave_results = calculation.interweave_results_pn

    # for force distribuion
    else:
        prepare_fea = calculation.prepare_fea_fd
        run_st = calculation.run_st_fd
        interweave_results = calculation.interweave_results_fd

    # Volumen as Fitness erhalten
    # Später können wir hier eine neue Funktion bauen
    # Die Funktion von Ga fnktioniert hier nicht,
    # da wir die Fitness mit Frame 0 errechnen
    geometry.update_members_pre()
    truss = prepare_fea()
    fea = run_st(truss, frame)
    interweave_results(fea, members)
    geometry.update_members_post()
    fitness = data["frames"][str(frame)]["kg"] # hier nur für kg, Änderung auf alle

    gd = individuals[str(frame)]

    return gd, fitness

def start_gd():
    scene = bpy.context.scene
    data = scene["<Phaenotyp>"]
    obj = data["structure"]
    members = data["members"]
    shape_keys = obj.data.shape_keys.key_blocks
    frame = bpy.context.scene.frame_current
    phaenotyp = scene.phaenotyp

    environment = data["environment"]
    individuals = data["individuals"]

    # Basis erstellen
    # Das erst Argument sind die Shapekeys
    # Das zweite Argument ist der Frame (Zeitleiste)
    # Jeder Frame ist eine eigene Berechnung
    # Die Nummer des Frame ist gleich die Nummer des Individuums

    # get data from gui

    # Hyperparamter:
    # Schrittlänge nur zur Neigungsbestimmung
    delta = phaenotyp.gd_delta
    # Lernrate, kann auch wählbar sein
    learning_rate = phaenotyp.gd_learning_rate
    # Abbruchkriterium auch als Eingabe möglich machen,
    abort = phaenotyp.gd_abort
    # maximal number if iteration,um Endlosschleifen zu vermeiden
    maxiteration = phaenotyp.gd_max_iteration

    # Ausgangspunkt
    chromosome_start = [0.5]
    neigung = [0]
    for i in range(len(shape_keys)-2):
        chromosome_start.append(0.5)
        neigung.append(0)
    #chromosome_start = [0.5, 0.5, 0.5] # kann auch mit GA ermittelt werden
    print ("Startpunkt: ", chromosome_start)
    chromosome_aktuell=chromosome_start
    frame_number=0
    print ()

    j=0
    while  j < maxiteration:
        frame_number+=1
        print ("Frame-number: ", frame_number)
        gd, fitness = create_individual(chromosome_aktuell,frame_number)
        print("gd", gd["name"], "mit fitness:", fitness)
        fitness_0 = fitness

        # Varianten von den Keys erstellen
        # dieser Teil könnte mp sein
        for i in range(len(shape_keys)-1):
            # Frame addieren
            bpy.context.scene.frame_current += 1
            frame = bpy.context.scene.frame_current
            chromosome = chromosome_aktuell.copy()
            print ("frame =",frame, "i=", i)
            frame_number+=1
            print ("Frame-number: ", frame_number)
            chromosome[i] += delta
            gd, fitness = create_individual(chromosome, frame)
            print("Gradient descent", gd["name"], "mit fitness:", fitness)
            # Neigung
            neigung[i]=(fitness-fitness_0)/delta
            print ("Neigung shapekey ",i,"=", neigung[i])
            # neuer Punkt
            chromosome_aktuell[i]=chromosome_aktuell[i]-neigung[i]*learning_rate
            if chromosome_aktuell[i]<0:
                chromosome_aktuell[i]=0
                neigung[i]=0
            if chromosome_aktuell[i]>1:
                chromosome_aktuell[i]=1
                neigung[i]=0
            print ("Neigung shapekey_",i,"=", neigung[i])
        print ("Neuer chromosome:",chromosome_aktuell)
        vektor = (np.linalg.norm(neigung))*learning_rate
        print("vektor: ",vektor)
        j+=1
        print()
        print()
        if vektor < abort:
            break
    print()
    print()
