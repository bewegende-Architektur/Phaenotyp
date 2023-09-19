		for id in quads:
			quad = quads[id]

			# read results from PyNite
			result = model.Quads[id]

			# only take highest value to zero
			shear = result.shear()
			moment = result.moment()
			membrane = result.membrane()

            # from PyNite
			Qx = float(shear[0])
			Qy = float(shear[1])

			Mx = float(moment[0])
			My = float(moment[1])
			Mxy = float(moment[2])

			Sx = float(membrane[0])
			Sy = float(membrane[1])
			Txy = float(membrane[2])

			# get deflection
			node_ids = quad["vertices_ids_structure"]
			deflection = []
			for i in range(4):
				# deflection only
				x = nodes[str(node_ids[i])].DX["Combo 1"]*0.1
				y = nodes[str(node_ids[i])].DY["Combo 1"]*0.1
				z = nodes[str(node_ids[i])].DZ["Combo 1"]*0.1

				# add deflection to initial position
				initial = quad["initial_positions"][frame][i]
				x += initial[0]
				y += initial[1]
				z += initial[2]

				deflection.append([x,y,z])

			# get average lengthes to calculate force by unit
			initial = quad["initial_positions"][frame]
			v_0 = array(initial[0])
			v_1 = array(initial[1])
			v_2 = array(initial[2])
			v_3 = array(initial[3])

			x_0 = v_1 - v_0 # first edge x
			x_1 = v_3 - v_2 # second edge x
			y_0 = v_2 - v_1 # first edge y
			y_1 = v_3 - v_0 # second edge y

			# as descripted in quad example
			length_x = (linalg.norm(x_0) + linalg.norm(x_1)) * 0.5 * 100 # to convert into cm
			length_y = (linalg.norm(y_0) + linalg.norm(y_1)) * 0.5 * 100 # to convert into cm

			# moment per unit
			shear_x = Qx/(length_x/2)
			shear_y = Qy/(length_y/2)

			moment_x = Mx/(length_x/2)
			moment_y = My/(length_y/2)
			moment_xy = Mxy/(length_y/2) #???

			membrane_x = Sx/(length_x/2)
			membrane_y = Sy/(length_y/2)
			membrane_xy = Txy/(length_y/2) #???

            # shorten and accessing once
            # bei Erstellung berechnen!
            # >>>>>
            A = quad["A"][frame]
            A = thickness * 100 # Dicke x 1 m in cm
            J = (100 * thickness)**3 / 12
            # <<<<<

            # buckling
            ir = sqrt(J/A) # in cm
            # modulus from the moments of area
            Wy = J / (thickness/2)

            moment_h = sqrt(moment_x**2 + moment_y**2)
            if membrane_x > 0:
                s = membrane_x/A + moment_h/Wy
            else:
                s = membrane_x/A - moment_h/Wy

            long_stress = s

            shear_h = sqrt(shear_x**2 + shear_y**2)
            tau_shear = 1.5 * s_h/A # for quads
            sigmav = sqrt(long_stress**2 + 3*tau_shear**2)

            overstress = False

            # check overstress and add 1.05 savety factor
            safety_factor = 1.05
            if abs(tau_shear) > safety_factor*quad["acceptable_shear"]:
                overstress = True

            if abs(quad["sigmav"][frame]) > safety_factor*quad["acceptable_sigmav"]:
                quad["overstress"][frame] = True

            # buckling
            if membrane_x < 0: # nur für Druckstäbe, axial kann nicht flippen?
                quad["lamda"][frame] = length_x*0.5/ir # für eingespannte Stäbe ist die Knicklänge 0.5 der Stablänge L, Stablänge muss in cm sein !
                if quad["lamda"][frame] > 20: # für lamda < 20 (kurze Träger) gelten die default-Werte)
                    kn = quad["knick_model"]
                    function_to_run = poly1d(polyfit(material.kn_lamda, kn, 6))
                    quad["acceptable_sigma_buckling"][frame] = function_to_run(quad["lamda"][frame])
                    if quad["lamda"][frame] > 250: # Schlankheit zu schlank
                        quad["acceptable_sigma_buckling"][frame] = function_to_run(250)
                        overstress = True
                    if safety_factor*abs(quad["acceptable_sigma_buckling"][frame]) > abs(sigma): # Sigma
                        overstress = True

                else:
                    quad["acceptable_sigma_buckling"][frame] = quad["acceptable_sigma"]

            # without buckling
            else:
                quad["acceptable_sigma_buckling"][frame] = quad["acceptable_sigma"]
                quad["lamda"][frame] = None # to avoid missing KeyError


            if abs(sigma) > safety_factor*quad["acceptable_sigma"]:
                overstress = True

            # Ausnutzungsgrad
            utilization = abs("long_stress" / quad["acceptable_sigma_buckling"][frame])

            # Einführung in die Technische Mechanik - Festigkeitslehre, H.Balke, Springer 2010
            # Berechnung der strain_energy für Normalkraft
            normalkraft_energie = (axial[i]**2)*(length_x)/(2*quad["E"]*A)

            # Berechnung der strain_energy für Moment
            moment_hq = moment_x**2+moment_y**2
            moment_energie = (moment_hq * length_x) / (quad["E"] * quad["Wy"][frame] * Do)

            # Summe von Normalkraft und Moment-Verzerrunsenergie
            strain_energy = ne + me

            # save to dict
			quad["shear_x"][frame] = shear_x
			quad["shear_y"][frame] = shear_y

			quad["moment_x"][frame] = moment_x
			quad["moment_y"][frame] = moment_y
			quad["moment_xy"][frame] = moment_xy

			quad["membrane_x"][frame] = membrane_x
			quad["membrane_y"][frame] = membrane_y
			quad["membrane_xy"][frame] = membrane_xy

			quad["length_x"][frame] = length_x
			quad["length_y"][frame] = length_y

			quad["deflection"][frame] = deflection

            quad["ir"][frame] = ir
            quad["A"][frame] = A
            quad["J"][frame] = J
            quad["Wy"][frame] = Wy
            quad["moment_h"][frame] = moment_h
            quad["long_stress"][frame] = long_stress
            quad["max_long_stress"][frame] = basics.return_max_diff_to_zero(long_stress)
            quad["shear_h"][frame] = shear_h
            quad["tau_shear"][frame] = tau_shear
            quad["sigmav"][frame] = sigmav
            quad["sigma"][frame] = quad["long_stress"][frame]

            quad["overstress"][frame] = False
            quad["utilization"][frame] = utilization

            quad["strain_energy"][frame] = strain_energy
            quad["normal_energy"][frame] = normalkraft_energie
            quad["moment_energy"][frame] = moment_energie

		# update progress
		progress.http.update_i()

		# get duration
		text = calculation_type + " involvement for frame " + str(frame) + " done"
		text +=  basics.timer.stop()
		print_data(text)

		data["done"][str(frame)] = True
