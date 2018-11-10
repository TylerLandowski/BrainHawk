# BrainHawk

## What is BrainHawk?
BrainHawk allows you to host a server (in Python) as well as a client (in BizHawk) to communicate data in an easy way, particularly for machine learning. The focus is to avoid Lua scripting as much as possible. 

## BHServer.py
The primary role of the server is to store data. It's capable of interpretting simple commands from a client, particularly to set or send data. 

## Writing a tool with BHServer.py
TODO

## BHClient.lua
The primary role of the client is to play the game while sending data (e.g. screenshots and other data) to the server, and receiving instructions back (e.g. controls to use, emulator commands, and reset statements).

## Writing a tool with BHClient.lua
First, we need to import, instantiate, and initialize the client.
The initialize() function retrieves initial settings for playing from the server, including:
* How often (in frames) to communicate with the server
* How fast to play the game
* Game's slot for save-state
* more

```lua
require("./BHClient")
c = DLSClient:new("http://127.0.0.1:1337")
c:initialize()
```

The loop that runs along with the game is defined here. We'll assume you want to use controls from the server, and only communicate with the server every so many frames. useControls() must be called before every frame, since controls are reset continuously.

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
