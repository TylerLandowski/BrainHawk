import numpy as np
import random  # Grabbing random mini-batches, and generating random actions
from collections import deque
from keras.models import load_model  # Loading DQN base model from disk
from keras.models import Sequential, Model
from keras.optimizers import Adam
from keras.layers import Dense, Flatten, Conv2D, BatchNormalization, Dropout, MaxPooling2D, Input
import h5py  # Saving DQN base model to disk
import pickle  # Saving python variables to disk


class DQN:
	NETWORKS = ["nvidia", "mini_driver", "micro_driver", "mario_driver"]

	def __init__(
			self,
			name = "dqn",  # Name used for saving and loading the DQN
			load = True,
			train = True,  # If false, will not use epsilon, and will not update networks or models
			network = None,
			auto_save = 100,
			ddqn = True,
			target_update_interval = 500,
			action_space = list(),
			input_shape = (120, 160, 3),
			batch_size = 32,  # Number of
			episodes_max = None,  # TODO
			replay_size_max = 1000,  # Number of experiences to store at one time
			gamma = .95,  # Discount rate
			epsilon_init = 1.0,  # Exploration rate
			epsilon_steps = 2000,  # Number of steps until epsilon_min is reached
			epsilon_min = 0.01,  # Minimum value to be reached for epsilon while training
			alpha = 1e-4,  # Learning rate of Adam optimizer
	):
		self.name = name
		self.train = train

		if load:
			self.load_model()
		else:
			self.auto_save = auto_save
			self.ddqn = ddqn
			self.target_update_interval = target_update_interval
			self.num_replays = 0
			self.action_space = action_space
			self.action_count = len(action_space)
			self.input_shape = input_shape
			self.batch_size = batch_size
			self.episodes_max = episodes_max
			self.replay_size_max = replay_size_max
			self.gamma = gamma
			self.epsilon = epsilon_init
			self.epsilon_decay = (epsilon_init - epsilon_min) / epsilon_steps
			self.epsilon_min = epsilon_min
			self.alpha = alpha
			self.experiences = deque(maxlen = replay_size_max)
			if network in self.NETWORKS:
				self.build_network(network)
			else:
				self.network = network

		if network is not None:
			# Initialize the networks
			self.target_network = self.network
			self.force_graph()
			self.network.summary()

	# Force graph creation (for multithreading)
	def force_graph(self):
		self.network._make_predict_function()
		self.network._make_test_function()
		self.network._make_train_function()
		self.target_network._make_predict_function()
		self.target_network._make_test_function()
		self.target_network._make_train_function()

	def build_network(self, model):
		if model == "nvidia":
			nvidia = Sequential()
			nvidia.add(BatchNormalization(input_shape = self.input_shape))
			nvidia.add(Conv2D(24, kernel_size = (5, 5), strides = (2, 2), activation = 'relu'))
			nvidia.add(BatchNormalization())
			nvidia.add(Conv2D(36, kernel_size = (5, 5), strides = (2, 2), activation = 'relu'))
			nvidia.add(BatchNormalization())
			nvidia.add(Conv2D(48, kernel_size = (5, 5), strides = (2, 2), activation = 'relu'))
			#nvidia.add(BatchNormalization())
			#nvidia.add(Conv2D(64, kernel_size = (3, 3), activation = 'relu'))
			#nvidia.add(BatchNormalization())
			#nvidia.add(Conv2D(64, kernel_size = (3, 3), activation = 'relu'))
			nvidia.add(Flatten())
			nvidia.add(Dense(1164, activation = 'relu'))
			drop_out = 1 - .6
			nvidia.add(Dropout(drop_out))
			nvidia.add(Dense(100, activation = 'relu'))
			nvidia.add(Dropout(drop_out))
			nvidia.add(Dense(50, activation = 'relu'))
			nvidia.add(Dropout(drop_out))
			nvidia.add(Dense(10, activation = 'relu'))
			nvidia.add(Dropout(drop_out))
			nvidia.add(Dense(self.action_count, activation = None))
			self.network = nvidia

		elif model == "mini_driver":
			md = Sequential()
			md.add(BatchNormalization(input_shape = self.input_shape))
			md.add(Conv2D(filters = 8, kernel_size = (3, 3), activation = "relu"))
			md.add(MaxPooling2D(pool_size = (4, 4), strides = (4, 4), padding = 'valid'))
			# md.add(Conv3D(filters = 2, kernel_size = (3, 3, 4), activation = "relu", data_format = "channels_last"))
			# md.add(MaxPooling3D(pool_size = (4, 4, 1), strides = (1, 1, 1), padding = "valid",
			#                     data_format = "channels_last"))
			md.add(Dropout(0.25))
			md.add(Flatten())
			# md.add(Dense(100, activation = 'relu'))
			# md.add(Dropout(.25))
			md.add(Dense(self.action_count, activation = None))
			self.network = md

		elif model == "micro_driver":
			md = Sequential()
			md.add(BatchNormalization(input_shape = self.input_shape))
			md.add(Conv2D(filters = 8, kernel_size = (3, 3), activation = "relu"))
			md.add(MaxPooling2D(pool_size = (4, 4), strides = (4, 4), padding = 'valid'))
			# md.add(Conv3D(filters = 2, kernel_size = (3, 3, 4), activation = "relu", data_format = "channels_last"))
			# md.add(MaxPooling3D(pool_size = (4, 4, 1), strides = (1, 1, 1), padding = "valid",
			#                     data_format = "channels_last"))
			md.add(Dropout(0.25))
			md.add(Flatten())
			# md.add(Dense(100, activation = 'relu'))
			# md.add(Dropout(.25))
			md.add(Dense(self.action_count, activation = None))
			self.network = md

		elif model == "mario_driver":
			md = Sequential()
			md.add(BatchNormalization(input_shape = self.input_shape))
			md.add(Conv2D(16, (1, 1), padding = "same", activation = "elu"))
			md.add(BatchNormalization())
			md.add(Conv2D(16, (3, 3), padding = "same", activation = "elu"))
			md.add(BatchNormalization())
			md.add(Conv2D(16, (1, 1), padding = "same", activation = "elu"))
			md.add(BatchNormalization())
			md.add(Conv2D(16, (3, 3), padding = "same", activation = "elu"))
			md.add(BatchNormalization())
			md.add(Conv2D(16, (3, 3), padding = "same", activation = "elu"))
			md.add(MaxPooling2D((3, 3), strides = (1, 1), padding = "same"))
			md.add(BatchNormalization())
			md.add(Conv2D(16, (1, 1), padding = "same", activation = "elu"))
			md.add(Flatten())
			md.add(Dense(self.action_count, activation = None))
			self.network = md

		self.network.compile(loss = 'mse', optimizer = Adam(lr = self.alpha, clipvalue = 1))

		#
		# self.model = Sequential()
		# self.model.add(Dense(24, input_shape = self.input_shape, activation = 'relu'))
		# self.model.add(Dense(24, activation = 'relu'))
		# self.model.add(Dense(self.action_count, activation = 'linear'))
		# self.model.compile(loss = 'mse', optimizer = Adam(lr = self.alpha))

	def save_experience(
			self,
			state,
			action,
			reward,  # Float
			next_state,
			terminal  # Bool
	):
		self.experiences.append((state, action, reward, next_state, terminal))

	def replay(self):
		if self.train:
			# Select a number of experiences
			if len(self.experiences) < self.batch_size:
				minibatch = random.sample(self.experiences, len(self.experiences))
			else:
				minibatch = random.sample(self.experiences, self.batch_size)

			# Train for each experience
			for state, action, reward, next_state, terminal in minibatch:
				state = np.expand_dims(state, axis = 0)
				next_state = np.expand_dims(next_state, axis = 0)

				# Calculate target network
				target = reward
				if not terminal:
					Q_next = self.network.predict(next_state)[0]

					# Predict the reward for the next given state
					if self.ddqn:
						# Q(s,a) <- r(s,a) + γ*Q(s', argmax_a(Q(s', a)))
						target += self.gamma * Q_next[action]
					else:
						# Q(s,a) <- r(s,a) + γ*max_aQ(s', a)
						target += self.gamma * np.amax(Q_next[0])

				# make the agent to approximately map
				# the current state to future discounted reward
				# We'll call that target_f
				target_f = self.target_network.predict(state)
				target_f[0][action] = target

				# Train the Neural Net with the state and target_f
				# K.clear_session()
				self.network.fit(state, target_f, epochs = 1, verbose = 0)

				if self.num_replays % self.target_update_interval == 0:
					# Q' <- Q
					self.target_network = self.network

			# Decay epsilon?
			if self.epsilon > self.epsilon_min:
				self.epsilon -= self.epsilon_decay

			# Save the model?
			self.num_replays += 1
			if self.num_replays % self.auto_save == 0:
				self.save_model()

	def select_action(self, state):
		# Should we explore?
		if self.train and np.random.rand() <= self.epsilon:
			# Act randomly
			return random.choice(self.action_space), True

		# Should we exploit?
		else:
			state = np.expand_dims(state, axis = 0)
			# Choose an action with highest predicted reward
			return self.network.predict_classes(state)[0], False

	def save_model(self):
		# Save the base network, skip the target network
		self.network.save(self.name + ".h5")

		# Variables to save
		v = {
			# "train": self.train,
			"auto_save": self.auto_save,
			"ddqn": self.ddqn,
			"target_update_interval": self.target_update_interval,
			"num_replays": self.num_replays,
			"input_shape": self.input_shape,
			"batch_size": self.batch_size,
			"episodes_max": self.episodes_max,
			"replay_size_max": self.replay_size_max,
			"gamma": self.gamma,
			"epsilon": self.epsilon,
			"epsilon_decay": self.epsilon_decay,
			"epsilon_min": self.epsilon_min,
			"alpha": self.alpha,
			# Possibly large values
			"action_space": self.action_space,
			"experiences": self.experiences
		}

		with open(self.name + ".pkl", "wb") as file:
			pickle.dump(v, file)

		print("Model saved - num_replays = " + str(self.num_replays))

	def load_model(self):
		# Load the base model
		self.network = load_model(self.name + ".h5")
		self.target_network = self.network

		# Load the dictionary of values
		with open(self.name + ".pkl", "rb") as file:
			v = pickle.load(file)
			# self.train = v["train"]
			self.auto_save = v["auto_save"]
			self.ddqn = v["ddqn"]
			self.target_update_interval = v["target_update_interval"]
			self.num_replays = v.get("num_replays")
			self.input_shape = v.get("input_shape")
			self.batch_size = v["batch_size"]
			self.episodes_max = v["episodes_max"]
			self.replay_size_max = v["replay_size_max"]
			self.gamma = v["gamma"]
			self.epsilon = v["epsilon"]
			self.epsilon_decay = v["epsilon_decay"]
			self.epsilon_min = v["epsilon_min"]
			self.alpha = v["alpha"]
			self.action_space = v["action_space"]
			self.action_count = len(self.action_space)
			self.experiences = v["experiences"]
