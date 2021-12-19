# Phänotyp
by bewegende Architektur e.U. and Karl Deix  

Phänotyp is an Add-On for Blender 3D  
https://www.blender.org/

It allows to perform genetic mutation of architectural structures. Furthermore it can be used to analyze moving shapes. This is especially useful when working on kinematic architectural projects. The tool is focusing on early stages of the design process and can be used for free without any warranty. If you want to participate in the project please get in contact via:  
chris@bewegende-Architektur.com

Analysis is done with PyNite:  
https://github.com/JWock82/PyNite

GA based on:  
https://www.geeksforgeeks.org/genetic-algorithms/

Material properties based on formulas from:  
https://www.johannes-strommer.com/formeln/flaechentraegheitsmoment-widerstandsmoment/  
https://www.maschinenbau-wissen.de/skript3/mechanik/festigkeitslehre/134-knicken-euler

## Current state
* Phänotyp is working as connection to PyNite
* Right now the focus is on structures with trusses
* Single frames, animations genetic mutations can be performed
* This is a very early stage of development. The tool is intended to be used by more experienced uses of Blender 3D.

## Known issues
* The installation of scipy and blender can cause problems
* Be sure to run Phänotyp as administrator for the first time 

## Roadmap
* Better implementation for different types of supports and loads
* Small material library and common sections
* Implementation of critical force and others
* Improvement of genetic algorithm
* Adding more inputs to the GA for example modifiers
* Adding more functions of fitness and its combination like created volume, area, light, shape and other

## Current release
from 2021-12-18 is version 0.0.1 for blender 3.0.0:  
<a href="https://github.com/bewegende-Architektur/Phaenotyp/blob/main/phaenotyp.zip" target="_blank">Phaenotyp 0.0.1</a>
