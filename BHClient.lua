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
        table[key] = val
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
    return (str == "True" and true or false)
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

--[[ Colors the screen based on whether the last action was guessed randomly ]]
function BHClient:colorAction ()
    if self.guessed == true then
        gui.drawBox(0, 0, 20, 20, RED, RED)
        --gui.drawText(0, 0, "Random Action")
    else
        gui.drawBox(0, 0, 20, 20, GREEN, GREEN)
    end
end

-- =====================================================================================================================
-- Server Interaction Functions
-- =====================================================================================================================

--[[ Returns whether it's time to update the server. Resets self.frames ]]
function BHClient:handleUpdate ()
    if self.frames == self.updateInterval then
        self.frames = 0
        return true
    else
        return false
    end
end

--[[ Sets the emu to the base state (loads save, numScreenshots = 0) ]]
function BHClient:restartEpisode ()
    savestate.load("../" .. self.save)
    self.numScreenshots = 0
end

--[[ Sends the string to the server, and returns each output as a separate return ]]
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

--[[ Sends a list of statements to the server, and returns each output as a separate return ]]
function BHClient:sendList (list)
    return self:sendStr(self:stringFromList(list))
end

--[[ Call the server's update function ]]
function BHClient:update()
    self:sendStr("UPDATE")
end

function BHClient:updateStatement()
    return "UPDATE"
end

--[[ Sets the variable on server to the given value, and labels it as the given data type.
     If no dataType is given, assume it to be a string. ]]
function BHClient:set (var, val, dataType)
    -- Send an HTTP post
    if not dataType then
        return self:sendStr("SET " .. var .. " " .. val)
    else
        return self:sendStr("SET " .. var .. " " .. dataType .. " " .. val)
    end
end

--[[ TODO ]]
function BHClient:setStatement (var, val, dataType)
    -- Send an HTTP post
    if not dataType then
        return "SET " .. var .. " " .. val
    else
        return "SET " .. var .. " " .. dataType .. " " .. val
    end
end

--[[ Grabs the data type and value of the variable on server ]]
function BHClient:get (var, response)
    local body = response

    if not response then
        -- Send an HTTP post
        body = self:sendStr("GET " .. var)
    end

    -- Does the variable exist?
    if body == "None" then
        return "None"
    end

    -- Is the variable outside data?
    if var == "restart" or var == "sound" or var == "guessed" then
        return self:boolFromString(body)
    elseif var == "update_interval" or var == "actions" or var == "speed" or var == "frameskip"
    or     var == "save_slot" then
        return tonumber(body)

        -- Is the variable inside data?
    else
        -- Split the body
        local dataType, val = string.match(body, "(%w+) (.+)")

        -- Convert the value based on the data type
        if dataType == "INT" then
            val = tonumber(val)
        elseif dataType == "BOOL" then
            val = bool:boolFromString(val)
        end

        return dataType, val
    end
end

--[[ TODO ]]
function BHClient:getStatement (var)
    return "GET " .. var
end

--[[ Takes a screenshot of the game, sends it to server ]]
function BHClient:saveScreenshot ()
    comm.httpPostScreenshot()
    c.numScreenshots = c.numScreenshots + 1
end

--[[ Stores controls from server to controls table ]]
function BHClient:updateControls (controlsString)
    local controls = controlsString

    if not controls then
        controls = self:sendStr("GET controls")
    end

    self.controls = self:tableFromString(controlsString)
end

function BHClient:updateControlsStatement()
    return "GET controls"
end

--[[ Checks if the episode should restart.
     If yes, load the save state and set numScreenshots = 0 ]]
function BHClient:checkRestart (restart)
    local bool = restart

    if not bool then
        bool = self:sendStr("GET restart")
    end

    if bool == "True" then
        self:restartEpisode()
    end
end

--[[ Returns the statement used for checkRestart() function
     Return of statement should be passed to checkRestart() ]]
function BHClient:checkRestartStatement ()
    return "GET restart; SET restart False"
end

function BHClient:getSave (name)
    local save = name

    if not save then
        save = self:sendStr("GET save")
    end

    self.save = save
end

function BHClient:getSaveStatement ()
    return "GET save"
end

function BHClient:checkGuessed (guessed)
    local bool = guessed

    if not bool then
        bool = self:get("guessed")
    end

    self.guessed = self:boolFromString(bool)
end

--[[  ]]
function BHClient:checkGuessedStatement ()
    return "GET guessed"
end

--[[ Loads BizHawk settings from the server. Sets the emu to the base state. ]]
function BHClient:initialize ()
    comm.httpSetPostUrl(self.addr)
    self:getSave()
    self.updateInterval = self:get("update_interval")
    client.SetSoundOn(self:get("sound"))
    client.speedmode(self:get("speed"))
    client.frameskip(self:get("frameskip"))
    self:restartEpisode()
end

-- =====================================================================================================================
-- ?
-- =====================================================================================================================

print("BHClient.lua loaded!")
