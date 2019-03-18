require("./BHClient")

c = DLSClient:new("http://127.0.0.1:1337")
c:initialize()

while true do
	c:useControls()   -- Set the controls to use until the next frame
	c:advanceFrame()  -- Advance a single frame
	
	-- Is it time to communicate with the server?
	if c:handleUpdate() then
		c:saveScreenshot()

		-- Build a list of statements (to send in one request to server)
		local statements = {
			c:setStatement("x", 512, "Int"),  -- Set x = 512 (as a Python Int). No return
			c:updateStatement(),              -- Call server's update(). No return
			c:updateControlsStatement(),      -- Returns controls from server
			c:checkRestartStatement()         -- Returns whether emulator should reset
		}

		-- Send statements, grab results
		local controlsString, restart = c:sendList(statements)

		-- Send results to the appropriate functions
		c:updateControls(controlsString)
		c:checkRestart(restart)
	end
end