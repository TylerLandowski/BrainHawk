--
-- @Author Tyler Landowski
--

DIST_ADDR = 0x16328A

require("./learningClient")

-- Create a new client
c = DLSClient:new("http://127.0.0.1:1337")
c:initialize()

function c:saveDistance ()
	c:set("distance" .. c.numScreenshots - 1, mainmemory.read_s16_be(DIST_ADDR), "INT")
end

function c:saveDistanceStatement ()
	return "SET distance " .. c.numScreenshots - 1 .. " " .. mainmemory.read_s16_be(DIST_ADDR)
end

-- Initialize distance list
c:sendStr("SET distance INT[] []")

while true do
	c:advanceFrame()
	c:useControls()
	--print(frames .. "/" .. updateInterval)

	-- Draw an indicator to show guesses (red) or predictions (green)
	c:colorAction()
	
	if c:handleUpdate() then
		-- print("Screenshot " .. c.numScreenshots)
		c:saveScreenshot()

		-- Build a list of statements (to send in one request to server)
		local statements = {
			c:saveDistanceStatement(),  -- No return
			c:updateStatement(),  -- No return
			c:updateControlsStatement(),  -- Returns controls
			c:checkRestartStatement(),  -- Returns whether emulator should reset
			c:checkGuessedStatement()  -- Returns whether last action was randomly guessed
		}

		-- Send statements, grab results
		local controlsString, restart, guessed = c:sendList(statements)

		-- Send results to the appropriate functions
		c:updateControls(controlsString)
		c:checkRestart(restart)
		c:checkGuessed(guessed)
	end
end