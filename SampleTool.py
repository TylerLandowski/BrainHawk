from BHServer import BHServer

# Start the TCP server
server = BHServer(
	# Server Settings
	ip = "127.0.0.1",
	port = 1337,
	# Data Settings
	use_grayscale = True,  # Store screenshots in grayscale
	system = "N64",  # Initialize server.controls to standard N64 controls
	# Client Settings
	update_interval = 5,  # Update to server every 5 frames
	frameskip = 1,
	speed = 6399,  # Emulate at 6399% original game speed (max)
	sound = False,  # Turn off sound
	rom = "ROM/MarioKart64.n64",  # Add a game ROM file
	saves = {"Save/MarioKart64.State": 1}  # Add a save state
)
server.start()

# first_iteration = True TODO

def update(self):
	if self.client_started():
		print(self.actions)
		print(self.screenshots[self.actions - 1].shape)

	actions = self.actions  # Grab number of times update() has been called
	ss = self.screenshots[actions - 1]  # Grab the last screenshot (numpy.ndarray)

	self.controls["P1 A"] = True         # Press the A button on Player 1's controller
	x_type = self.data["x"][0]           # Get type of variable x: "Int". Set by client
	x = self.data["x"][1]                # Get value of variable x: 512. Set by client

	if actions == 20:
		self.save_screenshots(0, actions - 1, "my_screenshot.png")
	elif actions == 40:
		self.new_episode()      # Reset the emulator, actions = 0, ++episodes
		if self.episodes == 3:  # Stop client after 3 episodes
			self.stop_client()


# Replace the server's update function with ours
BHServer.update = update
print("Ready.")

# Optional loop that can be implemented. Runs in main thread rather than server
# while True:
#     pass
