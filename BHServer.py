# -*- coding: utf-8 -*-

"""
@author: Tyler Landowski
"""

# TODO Allow loading ROM through name
# TODO Does self.socket break multithreading?
# TODO Public, private, protected
# TODO Return nil instead of None
# TODO Continuous input
# TODO Have sendStr return formatted data
# TODO Allow recording of humans
# TODO Autosave server data
# TODO Try multiple clients
# TODO Save CSV of debugging information

# TODO Stop things from breaking when emulator restarts?
# TODO Allow discluding variables from saving in DQN
# TODO Allow screenshot saving
# TODO Allow adjustment of screenshot resolution
# TODO Reveal screenshot memory size
# TODO ?    Allow endless screenshots, not terminated by episode
# TODO Check if self.close breaks threading, rewrite it
# TODO Stricter RegEx's and patterns
# TODO Fix screenshot encoding, showing b'tretre' in lua
# TODO Allow pausing and resuming learning, saving progress
# TODO Instructions
# TODO Fix naming conventions, check for lower/uppercase strictness
# TODO Rename BizHawk to Emulator
# TODO Typecast set requests of lists and dictionaries
# TODO Fix setting a previously defined variable as non-list, etc.
# TODO Use unquote instead of .replace()
# TODO Allow save states from files
# TODO Support more data types: float, dict, lists
# TODO Convert screenshot from dict to list
# TODO Check for pointer safety - did we overwrite any variable once passed to a function?

import socket as s  # Allows data connections to clients
import threading  # Allows multiple connections simultaneously
import re  # Pattern-matching messages using regular expressions
import ast  # Interpretting string representations of lists and ints
import numpy as np  # For probability selection
from urllib.parse import unquote  # Decoding url-safe screenshot strings from HTTP requests
import base64  # Decoding Base64 screenshot strings
import io  # Decodes Base64 to bytes
import matplotlib.image as mpimg  # Loading numpy.ndarray from PNG bytes
import matplotlib.pyplot as plt  # Visualizing screenshots


# Convert string representation of bool to bool
def to_bool(str):
	return True if str == "True" else False


# Returns a string representation of the dictionary
def dict_as_str(dict):
	string = ""

	for key, val in dict.items():
		string += ',' + key + ":" + str(val)

	return string[1:]


# Converts numpy.ndarray to grayscale
def to_grayscale(img):
	return 0.2989 * img[:, :, 0] + 0.5870 * img[:, :, 1] + 0.1140 * img[:, :, 2]


class BHServer:
	BUFSIZE = 38500

	def __init__(
			self,
			# ---------------
			# Server Settings
			# ---------------
			# Address to host server on
			ip = "127.0.0.1",
			# Port to host server on
			port = 1337,
			# Print auxiliary messages to console for debugging
			logging = False,
			# -------------
			# Data Settings
			# -------------
			mode = "HUMAN",
			# Frames to wait before emulator sends/receives data. Used by emu client
			update_interval = 5,
			# Store screenshots as grayscale FIXME
			use_grayscale = False,
			# System being emulated. Sets initial controls dictionary
			system = "N64",
			# -----------------
			# Emulator Settings
			# -----------------
			# Frameskip used by emu
			frameskip = 1,
			# Turns sound on
			sound = False,
			# Emulation speed percentage. Higher values train models faster. Max = 6399
			speed = 6399,
			# Dictionary of save states and their probabilities
			saves = {},
	):
		self.ip = ip  # Address to host server on
		self.port = port  # Port to host server on
		self.logging = logging  # Print auxiliary messages to console for debugging
		self.update_interval = update_interval  # Frames to wait before emulator sends/receives data
		self.use_grayscale = use_grayscale  # Store screenshots as grayscale
		self.frameskip = frameskip  # Frameskip used by emu
		self.sound = sound  # Turns sound on
		self.speed = speed  # Emulation speed percentage. Higher values train models faster
		self.saves = saves  # Dictionary of save states and their probabilities
			# Each save state will be loaded probabilistically
			# "PathToFile": Probability
		self.save = ""  # Path to the current save file. Updated with load_save()
		self.socket = None  # Server socket
		self.data = {}  # Stores {VAR: (DATATYPE, VAL)}. Utilized by SET and GET statements from clients.
		self.actions = 0  # Actions taken during the current episode
		self.screenshots = {}  # Stores screenshots as numpy.ndarrays
		self.restart = False  # Tells emu to restart. Set to False by client once emu has restarted
		self.controls = {}  # Controls dict to be passed to emulator, or received from emulator if recording
		self.close = False  # Closes client after message has been received
		self.guessed = True  # Last action was picked randomly

		self.load_save()  # Set initial save

		if system == "N64":
			self.controls = {
				"P1 A": False,
				"P1 A Down": False,
				"P1 A Left": False,
				"P1 A Right": False,
				"P1 A Up": False,
				"P1 B": False,
				"P1 C Down": False,
				"P1 C Left": False,
				"P1 C Right": False,
				"P1 C Up": False,
				"P1 DPad D": False,
				"P1 DPad L": False,
				"P1 DPad R": False,
				"P1 DPad U": False,
				"P1 L": False,
				"P1 R": False,
				"P1 Start": False,
				"P1 X Axis": 0,  # [-128, 127]
				"P1 Y Axis": 0,  # [-128, 127]
				"P1 Z": False,
				"Power": False,
				"Reset": False,
			}

		elif system == "NES":
			self.controls = {
				"P1 A": False,
				"P1 B": False,
				"P1 Down": False,
				"P1 Left": False,
				"P1 Right": False,
				"P1 Select": False,
				"P1 Start": False,
				"P1 Up": False,
				"Power": False,
				"Reset": False
			}

	# Prints the given message
	def log(self, msg):
		if self.logging: print(msg)

	# Called after every received "UPDATE" statement.
	# Replace this with your code.
	def update(self):
		pass

	# TODO
	def restart_episode(self):
		# NOTE: load_save() should also be called before update() is finished,
		#       OR save should be set to an appropriate path
		self.restart = True  # Tell the emulator to restart
		self.actions = 0

	# Connects the client and handles its message(s)
	def handle_client_connection(self, client_socket):
		while True:
			msg = client_socket.recv(self.BUFSIZE)
			if not msg: break
			self.log('Received {}'.format(msg))
			self.close = False
			self.handle_msg(msg.decode("utf-8"), client_socket)
			if self.close: break
		self.log("Client disconnected.")
		client_socket.close()

	# Checks for client connections
	def run(self):
		self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
		self.socket.bind((self.ip, self.port))
		self.socket.listen(5)
		self.log("Listening on {}:{}.".format(self.ip, self.port))
		while True:
			client_socket, address = self.socket.accept()
			self.log('Accepted connection from {}:{}'.format(address[0], address[1]))
			client_handler = threading.Thread(
				target = self.handle_client_connection,
				args = (client_socket,)
			)
			client_handler.start()

	# Starts the server, listens for clients
	def start(self):
		client_handler = threading.Thread(target = self.run)
		client_handler.start()

	# Stops the server
	def stop(self):
		self.socket.close()
		self.log("Server stopped.")
	
	def handle_msg(self, msg, client_socket):
		# * A msg can begin with "UPDATE", "SAVE", "GET", "SET", "POST".
		# * Every msg can hold multiple statements separated by '; ' FIXME
		# * An UPDATE will call self.update(). This is useful for when the emu is ready to receive new controls, or needs to check whether or not to reset
		# * A SAVE will FIXME
		# * A POST is simply an HTTP POST request
		#   It is utilized by two BizHawk lua methods:
		#   -comm.httpPost(), which sends a POST-formatted message, where we put all statements at the end (after "payload=")
		#   -comm.httpPostScreenshot(), which sends a POST-formatted message, where screenshot is sent as BASE64 string at the end (after "screenshot=")
		#   The functions may sometimes send messages without the data, i.e. ending in \r\n\r\n. The next message will include only the rest of the message.
		#   HTTP requests are encoded to be URL-safe
		#   Every POST must be responded to with an HTTP-formatted response, including messages split into 2 requests
		# * A GET grabs the datatype and value of a variable inside self.data, or just the value if outside self.data
		#   It does not interpret HTTP GET requests.
		#   All statements except for the last will be responded to with a single message, hold a number of responses seperated by '; '
		#   If a variable does not exist, or the requested index of a list does not exist, the response will be "None"
		# * A SET sets the value and datatype of a variable inside self.data, or just the value if outside of self.data
		#   A self.data variable can be set with SET NAME TYPE VAL
		#   A variable outside self.data can be set with SET NAME VAL
		#   A list must be initialized with SET NAME TYPE[] [ELEMENTS]
		#   A list element can be set using SET NAME IDX VAL. You can only set an element at an existing position, or append an element by using the index equal to the list size

		#
		# Handle every statement inside msg
		#

		new_msg = True  # Indicates whether msg's value has changed (i.e. any POST with payload)
		response = ""   # Response to the current statement

		# Iterate over every collection of statements
		while new_msg:
			new_msg = False

			# Iterate over every statement inside the msg
			for stmt in msg.split("; "):
				returns = False  # Indicates whether the statement returns anything

				#
				# Handle UPDATE request
				#

				if stmt.startswith("UPDATE"): self.update()

				#
				# Handle SAVE request
				#

				elif stmt.startswith("SAVE"):
					returns = False
					variables = stmt[5:].split()
					dictionary = {}

					for var in variables:
						# FIXME
						if var == "screenshots": dictionary[var] = self.screenshots
						else: dictionary[var] = self.data[var]

				#
				# Handle GET request
				#

				elif stmt.startswith("GET"):
					self.log("GET requested...")
					returns = True
					match = re.match(r"GET (.*)", stmt, re.I)
					var = match.group(1)

					#
					# Handle variable requests outside of self.data
					#

					if var.startswith("screenshot "): response += self.screenshots[int(var[11:])].decode("utf-8")
					elif var == "controls":           response += dict_as_str(self.controls)
					# Strings
					elif var == "save":               response += self.save
					# Integers
					elif var == "update_interval":    response += str(self.update_interval)
					elif var == "actions":            response += str(self.actions)
					elif var == "speed":              response += str(self.speed)
					elif var == "frameskip":          response += str(self.frameskip)
					# Booleans
					elif var == "restart":            response += str(self.restart)
					elif var == "sound":              response += str(self.sound)
					elif var == "guessed":            response += str(self.guessed)

					#
					# Handle variable requests inside self.data
					#

					else:
						splt = var.split(' ')

						# Are we getting the element of a list?
						if len(splt) == 2:
							var = splt[0]
							idx = int(splt[1])

							# Does the list exist?
							if self.data.get(var) is None:
								response += "None"

							else:
								lst = self.data[var][1]

								# Does the element exist?
								if idx >= len(lst):
									response += "None"

								# Return the list element
								else:
									response += str(lst[idx])

						# Are we getting the value of a variable?
						else:
							val = self.data.get(var)

							# Does the variable not exist?
							if val is None: response += "None"

							else:
								#
								# Send response, formatted based on data type
								#

								if val[0] == "DICT": response += dict_as_str(val[1])
								else:                response += val[0] + " " + str(val[1])

				#
				# Handle SET request
				#

				elif stmt.startswith("SET"):
					self.log("SET requested...")

					# SET arr INT[] []
					# SET arr 1 54398
					# SET x INT 5

					match = re.match(r"SET (.*)", stmt, re.I)
					after_set = match.group(1)

					#
					# Handle variable requests outside self.data TODO
					#

					if after_set.startswith("screenshot"):
						pass  # FIXME
					elif after_set.startswith("controls"):
						pass  # FIXME
					elif after_set.startswith("restart"):
						self.restart = to_bool(after_set[10:])
					elif after_set.startswith("update_interval"):
						self.update_interval = after_set[16:]

					#
					# Handle variable requests inside self.data
					#

					else:
						match = re.match(r"([^ ]*) ([^ ]*) (.*)", match.group(1), re.I)

						var = match.group(1)
						val = match.group(3)
						existing_var = self.data.get(var)

						# Are we setting a list element?
						if match.group(2)[0].isdigit():
							idx = int(match.group(2))

							# Does the variable exist? FIXME
							if existing_var is None:
								print("ERROR: Attempt to index a non-existent list")

							data_type = existing_var[0]

						# Are we setting a variable?
						else: data_type = match.group(2)

						# Convert the value according to the datatype
						if data_type.startswith("INT") or data_type.startswith("BOOL"):
							val = ast.literal_eval(val)

						# Are we working on a list?
						if data_type.endswith("[]"):
							# Are we initializing a new list?
							if existing_var is None: self.data[var] = (data_type, val)

							# Are we setting a list element
							else:
								lst = existing_var[1]

								# Are we setting an existing element, or appending a new one?
								if idx < len(lst):    lst[idx] = val
								elif idx == len(lst): lst.append(val)

								# Throw an error FIXME
								else:
									print("ERROR: List index out of range")

						# Are we setting a non-list variable?
						else:
							self.data[var] = (data_type, val)

				#
				# Handle POST requests (from BizHawk's comm.http* functions)
				#

				elif stmt.startswith("POST"):
					# 68,859, 38,400
					# 39655, 49835
					response = "HTTP/1.1 200 OK\r\n\r\n"
					self.close = True  # BizHawk expects connection to close after each Lua method call

					# Check the size of the body TODO Check speed of RegEx, optimize
					match = re.match(".*Content-Length: (\d*).*", stmt, re.S)
					cont_len = int(match.group(1))
					self.log("CONTENT_LENGTH: " + str(cont_len))

					# Should we expect the body in a new message directly after this one?
					if stmt.endswith("\r\n\r\n"):
						# Respond, to get the next message
						client_socket.send(response.encode("utf-8"))

						# Receive next message, replace old msg
						msg = client_socket.recv(cont_len).decode()

					# Check if message is screenshot
					screenshot_idx = msg[0:180].find("screenshot=")

					# Is this a screenshot?
					if screenshot_idx != -1:
						screenshot = msg[screenshot_idx + 11:]

						# Receive messages until msg size equals Content-Length
						while len(screenshot.encode("utf-8")) + 11 < cont_len:
							# Receive next msg
							msg = client_socket.recv(cont_len).decode()
							screenshot += msg

						# Store screenshot as numpy.ndarray
						img = base64.b64decode(unquote(screenshot))  # Using unquote because urlsafe_ doesn't work
						img = mpimg.imread(io.BytesIO(img), format = 'png')
						if self.use_grayscale:
							img = to_grayscale(img)
						self.screenshots[self.actions] = img
						self.actions += 1

					# Assume this is an HTTP-formatted POST command
					else:
						match = re.match(".*payload=(.*)", msg, re.S)
						msg = match.group(1)\
							.replace('+', ' ')\
							.replace('%3B', ';')\
							.replace('%5B', '[')\
							.replace('%5D', ']')\
							.replace('%2C', ',')

						# Re-iterate. handling body as new message
						new_msg = True

				# Did the statement return a response?
				if returns: response += "; "

				# Ignore any other statements (though there shouldn't be any more)
				if new_msg: break

		# Send back the response. Remove final separator
		if response.endswith("; "): client_socket.send(response.encode("utf-8")[:-2])
		else:                       client_socket.send(response.encode("utf-8"))

	# Loads a save state probabilistically using the self.saves
	def load_save(self):
		self.save = np.random.choice(
			a = list(self.saves.keys()),
			size = 1,
			# Convert values into probabilities if not already
			p = list(v/sum(self.saves.values()) for v in self.saves.values())
		)[0]

	# Previews an image of the screenshot at index idx
	def show_screenshot(self, idx):
		scrot = self.screenshots[idx]
		print(scrot)
		print(scrot.shape)
		i = base64.b64decode(scrot)
		i = io.BytesIO(i)
		i = mpimg.imread(i, format = 'png')
		plt.imshow(i)
		plt.show()

	@staticmethod
	# Crop the image, given decimal percentages
	def crop_percent(img, top, left, bottom, right):
		y1 = int(top * img.shape[0])
		x1 = int(left * img.shape[1])
		y2 = int(img.shape[0] - (bottom * img.shape[0]))
		x2 = int(img.shape[1] - (right * img.shape[1]))
		return img[y1:y2, x1:x2]

	@staticmethod
	# Helper recursive function for make_action_map()
	def __mam_h(i, action, actions, action_map):
		control = actions[i]
		for value in control[1]:
			action = action.copy()
			action[control[0]] = value

			if i == len(actions) - 1:
				action_map.append(action)
			else:
				BHServer.__mam_h(i + 1, action, actions, action_map)

	@staticmethod
	# Returns a discrete dict that maps an int to a discrete list of controls
	def make_action_map(actions):
		action_map = []
		BHServer.__mam_h(0, {}, actions, action_map)
		return action_map

	@staticmethod
	# Returns a discrete list [0, 1, 2, .., n], where n = len(action_map)
	def make_action_space(action_map):
		action_space = []
		for i in range(len(action_map)):
			action_space.append(i)
		return action_space
