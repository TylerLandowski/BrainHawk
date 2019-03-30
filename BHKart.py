from BHServer import BHServer
from DQN import DQN
import numpy as np
from skimage.transform import resize

RECORDING = False  # If true, will record the experiences (to learn from human gameplay)
EXPERIENCES_NAME = "experiences"
TRAIN = True  # If true, will train the model
LOAD_DQN = False
MODEL_NAME = "nvidia_kart64"
MODEL_TYPE = "nvidia"
SCROT_Y = 60  # 120, 105
SCROT_X = 120  # 160, 140
SCROT_GRAY = True
STACK_SZ = 4
UPDATE_INTERVAL = 5


# Start the TCP server
server = BHServer(
	# Server Settings
	ip = "127.0.0.1",
	port = 1337,
	# Data Settings
	use_grayscale = SCROT_GRAY,
	system = "N64",
	# Client Settings
	update_interval = UPDATE_INTERVAL,
	frameskip = 1,
	speed = 6399 if TRAIN else 100,
	sound = not TRAIN,
	rom = "ROM/MarioKart64.n64",
	saves = {"Save/MarioKart64.State": 1}
)
server.start()

# Define a discrete action space for DQN
pos_acts = [
	("P1 A", [True]),
	("P1 X Axis", [-128, -63, -30, 0, 30, 63, 127])
]
action_map = server.make_action_map(pos_acts)
action_space = server.make_action_space(action_map)

# Create a DQN
dqn = DQN(
	name = MODEL_NAME,
	train = TRAIN,
	load = LOAD_DQN,
	auto_save = 50,
	network = MODEL_TYPE,
	ddqn = False,
	action_space = action_space,
	target_update_interval = 100,
	input_shape = (SCROT_Y, SCROT_X, STACK_SZ),
	batch_size = 32,
	replay_size_max = 1000,
	gamma = .95,
	epsilon_init = 0.9,
	epsilon_steps = 100000,
	epsilon_min = 0.02,
	alpha = 1e-4,
)

server.stack_size = 0
server.prev_state = None
server.prev_action = None
server.prev_reward = None
server.high_score = 0


def preprocess(img):
	img2 = server.crop_percent(img, .2, .15, .35, .15)
	img2 = resize(img2, (SCROT_Y, SCROT_X))
	return img2


def get_score():
	actions = server.actions
	return server.data["distance"][1][actions - 1] / actions


def get_state():
	# Return a stack of the last 4 screenshots
	# shape: (120, 160, 4)
	actions = server.actions
	state = preprocess(np.stack([
		server.screenshots[actions - 4],
		server.screenshots[actions - 3],
		server.screenshots[actions - 2],
		server.screenshots[actions - 1],
	], axis = 2))
	return state


def get_reward():
	# Calculate the reward based on the distance travelled since last experience
	actions = server.actions
	dist_now = server.data["distance"][1][actions - 1]
	dist_prev = server.data["distance"][1][actions - 5]
	rwd = dist_now - dist_prev
	#print(rwd)
	return rwd


# TODO Support different update intervals
def is_stuck():
	# Check if the AI is stuck (not progressing fast enough). If it does not move a certain speed, or moves backwards,
	# we can safely ignore training in that state and place it in the initial state

	actions = server.actions
	frames = actions * UPDATE_INTERVAL

	if frames >= 200:  # 400
		stt_dist = server.data["distance"][1][actions - 40]
		end_dist = server.data["distance"][1][actions - 1]
		tot = end_dist - stt_dist
		avg = tot / 12  # 9
		progressing = avg >= 1

		return not progressing

	else:
		return False


def is_terminal():
	return is_stuck() or completed_lap()


def completed_lap():
	return server.data["distance"][1][server.actions - 1] == 1893  # Luigi Raceway Distance


def controls_from_action(action):
	return action_map[action]


def update(self):
	self.stack_size += 1
	server.show_screenshot(server.actions - 1)

	# Do we have at least 2 stacks worth of frames?
	if server.actions >= 2 * STACK_SZ + 1:
		if self.stack_size == 4:
			self.stack_size = 0
			terminal = is_terminal()

			#
			# Save this experience into the DQN's replay memory
			# Save data for the next experience
			#

			state = get_state()

			if TRAIN:
				# Save data
				dqn.save_experience(self.prev_state, self.prev_action, self.prev_reward, state, terminal)
				# print("prev_state: " + str(self.prev_state.shape))
				# print("prev_act: " + str(self.prev_action))
				# print("prev_rew: " + str(self.prev_reward))
				# print("state: " + str(state.shape))
				# dqn.replay()

			if terminal:
				dqn.replay()
				score = get_score()
				self.high_score = score if score > self.high_score else self.high_score

				if dqn.num_replays % 50 == 0:
					print("High Score: " + str(self.high_score))
					self.high_score = 0

				# Don't wait for the next state
				server.new_episode()
			else:
				self.prev_state = state
				self.prev_action, server.guessed = dqn.select_action(state)
				self.prev_reward = get_reward()
				server.controls = controls_from_action(self.prev_action)

	else:
		# Record the first frame as a starting point
		if self.stack_size == 1:
			# Send a black screen TODO Change for grayscale
			self.prev_action = dqn.select_action(np.zeros((SCROT_Y, SCROT_X, STACK_SZ)))

		# Don't learn on first stack - we need at least 2
		if self.stack_size == 1 + STACK_SZ:
			self.stack_size = 0
			self.prev_state = get_state()
			self.prev_reward = get_reward()
			self.prev_action, server.guessed = dqn.select_action(self.prev_state)
			server.controls = controls_from_action(self.prev_action)


# Replace the server's update function with ours
BHServer.update = update
print("Ready.")
