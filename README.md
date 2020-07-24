# BrainHawk

## What is BrainHawk?
BrainHawk is designed for enabling machine learning in Python for games running inside the BizHawk emulator. It allows a Python script to control the emulator, grab screenshots, and obtain data from a game's memory.

BrainHawk allows you to host a server (in Python) and a client BizHawk plugin (in Lua) to easily communicate data, specifically for machine learning and data collection. The focus is to require as little Lua scripting as possible, and provide functions and variables commonly used in learning algorithms, in order to organize projects in a clean way.

An overview of the two files and what to do with them is included below.

## BHServer.py
The server is there to store data from the client and send back info for running the emulator. It interprets simple commands from a client. You'll write your own Python file that calls the ```BHServer()``` command to return an instance of the server. That file should contain the code to handle the data received. For instance, it could run a machine learning algorithm.

## BHClient.lua
The client plays the game while sending data (screenshots and more) to the server, and receives instructions back (controls to use, emulator commands, reset/exit requests). You'll write your own Lua file that instantiates a BHClient. Your code will run in a while loop that advances frames and chooses what data to write and when.

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
	use_grayscale = False,
	system = "N64",
	# Client Settings
	update_interval = 5,
	speed = 100,
	rom = "ROM/MarioKart64.n64",
	saves = {"Save/MarioKart64.State": 1}
)
server.start()
```

The server takes a large number of arguments that come in 3 types:
* Server Settings - How server should operate
* Data Settings - How server should store data
* Client Settings - How the client should operate, how emulator should be initialized and changed

The ROM is loaded once emulator begins. The saves, however, are loaded into 'save' variable at each 'episode', or single run of the game. For flexibility, many states can be given, each with a probability of being picked. When the emulator is asked to reset, the server randomly picks a save to send back. Alternatively, the 'save' variable can manipulated directly. *The relative path of the save and ROM should begin at the parent of the BizHawk directory*.

Every so many frames, the client will 'update' to the server, by sending data and requesting data back. Every time the client calls an update, the server's update() function is called. You should write the update function yourself, then override the server's function with yours. This function will synchronize data updates between the server and client, by allowing code to be called using a client's request. For example, the client sends data, calls an update for server to generate controls, and asks for controls back.

Let's say every time the server is updated, we want to press the A button, grab the last screenshot, and preview it. We want to grab a variable the client has stored, labeled "x", to demonstrate auxiliary data storage. The .lua tool will set a variable 'x' as an Int that we will read.

After 20 updates, we'll save the latest screenshot to disk
After 40 updates, we'll start a new episode of learning, and reset emulator
After 3 episodes, we'll stop learning and close the client

```Python
def update(self):
	if self.client_started():
		print(self.actions)
		print(self.screenshots[self.actions - 1].shape)

	actions = self.actions              # Number of times update() has been called
	ss = self.screenshots[actions - 1]  # Grab the last screenshot (numpy.ndarray)
	
	self.controls["P1 A"] = True        # Press the A button on Player 1's controller
	x_type = self.data["x"][0]          # Get type of variable x: "INT". Set by client
	x = self.data["x"][1]               # Get value of variable x: 512. Set by client

	if actions == 20:
		self.save_screenshots(0, actions - 1, "my_screenshot.png")
	elif actions == 40:
		self.new_episode()      # Reset the emulator, actions = 0, ++episodes
		if self.episodes == 3:  # Stop client after 3 episodes
			self.exit_client()
			

BHServer.update = update
print("Ready.")
```

The server file tells the client how to operate, so you don't have to do it in Lua. Note that there are no user commands to send data directly to the client. Data is automatically sent to the client when it is requested. For example, the ```new_episode()``` command will set a flag telling the client to reset the emulator, which will be automatically checked at every update from the client. Most data needed by the client is sent as parameters to the server upon initialization - for example, emulation speed, update interval, and save location.

You should now have a general idea of storing and accessing data on the server, and commanding the emulator. This sample file is included as SampleTool.py. When run, it should print 'Ready.' and wait for the client.

## Writing a tool with BHClient.lua
Your Lua tool (BizHawk plugin) should be run only after the server has begun running and is 'Ready.'

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
	if c:timeToUpdate() then
		-- Send/Receive info from the server
	end
end
```

The ```timeToUpdate()``` function will return True if the number of frames has reached the 'update_interval', so we don't update the server after every single frame.

Inside that if statement is where you should put code to communicate with the server. Say you want to send a screenshot, set some variable x, and receive new controls to use. As always, we'll want to check if we should exit or restart. We'll want to call an UPDATE to the server after sending the screenshot so the server tool can determine the controls based off of it. Inside the if statement, we'd place this code:

```lua
 -- Save a screenshot on the server
c:saveScreenshot()

-- Build a list of statements (to send in one request to server)
local statements = {
    c:setStatement("x", 512, "INT"),  -- Set x = 512 (as a Python Int). No return
    c:getStatement("x"),              -- Get value for x
    c:updateStatement(),              -- Call server's update(). No return
    c:setControlsStatement(),         -- Returns controls from server
    c:checkRestartStatement(),        -- Returns whether emulator should reset
    c:checkExitStatement()            -- Returns whether client should exit
}

-- Send statements, grab results
local x_response, controls_response, restart_response, exit_response = c:sendList(statements)

-- Send results to the appropriate functions
local xType, x = c:get(x_response)
c:setControls(controls_response)
c:checkRestart(restart_response)

console.writeline("x: " .. xType .. " " .. x)

-- Did the server tell us to exit?
if c:checkExit(exit_response) then break end
```

Since the server interprets a set of statements, we simply built a list of them and sent it using sendList(). sendList() will return the server's response to each statement in order, if they send a usable (non-empty) response. Statements UPDATE and SET give no response, and we expect no return. The only reason saveScreenshot() is sent separately is because of hard limitations in the Lua library of BizHawk. The reasoning behind sending a list rather than individual commands was to minimize total latency of sending and receiving messages which tends to build, especially given BizHawk's limitations. The server will interpret commands first-come first-serve just like ordinary code, therefore controls will be determined only after the UPDATE is requested.

Afterwards, the returns (server results) are sent from sendList() to their functions to interpret them.

Notice the updateStatement(). This tells the server to call its update() function, which does nothing until you implement it in your Python program. Be careful with this. You generally want to call an update before you receive any data from the server. If your machine learning model generates controls given a screenshot, you'll want to send the screenshot, then update, then grab the controls in that order.

You should now have an idea of how to write a Lua plugin that runs the game and commands the client by sending and receiving data. This sample file is included with additional functionality as SampleTool.lua. When run, it should print 'BHClient.lua loaded!' and continue running.

## Setting up BizHawk
BrainHawk was designed specifically for the most recent version of BizHawk (2.3). It likely will not work on older versions, and possibly newer versions.

Open EmuHawk.exe. Open the game (ROM) of your choice, and create a save state by clicking File -> Save State -> Save Named State... . Make as many as you want. Next, click Tools -> Lua Console. Click Open Script, and once your server is started and 'Ready', open the .lua file you created.

Searching for ROMs and save states begins at the parent folder of BizHawk.

If you want to pause the game or learning process at any time, click Emulation -> Pause. This will not break the server or client - it simply waits for you to unpause.

_**NOTE: BizHawk cannot send screenshots greater than an unknown size.**_ Somewhere around maybe 70k bytes, the BizHawk script which calls a screenshot will crash. This is an unfortunate limitation we cannot get past at the moment. To work around this, you'll have to change your rendering settings. In particular, you'll want to change your resolution to somewhere less than 160x120 for N64, though 160x120 works most of the time. You'll have to experiment. The more 'complex' a picture is, the more space it will take up when compressed. Therefore, although you may get past the loading screen at higher resolutions, expect a crash once you begin the game.

## Server Data
Server data types are based off of Python's data types. Few are supported:
* INT
* BOOL
* STRING
* INT[]
* BOOL[]
* STRING[]

The server's 'data' variable stores a dictionary of the form ```{var, (type, val)}```. The client can directly store variables and access them inside.

There are other variables outside of the data variable, all handled with their own server functions. There are two types.

### READABLE from Client
Dictionaries:
* screenshots - Stores screenshots from *current* episode
* controls - Controls to be sent to emulator
Strings:
* rom - Path to ROM (from parent of BizHawk directory)
* save - Path to current savestate (from parent of BizHawk directory)
Integers:
* update_interval - Number of frames between calls from client to server (through update() function)
* speed - Emulation speed percentage of emulator. Maximum 6399. Higher percentages will speed up learning drastically.
* frameskip - Frameskip of emulator
Booleans:
* exit - Whether client should exit. Sets to False after being read from client.
* restart - Whether client should restart (load save state). When read, sets to False.
* sound - Emulation sound
* guessed - Whether controls were determined randomly. 

### Server Access Only
* episodes - Number of episodes *COMPLETED*
* actions - Number of actions (updates) called from client
* client_started_flag - Whether emulator just started. Should be accessed ONLY from client_started(), which automatically sets to False after.
* use_grayscale - When True, will save screenshots in grayscale
* saves - Holds save states and their probabilities. ```{"path": prob}```

## Server Functions
Client interaction functions:
* update() - Called using client's UPDATE statement. You should replace this in your Python tool to synchronize handling of newly submitted data (e.g. screenshots), and updating variables (e.g. controls) the client will request next.
* reset_data() - Resets all data to defaults, allowing a new client to connect.
* exit_client() - Tells client to exit.
* client_started() - Whether client just connected and called initial RESET. Returns False until next RESET.
* new_episode() - Starts a new episode: asks client to reset
* load_save() - Loads a save probabilistically into 'save' for next emulator reset/episode

Data exportation functions:
* save_screenshots(start, end, name) - Saves a range of screenshots to disk from screenshots dictionary (including end index)
* show_screenshot(idx) - Previews a screenshot in screenshots dictionary using pyplot. Note: pyplot should be run from the main thread, NOT through the server's update() function.

## Client Functions

Most of the client's functions offer a 'statement' alternative. These statements can be compiled into a list and sent using the 'sendList' function. This minimizes unnecessary hang times by sending/receiving all data to and from the server in one message.

### Emulator functions
* timeToUpdate() - Returns whether it's time to update to server (frames == updateInterval).
* advanceFrame() - Plays a single frame of the game.
* newEpisode() - Resets emu to base state (load save, resets data). Called automatically by checkRestart()

### Server interaction functions
Initialization functions:
* initialize() - Prepares emulator and loads initialization data from server using all initialization functions.
* loadRom() - Loads the rom from server.
* setUpdateInterval(rsp) - Sets update interval from server.
* setUpdateIntervalStatement() 
* setSound(rsp) - Sets whether sound is enabled from server
* setSoundStatement()
* setSpeed(rsp) - Sets emulation speed percentage from server.
* setSpeedStatement()
* setFrameskip(rsp) - Sets frameskip from server.
* setFrameskipStatement()

Thing:
* sendList(list) - Sends a list of statements to the server. Returns each server response individually. If the statement merits no response (SET, UPDATE, RESET), nothing is returned. The server responses should be passed to their respective functions (named after their statements).
* updateStatement() - Statement for calling server's UPDATE function.
* checkRestart(rsp) - Restarts emulator if server asked to restart (calls newEpisode()).
* checkRestartStatement()
* checkExit(rsp) - Returns server's 'exit' function.
* checkExitStatement()
* saveScreenshot() - Stores screenshot of game on server. No statement. Must be called on it's own due to BizHawk's implementation.
* setControls(rsp) - Sets controls from server.
* setControlsStatement()
* setSave(rsp) - Sets save state from server.
* setSaveStatement()

User data functions:
* get(rsp) - Gets a variable (data_type, value) from inside or outside server's data.
* getStatement(var) - Requires variable name.
* setStatement(var, val, type) - Statement for setting a variable on server's data. Requires name, value, and data_type. 
* getListElem(rsp) - Gets an element of a list in server's data.
* getListElemStatement(list, idx) - Requires name and index.

## Server Message Syntax
Sending custom TCP messages to the server is largely unnecessary since their functions are already implemented in the Lua client. However, for extended functionality, or for implementing functionality in a different language, here is the syntax:

For retrieving any variable (and its type):
* `GET var`
* If the variable does not exist, will return "None"
* Returns the type, followed by a space, followed by the value

For setting a defined variable:
* `SET var val`
* val is expected to be interpretable as the appropriate data type. Therefore, an Int could be set to -143, but not a string.

For setting a user-defined variable (not list):
* `SET var type val`

For setting a user-defined variable (list):
* `SET var type[] val [e1, e2, ...]`
* Every element in the list must be specified, as well as the list type
