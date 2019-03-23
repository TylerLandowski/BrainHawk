# -*- coding: utf-8 -*-

"""
@author: Tyler Landowski
"""

# TODO self.actions incremented after update() instead of screenshot(). Check if stable
# TODO Check if sample tool code increments episodes correctly (new_episode, exit_client)

# TODO Test syntax in Lua
# TODO Save server data to disk (just screenshots?). Autosave?
# TODO Does self.socket break multithreading?
# TODO Public, private, protected

# TODO Semicolons in message statements?
# TODO Reveal screenshot memory size
# TODO ?    Allow endless screenshots, not terminated by episode
# TODO Check if self.close_client breaks threading, rewrite it
# TODO Stricter RegEx's and patterns
# TODO Fix screenshot encoding, showing b'tretre' in lua
# TODO Allow pausing and resuming learning, saving progress
# TODO Fix naming conventions, check for lower/uppercase strictness
# TODO Typecast set requests of lists and dictionaries
# TODO Fix setting a previously defined variable as non-list, etc.
# TODO Use unquote instead of .replace()
# TODO Allow save states from files
# TODO Support more data types: float, dict, lists
# TODO Convert screenshot from dict to list
# TODO Check for pointer safety - did we overwrite any variable once passed to a function?

import sys
import socket as s  # Allows data connections to clients
import threading  # Allows multiple connections simultaneously
import re  # Pattern-matching messages using regular expressions
import ast  # Interpretting string representations of lists and ints
import numpy as np  # For probability selection
from urllib.parse import unquote, unquote_plus  # Decoding url-safe HTTP requests
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
            # -------------
            # Data Settings
            # -------------
            # Not yet implemented
            mode = "HUMAN",  # Used for recording human input to emulator
            # Store screenshots as grayscale
            use_grayscale = False,
            # System being emulated. Sets initial controls dictionary
            system = "N64",
            # ---------------
            # Client Settings
            # ---------------
            # Frames to wait before emulator sends/receives data. Used by emu client
            update_interval = 5,
            # Frameskip used by emu
            frameskip = 1,
            # Game sound on?
            sound = False,
            # Emulation speed percentage. Higher values train models faster. Max = 6399
            speed = 6399,
            # ROM game file
            rom = "",
            # Dictionary of save states and their probabilities
            saves = dict(),
    ):

        # --------------------
        # Server-Readable Only
        # --------------------
        # Socket
        self.ip = ip        # Address to host server on
        self.port = port    # Port to host server on
        self.socket = None  # Server socket
        # Misc
        self.logging = False       # Print auxiliary messages to console for debugging
        self.close_client = False  # Closes client after message has been received
        # Learning
        self.episodes = 0  # Number of COMPLETED episodes. Incremented by new_episode and exit_client
        self.actions = 0   # Actions taken during the current episode (number of UPDATEs called)
        # Emulator status
        self.client_started_flag = False  # Did the client just call START? Access ONLY by client_started()
        # Data Management
        self.use_grayscale = use_grayscale  # Store screenshots as grayscale
        self.saves = saves  # Dictionary of save states and their probabilities {"path": prob}
        # ---------------------------
        # Client-Accessible Variables
        # ---------------------------
        # Emulator Initialization
        self.frameskip = frameskip  # Frameskip used by emu
        self.sound = sound  # Turns sound on
        self.speed = speed  # Emulation speed percentage. Higher values train models faster
        self.rom = rom      # ROM game file
        self.update_interval = update_interval  # Frames to wait before emulator sends/receives data
        # Emulator Controls
        self.restart = False  # Tells emu to restart. Set to False after value is requested
        self.exit = False     # Tells client to exit.
        self.save = ""        # Path to the current save file (from parent of BizHawk dir). Updated with load_save()
        self.controls = {}    # Controls dict to be passed to emulator, or received from emulator if recording
        # Client-Settable
        self.data = dict()         # Stores {VAR: (DATATYPE, VAL)}. Utilized by SET and GET statements from clients
        self.screenshots = dict()  # Stores screenshots as numpy.ndarrays
        # Misc
        self.guessed = False  # Last action was picked randomly?

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

    #
    # Socket / Server Status Functions
    #

    # Prints the given message
    def log(self, msg):
        if self.logging: print(msg)

    # Connects the client and handles its message(s)
    def handle_client_connection(self, client_socket):
        try:
            while True:
                msg = client_socket.recv(self.BUFSIZE)
                if not msg: break
                self.log('Received {}'.format(msg))
                self.close_client = False
                self.handle_msg(msg.decode("utf-8"), client_socket)
                if self.close_client: break
        finally:
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

    #
    # Client/Data Functions
    #

    # Called after every received "UPDATE" statement.
    # Replace this with your code.
    def update(self):
        print("ERROR: Update called, but not implemented")

    # Returns whether the client just called START. If True is returned, will return False until client starts again
    def client_started(self):
        started = self.client_started_flag
        self.client_started_flag = False
        return started

    # Starts a new episode of learning
    def new_episode(self):
        # NOTE: load_save() should also be called before update() is finished,
        self.restart = True  # Tell the emulator to restart
        self.actions = 0
        self.episodes = self.episodes + 1

    # Cleans the server to resume learning
    # The server will not have to restart every time the client restarts if client calls "RESET" upon starting
    def reset_data(self):
        self.actions = 0
        self.episodes = 0
        self.screenshots = dict()
        self.data = dict()
        self.client_started_flag = True
        self.log("Initialized data to defaults")

    # Requests that the client stop and disconnect
    def exit_client(self):
        self.episodes = self.episodes + 1  # Mark another completed episode
        self.exit = True

    # Loads a save state probabilistically using the self.saves, stores in self.save for client to read.
    def load_save(self):
        self.save = np.random.choice(
            a = list(self.saves.keys()),
            size = 1,
            # Convert values into probabilities if not already
            p = list(v / sum(self.saves.values()) for v in self.saves.values())
        )[0]

    #
    # Data Exportation Functions
    #

    # TODO Does this work?
    # Saves a range of screenshots to disk from screenshots dictionary
    def save_screenshots(self, start, end, name):
        for idx in range(start, end + 1):
            plt.imsave(name, self.screenshots[idx])

    # Previews an image of the screenshot at index idx
    # NOTE: Must be called from main thread, NOT from update()
    def show_screenshot(self, idx):
        scrot = self.screenshots[idx]
        plt.imshow(scrot)
        plt.show()

    #
    # Message Reading Functions
    #

    # Handle a message of a list of statements from a client
    def handle_msg(self, msg, client_socket):
        # NOTE: msg is url-safe. It is NOT decoded unless needed

        # * A msg can begin with "UPDATE", "RESET", "GET", "SET", "POST".
        # * Every msg can hold multiple statements separated by '; ' FIXME
        # * An UPDATE will call self.update(). This is useful for when the emu is ready to receive new controls, or needs to check whether or not to reset
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
                # Handle RESET request
                #

                if stmt.startswith("RESET"):
                    # Reset variables
                    self.reset_data()

                #
                # Handle UPDATE request
                #

                elif stmt.startswith("UPDATE"):
                    self.actions += 1
                    self.update()

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

                    # Dictionaries
                    if var.startswith("screenshots "): response += self.screenshots[int(var[11:])].decode("utf-8")
                    elif var == "controls":            response += dict_as_str(self.controls)
                    # Strings
                    elif var == "rom":                 response += self.rom
                    elif var == "save":                response += self.save
                    # Integers
                    elif var == "update_interval":     response += str(self.update_interval)
                    elif var == "speed":               response += str(self.speed)
                    elif var == "frameskip":           response += str(self.frameskip)
                    # Booleans
                    elif var == "exit":
                        response += str(self.exit)
                        self.exit = False
                    elif var == "restart":
                        response += str(self.restart)
                        self.restart = False
                    elif var == "sound":               response += str(self.sound)
                    elif var == "guessed":             response += str(self.guessed)

                    #
                    # Handle variable requests inside self.data
                    #

                    else:
                        splt = var.split(' ')

                        # Are we getting the element of a list?
                        if len(splt) == 2:
                            var = splt[0]
                            idx = int(splt[1])

                            # Does the list not exist?
                            if self.data.get(var) is None:
                                response += "None"

                            else:
                                lst = self.data[var][1]

                                # Does the element exist?
                                if idx >= len(lst) or idx < -1 * len(lst):
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
                                # Send response, formatted based on data type
                                if val[0] == "DICT": response += dict_as_str(val[1])
                                else:                response += val[0] + " " + str(val[1])

                #
                # Handle SET request
                #

                elif stmt.startswith("SET"):
                    self.log("SET requested...")

                    # Setting variable:
                    # 	SET name type val
                    # Setting list:
                    # 	SET name type[] []
                    # Setting list element value:
                    # 	SET name idx val

                    match = re.match(r"SET (.*)", stmt, re.I)
                    after_set = match.group(1)

                    #
                    # Handle variable requests outside self.data
                    #

                    # Dictionaries
                    if after_set.startswith("screenshots"):
                        print("ERROR: screenshots is read only")
                    elif after_set.startswith("controls"):
                        print("ERROR: controls is read only")
                    # Strings
                    elif after_set.startswith("rom"):
                        print("ERROR: rom is read only")
                    elif after_set.startswith("save"):
                        print("ERROR: save is read only")
                    # Integers
                    elif after_set.startswith("update_interval"):
                        print("ERROR: update_interval is read only")
                    elif after_set.startswith("actions"):
                        print("ERROR: actions is read only")
                    elif after_set.startswith("speed"):
                        print("ERROR: speed is read only")
                    elif after_set.startswith("frameskip"):
                        print("ERROR: frameskip is read only")
                    # Booleans
                    elif after_set.startswith("exit"):
                        print("ERROR: exit is read only")
                    elif after_set.startswith("restart"):
                        self.restart = after_set[8:]
                    elif after_set.startswith("sound"):
                        print("ERROR: sound is read only")
                    elif after_set.startswith("guessed"):
                        print("ERROR: guessed is read only")

                    #
                    # Handle variable requests inside self.data
                    #

                    else:
                        match = re.match(r"([^ ]*) ([^ ]*) (.*)", match.group(1), re.I)

                        var = match.group(1)
                        val = match.group(3)
                        existing_var = self.data.get(var)

                        has_idx = False

                        # Are we setting a list element?
                        if match.group(2)[0].isdigit():
                            has_idx = True
                            idx = int(match.group(2))

                            # Does the variable exist?
                            if existing_var is None:
                                print("ERROR: Attempt to index non-existent list " + var)
                                return

                            data_type = existing_var[0]

                        # Are we setting a variable?
                        else: data_type = match.group(2)

                        # Convert the value according to the datatype
                        if data_type.startswith("INT") or data_type.startswith("BOOL") or data_type.startswith("STRING"):
                            try:
                                val = ast.literal_eval(val)
                            except:
                                print(val)
                                print("ERROR: Data value does not match datatype")
                                return
                        # TODO Check if BOOL when INT, INT when BOOL,
                        # TODO INT inside BOOL list, BOOL inside INT list
                        else:
                            print("ERROR: Unrecognized datatype " + data_type)
                            return

                        # Are we working on a list?
                        if data_type.endswith("[]"):
                            if not isinstance(val, list) and not has_idx:
                                print("ERROR: List initialization value does not match datatype")
                                return

                            # Are we initializing a new list?
                            if existing_var is None and not has_idx:
                                self.data[var] = (data_type, val)

                            # Are we setting a list element or re-initializing the list?
                            else:
                                # Are we given a data type rather than an index?
                                if not has_idx:
                                    # Re-initialize the list
                                    self.data[var] = (data_type, val)
                                else:
                                    lst = existing_var[1]

                                    # Are we setting an existing element, or appending a new one?
                                    if idx < len(lst):    lst[idx] = val
                                    elif idx == len(lst): lst.append(val)

                                    # Throw an error
                                    else:
                                        print("ERROR: List " + var + "[" + str(idx) + "]" + " index out of range")
                                        return

                        # Are we setting a non-list variable?
                        else:
                            self.data[var] = (data_type, val)

                #
                # Handle POST requests (from BizHawk's comm.http* functions)
                #

                elif stmt.startswith("POST"):
                    # 68,859

                    response = "HTTP/1.1 200 OK\r\n\r\n"
                    self.close_client = True  # BizHawk expects connection to close after each Lua method call

                    # Check the size of the body
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

                        # Store screenshot as numpy.ndarray (replace if already exists)
                        img = base64.b64decode(unquote_plus(screenshot))  # Using unquote because urlsafe_ doesn't work
                        img = mpimg.imread(io.BytesIO(img), format = 'png')
                        if self.use_grayscale:
                            img = to_grayscale(img)
                        self.screenshots[self.actions] = img

                    # Assume this is an HTTP-formatted POST command
                    else:
                        match = re.match(".*payload=(.*)", msg, re.S)
                        msg = unquote_plus(match.group(1))

                        # Re-iterate. handling body as new message
                        new_msg = True

                # Did the statement return a response?
                if returns: response += "; "

                # Ignore any other statements (though there shouldn't be any more)
                if new_msg: break

        # Send back the response. Remove final separator
        if response.endswith("; "): client_socket.send(response.encode("utf-8")[:-2])
        else:                       client_socket.send(response.encode("utf-8"))

    #
    # Auxilliary Static Functions
    #

    @staticmethod
    # Crop the image, given decimal percentages
    def crop_percent(img, top, left, bottom, right):
        y1 = int(top * img.shape[0])
        x1 = int(left * img.shape[1])
        y2 = int(img.shape[0] - (bottom * img.shape[0]))
        x2 = int(img.shape[1] - (right * img.shape[1]))
        return img[y1:y2, x1:x2]

    @staticmethod
    # Returns a discrete dict that maps an int to a discrete list of controls
    def make_action_map(actions):
        action_map = []
        BHServer.__mam_h(0, {}, actions, action_map)
        return action_map

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
    # Returns a discrete list [0, 1, 2, .., n], where n = len(action_map)
    def make_action_space(action_map):
        action_space = []
        for i in range(len(action_map)):
            action_space.append(i)
        return action_space
