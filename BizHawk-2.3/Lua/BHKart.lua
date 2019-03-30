--
-- @Author Tyler Landowski
--

DIST_ADDR = 0x16328A

require("./BHClient")

-- Create a new client
c = BHClient:new("http://127.0.0.1:1337")
c:initialize()

function c:saveDistanceStatement ()
	return "SET distance " .. c.numScreenshots - 1 .. " " .. mainmemory.read_s16_be(DIST_ADDR)
end

-- Initialize distance list
c:sendStr("SET distance INT[] []")

while true do
	c:useControls()
	c:advanceFrame()
	--print(frames .. "/" .. updateInterval)

	-- Draw an indicator to show guesses (red) or predictions (green)
	c:colorAction()
	
	if c:timeToUpdate() then
		-- print("Screenshot " .. c.numScreenshots)
		c:saveScreenshot()

		-- Build a list of statements (to send in one request to server)
		local statements = {
			c:saveDistanceStatement(),  -- No return
			c:updateStatement(),  -- No return
			c:setControlsStatement(),  -- Returns controls
			c:checkGuessedStatement()  -- Returns whether last action was randomly guessed
			c:checkExitStatement(),  -- Returns whether emulator should reset
		}

		-- Send statements, grab results
		local controls, guessed, restart, exit = c:sendList(statements)

		-- Send results to the appropriate functions
		c:setControls(controls)
		c:checkGuessed(guessed)
		c:checkRestart(restart)

		if c:checkExit(exit) then break end
	end
end