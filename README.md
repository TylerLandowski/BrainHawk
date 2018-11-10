# BrainHawk

## What is BrainHawk?
BrainHawk allows you to host a server (in Python) as well as a client (in BizHawk) to communicate data in an easy way, particularly for machine learning. The focus is to avoid Lua scripting as much as possible. 

## BHServer.py
The primary role of the server is to store data. It's capable of interpretting simple commands from a client, particularly to set or send data. 



## BHClient.lua
The primary role of the client is to play the game while sending data (e.g. screenshots and other data) to the server, and receiving instructions back (e.g. controls to use, emulator commands, and reset statements).

## Server Message Syntax
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
