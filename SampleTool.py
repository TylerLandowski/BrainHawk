import matplotlib.pyplot as plt  # Visualizing screenshots

from BHServer import BHServer

# Start the TCP server
server = BHServer(
	# Server Settings
	ip = "127.0.0.1",
	port = 1337,
	# Data Settings
	use_grayscale = True,  # Store screenshots in grayscale
	system = "N64",        # Initialize server.controls to standard N64 controls
	# Client Settings
	update_interval = 5,   # Update to server every 5 frames
	# Emulator Settings
	speed = 6399,          # Emulate at 6399% original game speed (max)
	sound = False,         # Turn off sound
	saves = {"Save/MarioKart.State": 1}  # Add a save state
)
server.start()

first_iteration = True

def update(self):
	if server.emu_started:
		print(server.actions)
		print(server.screenshots[server.actions - 1].shape)
		server.emu_started = False

	actions = self.actions  # Grab number of times update() has been called
	ss = self.screenshots[actions - 1]  # Grab the last screenshot (numpy.ndarray)

	self.controls["P1 A"] = True         # Press the A button on Player 1's controller
	x_type = self.data["x"][0]           # Get type of variable x: "Int"
	x = self.data["x"][1]                # Get value of variable x: 512

	if actions == 20:
		self.save_screenshot(actions - 1, "my_screenshot.png")
	elif actions == 40:
		self.stop()
		self.restart_episode()             # Reset the emulator, set actions = 0


# Replace the server's update function with ours
BHServer.update = update
print("Ready.")

# Optional loop. Runs in main thread rather than server
while True:
	pass