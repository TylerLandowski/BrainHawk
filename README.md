# BrainHawk

## What is BrainHawk?
BrainHawk is designed for easy machine learning in Python for games running inside the BizHawk emulator. It allows a Python script to control the emulator, grab screenshots, and obtain data from a game's memory.

BrainHawk allows you to host a server (in Python) and a BizHawk plugin (in Lua) to communicate data in an easy way, specifically for machine learning and data collection. The focus is to avoid Lua scripting as much as possible, and provide functions and variables commonly used in learning algorithms, in order to organize projects in a clean way.

An overview of the two files and what to do with them is included below.

## BHServer.py
The primary role of the server is to store data. It's capable of interpretting simple commands from a client, particularly to set or send data. You'll want to write your own Python file that calls the ```BHServer()``` command to return an instance of the server. That file should contain the code to handle the data received. For instance, it could run a machine learning algorithm.

## BHClient.lua
The primary role of the client is to play the game while sending data (e.g. screenshots and other data) to the server, and receiving instructions back (e.g. controls to use, emulator commands, and reset commands). You'll want to write your own Lua file that instantiates a BHClient. Your code will run in a while loop that advances the frames of the emulator and chooses what data to write and when.

## Writing a tool with BHServer.py
Your Python tool will interact with the data from BizHawk and send data back. Whether you're running a machine learning algorithm or just logging data, you'll do it here in Python. Rather than having a completely separate client, we can directly interact with the server using our own Python code.

We start off by importing, instantiating, and starting the server.

```Python
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
	saves = {"Save/MarioKart.State": 1} # Add a save state
)
server.start()
```

The server takes a large number of arguments that come in 4 types:
* Server Settings - How the server should operate
* Data Settings - How the server should store data
* Client Settings - How the client should operate
* Emulator Settings - How the emulator should be initialized and changed

Note that there is argument for loading the ROM. Instead, save states are read for flexibility, and they are stored in a dictionary along numbers representing the respective probability. When the emulator is asked to reset, the server randomly picks a save to send back. The relative path of the save, when read, will begin at the root of the BizHawk directory.

Every so many frames, the client will 'update' to the server, by sending data and requesting data back. Every time the client calls an update, the server's update() function is called. You should write the update function yourself, then override the server's function with yours.

Let's say every time the server is updated, we want to press the A button, grab the last screenshot, and preview it. We want to grab a variable the client has stored, labeled "x", to demonstrate auxiliary data storage. The .lua tool will set a variable 'x' as an Int that we will read.

After 20 updates, we'll show only the last screenshot stored.
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
		server.save_screenshot(actions - 1, "my_screenshot.png")
	elif actions == 40:
		server.restart_episode()             # Reset the emulator, set actions = 0


# Replace the server's update function with ours
BHServer.update = update
```

The server file is responsible for telling the client how to operate, so you don't have to do it in Lua. Note that there are no user commands to send data directly to the client. Data is automatically sent to the client, but only when it is requested. For example, the ```restart_episode()``` command will set a flag telling the client to reset the emulator, which will be automatically checked at every update from the client. Most data needed by the client is sent as parameters to the server upon initialization - for example, emulation speed, update interval, and save location.

You should now have a general idea of storing and accessing data on the server, and commanding the emulator. This sample file is included as SampleTool.py. When run, it should print 'Ready.' and wait for the client.

## Writing a tool with BHClient.lua
Your Lua tool/BizHawk plugin should be run only after the server has begun running and is 'Ready'.

First, we need to import, instantiate, and initialize the client.
The initialize() function retrieves settings for playing from the server, including:
* How often (in frames) to communicate with the server
* How fast to play the game
* Save state to use
* more

```lua
require("./BHClient")
c = BHClient:new("http://127.0.0.1:1337")
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

Since the server interprets a set of statements, we simply built a list of them and sent it using sendList(). sendList() will return the server's response to each statement in order. Statements like UPDATE and SET give no response, so we don't worry about them. The only reason saveScreenshot() is sent separately is because of hard limitations in the Lua library of BizHawk.

Afterwards, we sent the returns from sendList() to their functions. The reasoning behind this was simplicity, but more importantly, minimizing the total latency which tends to build, especially given BizHawk's limitations. 

Notice the updateStatement(). This tells the server to call its update() function, which does nothing until you implement it in your python program. Be careful with this. You'll want to call an update before you receive any data from the server. If your machine learning model generates controls given a screenshot, you'll want to send the screenshot, then update, then grab the controls in that order.

You should now have an idea of how to write a Lua plugin that runs the game and commands the client by sending and receiving data. This sample file is included as SampleTool.lua. When run, it should print 'BHClient.lua loaded!' and continue running.

## Setting up BizHawk
BrainHawk was designed specifically for the most recent version of BizHawk (2.3). It likely will not work on older versions.

Open EmuHawk.exe. You'll want to open the game (ROM) of your choice, and create a save slot wherever you choose by clicking File -> Save State -> ... . This is what will load every time the emulator is asked to reset. For simplicity, you can tell the server to load any of the states from 0-9, with 1 being the default (external states are not supported). Next, click Tools -> Lua Console. Click Open Script, and once your server is started and 'Ready', open the .lua file you created.

If you want to pause the game or learning process at any time, click Emulation -> Pause. This will not break the server or client - it simply waits for you to unpause.

_**NOTE: BizHawk cannot send screenshots greater than an unknown size.**_ Somewhere around maybe 70k bytes, the BizHawk script which calls a screenshot will crash. This is an unfortunate limitation we cannot get past at the moment. To work around this, you'll have to change your rendering settings. In particular, you'll want to change your resolution to somewhere less than 160x120 for N64, though 160x120 works most of the time. You'll have to experiment. The more 'complex' a picture is, the more space it will take up when compressed. Therefore, although you may get past the loading screen at high resolutions, expect a crash once you begin the game.

## Server Data
Server data types are based off of Python's data types. Currently, only a few are supported:
* Int

There are many variables built in to the server outside of the data variable. Here are a few:
* reset

## Server Functions

## Client Functions

Most of the client's functions offer a 'statement' alternative. These statements can be compiled into a list and sent using the 'sendList' function. This minimizes unnecessary hang times by sending all data, and retrieving all data, to and from the server in one message.

```lua set(var, val, dataType)```
Set's a variable on the server.
If no dataType is given, assume 

## Server Message Syntax
Sending custom TCP messages to the server is largely unnecessary since their functions are already implemented in the Lua client. However, for extended functionality, or for implementing functionality in a different language, here is the syntax:

For retrieving any variable (and its type):
* `GET var`
* If the variable does not exist, will return "None"

For setting a defined variable:
* `SET var val`
* val is expected to be interpretable as the appropriate data type. Therefore, an Int could be set to -143, but not a string.

For setting a user-defined variable (not list):
* `SET var type val`

For setting a user-defined variable (list):
* `SET var type[] val [e1, e2, ...]`
* Every element in the list must be specified, as well as the list type
