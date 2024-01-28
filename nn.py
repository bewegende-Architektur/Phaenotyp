import bpy

import numpy as np

def highest_fitness(individuals, name):
	highest = 0
	for frame, individual in individuals.items():        
		v = individual["fitness"][name]
		if v > highest:
			highest = v
	
	return highest

# based on Déborah Mesquita
# https://realpython.com/python-ai-neural-network/

class neural_network:
	def __init__(self, learning_rate, matrix_size):
		weights = []
		for i in range(matrix_size):
			weights.append(np.random.randn())
			
		self.weights = np.array(weights)
		self.bias = np.random.randn()
		self.learning_rate = learning_rate

	def _sigmoid(self, x):
		return 1 / (1 + np.exp(-x))

	def _sigmoid_deriv(self, x):
		return self._sigmoid(x) * (1 - self._sigmoid(x))

	def train(self, input_vectors, targets, iterations):
		cumulative_errors = []
		for current_iteration in range(iterations):
			# Pick a data instance at random
			random_data_index = np.random.randint(len(input_vectors))
			input_vector = input_vectors[random_data_index]
			target = targets[random_data_index]

			# Compute the gradients and update the weights
			derror_dbias, derror_dweights = self._compute_gradients(
				input_vector, target
			)

			self._update_parameters(derror_dbias, derror_dweights)

			# Measure the cumulative error for all the instances
			if current_iteration % 100 == 0:
				cumulative_error = 0
				# Loop through all the instances to measure the error
				for data_instance_index in range(len(input_vectors)):
					data_point = input_vectors[data_instance_index]
					target = targets[data_instance_index]
					prediction = self.predict(data_point)
					error = np.square(prediction - target)
					cumulative_error = cumulative_error + error

				cumulative_errors.append(cumulative_error)

		return cumulative_errors

	def predict(self, input_vector):
		layer_1 = np.dot(input_vector, self.weights) + self.bias
		layer_2 = self._sigmoid(layer_1)
		prediction = layer_2
		return prediction

	def _compute_gradients(self, input_vector, target):
		layer_1 = np.dot(input_vector, self.weights) + self.bias
		layer_2 = self._sigmoid(layer_1)
		prediction = layer_2

		derror_dprediction = 2 * (prediction - target)
		dprediction_dlayer1 = self._sigmoid_deriv(layer_1)
		dlayer1_dbias = 1
		dlayer1_dweights = (0 * self.weights) + (1 * input_vector)

		derror_dbias = (
			derror_dprediction * dprediction_dlayer1 * dlayer1_dbias
		)
		derror_dweights = (
			derror_dprediction * dprediction_dlayer1 * dlayer1_dweights
		)

		return derror_dbias, derror_dweights

	def _update_parameters(self, derror_dbias, derror_dweights):
		self.bias = self.bias - (derror_dbias * self.learning_rate)
		self.weights = self.weights - (
			derror_dweights * self.learning_rate
		)

def start():
	'''
	Main function to run neural network.
	'''

	scene = bpy.context.scene
	data = scene["<basics.print_data>"]
	obj = data["structure"]
	shape_keys = obj.data.shape_keys.key_blocks
	basics.print_data = scene.basics.print_data

	environment = data["environment"]
	individuals = data["individuals"]
	
	# create / recreate results
	data["results"] = {}
	results = data["results"]

	# get data from gui	
	learning_rate = basics.print_data.nn_learning_rate
	epochs = basics.print_data.nn_epochs
	
	fitness_functions =  individuals["0"]["fitness"]
	for fitness_function, fitness in fitness_functions.items():
		# lists for this fitness
		try:
			chromosomes = []
			targets = []
			# get scale of target for normalization
			scale = highest_fitness(individuals, fitness_function)
			if scale !=0:
				for frame, individual in individuals.items():
					chromosome = individual["chromosome"]
					chromosomes.append(chromosome)
					
					target = individual["fitness"][fitness_function]
					targets.append(target/scale)

			input_vectors = np.array(chromosomes)
			targets = np.array(targets)

			matrix_size = len(individuals["0"]["chromosome"])

			nn = neural_network(learning_rate, 3)
			training_error = nn.train(input_vectors, targets, epochs)
			#print(nn.predict([0.1, 0.7, 0.2])*scale, "should be 32.498")
			#print(nn.weights)
			result = nn.predict([0.1, 0.7, 0.2])*scale
			results[fitness_function] = result
		except:
			pass
