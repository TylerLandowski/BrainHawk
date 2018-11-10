from DQN import DQN
import numpy as np

dqn = DQN(input_shape = (120, 160, 4), action_space = [0,1,2,3,4])
dqn.build_network()

state = np.zeros((120, 160, 4))
state_p = np.expand_dims(state, axis=0)

for i in range(0, 12):
	dqn.save_experience(state, 3, 1, state, False)

dqn.replay()

print("Done!")