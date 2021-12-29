# Phänotyp
by bewegende Architektur e.U.  
with support from Karl Deix  

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
* Single frames, animations and genetic mutations with shape-keys can be performed
* This is a very early stage of development. The tool is intended to be used by more experienced users of Blender 3D at the moment.

## Roadmap
* Better implementation for different types of supports and loads
* Small material library and common sections
* Implementation of critical force and others
* Improvement of genetic algorithm
* Adding more inputs to the GA for example modifiers
* Adding more functions of fitness and its combination like created volume, area, light, shape and other

## Getting started
You can find three quick tutorials on Youtube:  
https://youtu.be/shloSw9HjVI  
https://youtu.be/i-5duKyuBiU  
https://youtu.be/F5ilsBDoIkY  

## Current release
2021-12-29 | version 0.0.2 for blender 3.0.0:  
<a href="https://github.com/bewegende-Architektur/Phaenotyp/releases" target="_blank">Phaenotyp 0.0.2</a>
