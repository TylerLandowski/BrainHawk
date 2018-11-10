# BrainHawk

## What is BrainHawk?
BrainHawk allows you to host a server (in Python) as well as a client (in BizHawk) to communicate data in an easy way, particularly for machine learning. The focus is to avoid Lua scripting as much as possible. 

## BHServer.py
The primary role of the server is to store data. It's capable of interpretting simple commands from a client, particularly to set or send data. 

## BHClient.lua
The primary role of the client is to play the game while sending data (e.g. screenshots and other data) to the server, and receiving instructions back (e.g. controls to use, emulator commands, and reset statements).

## Writing a tool with BHServer.py
Your Python tool will interact with the data from BizHawk and send data back. Whether you're running a machine learning algorithm or just logging data, you'll do it here in Python. Rather than having a completely separate client, we can directly interact with the server using our own Python code.

We start off by importing, instantiating, and starting the server.

```Python
from BHServer import BHServer

# Start the TCP server
server = BHServer(
	ip = "127.0.0.1",
	port = 1337,
	update_interval = 5,   # Update the server every 5 frames
	use_grayscale = true,  # Store screenshots in greyscale
	system = "N64",        # Initialize server.controls to standard N64 controls
	speed = 6399,          # Emulate at 6399% original game speed
	sound = false,         # Turn off sound
	save_slot = 1          # Load state 1
)
server.start()
```

Every time the client calls an update, the server's update() function is called. You should write the update function yourself, then override the server's function with yours.

Let's say we wanted to press the A button, grab the last screenshot, and preview it. The .lua tool will set a variable 'x' as an Int that we will read.

After 40 updates, we'll reset the emulator.

```Python
def update(self):
	actions = server.actions               # Grab number of times update() has been called
	print(server.actions)
	server.controls["P1 A"] = True         # Press the A button on Player 1's controller
	ss = server.screenshots[actions - 1]   # Grab the last screenshot (numpy.ndarray)
	print(ss.shape)                        # Print shape of screenshot
	x_type = server.data["x"][0]           # Get type of variable x: "Int"
	x = server.data["x"][1]                # Get value of variable x: 512
	
	if actions == 20:
		server.show_screenshot(actions - 1)  # Preview the last screenshot
	elif actions == 40:
		server.restart_episode()             # Reset the emulator, set actions = 0

# Replace the server's update function with ours
BHServer.update = update
```

## Writing a tool with BHClient.lua
Your Lua tool/BizHawk plugin should be run after the server has begun running and is 'Ready'.

First, we need to import, instantiate, and initialize the client.
The initialize() function retrieves settings for playing from the server, including:
* How often (in frames) to communicate with the server
* How fast to play the game
* Game's slot for save-state
* more

```lua
require("./BHClient")
c = DLSClient:new("http://127.0.0.1:1337")
c:initialize()
```

The loop that runs along with the game is defined here. We'll assume you want to use controls from the server, and only communicate with the server every so many frames. useControls() applies controls saved previously from the server, and must be called before every frame, since controls are reset continuously.

```lua
while true do
	c:useControls()   -- Set the controls to use until the next frame
	c:advanceFrame()  -- Advance a single frame
	
	-- Is it time to communicate with the server?
	if c:handleUpdate() then
		-- Send/Receive info from the server
	end
end
```

Inside that if statement is where you should put code to communicate with the server. Let's say you want to send a screenshot, grab new controls, and ask if we should reset the game to the save. Inside the if statement, we'd place this code:

```lua
c:saveScreenshot()

-- Build a list of statements (to send in one request to server)
local statements = {
	c:updateStatement(),          -- Call server's update(). No return
	c:updateControlsStatement(),  -- Returns controls from server
	c:checkRestartStatement(),    -- Returns whether emulator should reset
	"SET x Int 512"               -- Set x = 512 (as a Python Int). No return
}

-- Send statements, grab results
local controlsString, restart = c:sendList(statements)

-- Send results to the appropriate functions
c:updateControls(controlsString)
c:checkRestart(restart)
```

Since the server interprets a set of statements, we simply built a list of them and sent it using sendList(). sendList() will return the server's response to each statement in order. Statements like UPDATE and SET give no response, so we don't worry about them. The only reason saveScreenshot() is sent separately is because of hard limitations in the Lua libary of BizHawk.

Afterwards, we sent the returns from sendList() to their functions. The reasoning behind this was simplicity, but more importantly, minimizing the total latency which tends to build, especially given BizHawk's limitations. 

Notice the updateStatement(). This tells the server to call its update() function, which does nothing until you implement it in your python program. Be careful with this. You'll want to call an update before you receive any data from the server. If your machine learning model generates controls given a screenshot, you'll want to send the screenshot, then update, then grab the controls in that order.

## Setting up BizHawk
BrainHawk was designed specifically for the most recent version of BizHawk (2.3). It likely will not work on older versions.

Open EmuHawk.exe. You'll want to open the game (ROM) of your choice, and create a save slot wherever you choose by clicking File -> Save State -> ... . This is what will load every time the emulator is asked to reset. For simplicity, you can tell the server to load any of the states from 0-9, with 1 being the default (external states are not supported). Next, click Tools -> Lua Console. Click Open Script, and once your server is started and 'Ready', open the .lua file you created.

If you want to pause the game or learning process at any time, click Emulation -> Pause. This will not break the server or client - it simply waits for you to unpause.

_**NOTE: BizHawk cannot send screenshots greater than an unknown size.**_ Somewhere around maybe 70k bytes, the BizHawk script which calls a screenshot will crash. This is an unfortunate limitation we cannot get past at the moment. To work around this, you'll have to change your rendering settings. In particular, you'll want to change your resolution to somewhere less than 160x120 for N64, but 160x120 works most of the time. You'll have to experiment. The more 'complex' a picture is, the more space it will take up. Therefore, although you may get past the loading screen, expect a crash once you begin the game at high resolutions.

## Server Message Syntax
Sending custom TCP messages to the server is largely unnecessary since their functions are already implemented in the Lua client. However, for extended functionality, or for implementing functionality in a different language, here is the syntax:

For retrieving any variable:
* `GET var`
* If the variable does not exist, will return "None"

For setting a predefined variable:
* `SET var val`
* val is expected to be a interpretable as the appropriate data type

For setting a user-defined variable (not list):
* `SET var type val`

For setting a user-defined variable (list):
* `SET var type[] val [e1, e2, ...]`
