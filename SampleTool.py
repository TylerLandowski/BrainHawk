from BHServer import BHServer

# Start the TCP server
server = BHServer(
	ip = "127.0.0.1",
	port = 1337,
	update_interval = 5,   # Update the server every 5 frames
	use_grayscale = True,  # Store screenshots in greyscale
	system = "N64",        # Initialize server.controls to standard N64 controls
	speed = 6399,          # Emulate at 6399% original game speed
	sound = False,         # Turn off sound
	save_slot = 1          # Load state 1
)
server.start()

def update(self):
	actions = server.actions               # Grab number of times update() has been called
	print(server.actions)
	server.controls["P1 A"] = True         # Press the A button on Player 1's controller
	ss = server.screenshots[actions - 1]   # Grab the last screenshot (numpy.ndarray)
	print(ss.shape)                        # Print shape of screenshot
	x_type = server.data["x"][0]           # Get type of variable x: "Int"
	x = server.data["x"][1]                # Get value of variable x: 512
	
	if actions == 40:
		server.restart_episode()             # Reset the emulator, set actions = 0

# Replace the server's update function with ours
BHServer.update = update
print("Ready.")