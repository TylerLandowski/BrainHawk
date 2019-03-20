--
-- Author: Tyler Landowski
--

-- =====================================================================================================================
-- Constants
-- =====================================================================================================================

GREEN = 0x6600FF00
RED = 0x66FF0000

-- =====================================================================================================================
-- ?
-- =====================================================================================================================

BHClient = {}
BHClient.__index = BHClient

function BHClient:new (
    addr
)
    local self = {}
    setmetatable(self, BHClient)

    -- Address of the server
    self.addr = addr or "http://127.0.0.1:1337"
    -- Path to save state
    self.save = ""
    -- How many frames before BizHawk sends and receives data from server
    self.updateInterval = 20
    -- How many screenshots we've taken since the last episode
    self.numScreenshots = 0
    -- How many frames we've advanced since the last update
    self.frames = 0
    -- Controls to use until the next update
    self.controls = {}
    -- Whether the last action was guessed randomly
    self.guessed = true

    return self
end

-- =====================================================================================================================
-- General Useful Functions
-- =====================================================================================================================

--[[ Converts string-representation of a table to a table
     Input Format: "key:val,key:val,key:val" ]]
function BHClient:tableFromString (str)
    local table = {}
    
    for key, val in string.gmatch(str, "([^,]+):([^,]+)") do
        -- TODO Convert based on data type?
        table[key] = self:convertValue(val)
    end

    return table
end

--[[ Returns a list of statements to a delimited string
     Output Format: "s1; s2; s3" ]]
function BHClient:stringFromList (list)
    local str = ""

    for _, elem in pairs(list) do
        str = str .. elem .. "; "
    end

    return str:sub(1, -3)
end

--[[ Returns a boolean given a string representing a bool ]]
function BHClient:boolFromString (str)
    if str == "True" then
        return true
    elseif str == "False" then
        return false
    else
        return null
    end
end

--[[ Converts a value contained in a string to a guessed value ]]
function BHClient:convertValue(val)
    if val == "True" or val == "False" then
        return self:boolFromString(val)
    elseif tonumber(val) then
        return tonumber(val)
    else
        return val
    end
end

-- =====================================================================================================================
-- Emulator Functions
-- =====================================================================================================================

--[[ Applies the controls table for the current frame ]]
function BHClient:advanceFrame ()
    emu.frameadvance()
	self.frames = c.frames + 1
end

--[[ Applies the controls table for the current frame ]]
function BHClient:useControls ()
    joypad.set(self.controls)
    joypad.setanalog(self.controls)
end

--[[ Returns whether it's time to update the server. Resets self.frames ]]
function BHClient:checkForUpdate ()
    if self.frames == self.updateInterval then
        self.frames = 0
        return true
    else
        return false
    end
end

--[[ Colors the screen based on whether the last action was guessed randomly ]]
function BHClient:colorAction ()
    if self.guessed == true then
        gui.drawBox(0, 0, 20, 20, RED, RED)
    else
        gui.drawBox(0, 0, 20, 20, GREEN, GREEN)
    end
end

-- =====================================================================================================================
-- Server Interaction Functions
-- =====================================================================================================================

--[[ Sets the emu to base state (loads save, numScreenshots = 0) ]]
function BHClient:restartEpisode ()
    savestate.load("../" .. self.save)
    self.numScreenshots = 0
end

--[[ Sends string of statements to the server, returns each output as separate return ]]
function BHClient:sendStr (str)
    -- Send an HTTP post
    local response = comm.httpPost(self.addr, str)

    -- Grab the body of the response
    local headEnd = string.find(response, "\r\n\r\n")
    local rspStart = 0
    local rspEnd = string.len(response)
    if not (headEnd == nil) then
        rspStart = headEnd + 4
    end
    local msg = string.sub(response, rspStart, rspEnd)

    -- Split the msg into each statement response
    local returns = {}
    local i = 1
    for ret in string.gmatch(msg .. "; ", "(.-)(; )") do
        -- Add the return to our list
        returns[i] = ret
        i = i + 1
    end

    -- Return each statement response separately
    return unpack(returns)
end

--[[ Sends list of statements to the server, returns each output as separate return ]]
function BHClient:sendList (list)
    return self:sendStr(self:stringFromList(list))
end

--[[ Returns statement to call server's update() function ]]
function BHClient:updateStatement()
    return "UPDATE"
end

--[[ Returns statement to set a variable on server to value and datatype
     If no dataType is given, assume it to be a string. ]]
function BHClient:setStatement (var, val, dataType)
    if not dataType then
        return "SET " .. var .. " " .. val
    else
        return "SET " .. var .. " " .. dataType .. " " .. val
    end
end

--[[ Returns the data type and value of the variable, given the server's response]]
function BHClient:get (response)
    if not response then
        print("ERROR: No server response given to get()")
        return "None"
    end

    -- Does the variable exist?
    if response == "None" then
        return "None"
    end

    -- Split the response
    local dataType, val = string.match(response, "(%w+) (.+)")

    -- Were we given just a value?
    if not dataType then
        -- Guess the data type and convert
        return self:convertValue(response)
    end

    -- Convert the value based on the data type
    if dataType == "INT" then
        val = tonumber(val)
    elseif dataType == "BOOL" then
        val = bool:boolFromString(val)
    elseif dataType == "STRING" then
        print("Got here STRING")
    elseif dataType == "INT[]" then
        print("Got here INT[]")
        val = self:tableFromString(val)
    elseif dataType == "BOOL[]" then
        print("Got here BOOL[]")
        val = self:tableFromString(val)
    elseif dataType == "STRING[]" then
        print("Got here STRING[]")
        val = self:tableFromString(val)
    end

    return dataType, val
end

--[[ Returns statement for getting value of a variable from server ]]
function BHClient:getStatement (var)
    if var == "controls" then
        print("ERROR: Please use updateControls() to get controls")
        return null
    elseif var == "screenshot" then
        print("ERROR: Getting screenshots not supported")
        return null
    end

    return "GET " .. var
end

--[[ Returns value of a list's element, given a response from server ]]
function BHClient:getListElem (response)
    if not response then
        print("ERROR: No server response given to getListElem()")
        return null
    end

    -- Does the variable exist?
    if response == "None" then
        return "None"
    end

    -- Guess datatype and convert
    return self:convertValue(response)
end

--[[ Returns statement to get an element of a list at an index
     Server's response should be passed to getListElem() ]]
function BHClient:getListElemStatement (list, idx)
    -- Is the list outside data?
    if list == "controls" or list == "screenshot" then
        print("ERROR: List element grabbing from outside server's data not supported")
        return null
    elseif list == "restart" or list == "sound" or list == "guessed" or list == "update_interval" or list == "actions"
         or list == "speed" or list == "frameskip" or list == "save_slot" or list == "controls" or list == "screenshot" then
        print("ERROR: Attempt to index non-list " .. list)
        return null
    end

    return "GET " .. list .. " " .. str(idx)
end

--[[ Takes screenshot of game window, sends to server ]]
function BHClient:saveScreenshot ()
    comm.httpPostScreenshot()
    c.numScreenshots = c.numScreenshots + 1
end

--[[ Stores controls from server to controls table, given server's response ]]
function BHClient:updateControls (controls)
    if not controls then
        print("ERROR: No server response given to updateControls()")
        return null
    end

    self.controls = self:tableFromString(controls)
end

--[[ Returns statement for updateControls()
     Server's response should be passed to updateControls() ]]
function BHClient:updateControlsStatement()
    return "GET controls"
end

--[[ Checks if the episode should restart, given server's response
     If yes, load the save state and set numScreenshots = 0 ]]
function BHClient:checkRestart (restart)
    if not restart then
        print("ERROR: No server response given to checkRestart()")
        return
    end

    if restart == "True" then
        self:restartEpisode()
    elseif not restart == "False" then
        print("ERROR: Server malfunction when retrieving restart")
    end
end

--[[ Returns statement for checkRestart()
     Server's response should be passed to checkRestart() ]]
function BHClient:checkRestartStatement ()
    return "GET restart; SET restart False"
end

--[[ Updates the save state, given the server's response ]]
function BHClient:getSave (save)
    if not save then
        print("ERROR: No server response given to getSave()")
        return null
    end

    self.save = save
end

--[[ Returns statement for getSave()
     Server's response should be passed to getSave() ]]
function BHClient:getSaveStatement ()
    return "GET save"
end

--[[ Checks if the current controls were determined randomly ]]
function BHClient:checkGuessed (guessed)
    if not guessed then
        print("ERROR: No server response given to checkGuessed()")
        return
    end

    self.guessed = self:boolFromString(bool)
end

function BHClient:checkGuessedStatement ()
    return "GET guessed"
end

function BHClient:getSoundStatement ()
    return "GET sound"
end

function BHClient:getUpdateIntervalStatement ()
    return "GET update_interval"
end

function BHClient:getSpeedStatement ()
    return "GET speed"
end

function BHClient:getFrameskipStatement ()
    return "GET frameskip"
end

--[[ Loads BizHawk settings from the server. Sets the emu to the base state ]]
function BHClient:initialize ()
    comm.httpSetPostUrl(self.addr)

    -- Prepare list of statements
    local statements = {
        "RESET",  -- No return
        self:getSaveStatement(),
        self:getUpdateIntervalStatement(),
        self:getSoundStatement(),
        self:getSpeedStatement(),
        self:getFrameskipStatement()
    }

    -- Send statements to server, retrieve response
    local save, updateInterval, sound, speed, frameskip = self:sendList(statements)

    -- Handle each response and pass to appropriate functions
    self:getSave(save)
    self.updateInterval = self:get(updateInterval)
    client.SetSoundOn(self:get(sound))
    client.speedmode(self:get(speed))
    client.frameskip(self:get(frameskip))

    self:restartEpisode()
end

-- =====================================================================================================================
-- ?
-- =====================================================================================================================

print("BHClient.lua loaded!")
