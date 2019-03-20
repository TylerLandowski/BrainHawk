require("./BHClient")

c = BHClient:new("http://127.0.0.1:1337")
c:initialize()

while true do
    c:useControls()   -- Set the controls to use until the next frame
	c:advanceFrame()  -- Advance a single frame

	-- Is it time to communicate with the server?
	if c:checkForUpdate() then
		c:saveScreenshot()

		-- Build a list of statements (to send in one request to server)
		local statements = {
			c:setStatement("x", 512, "Int"),  -- Set x = 512 (as a Python Int). No return
			c:getStatement("x"), -- Get value for x
			c:updateStatement(),              -- Call server's update(). No return
			c:updateControlsStatement(),      -- Returns controls from server
			c:checkRestartStatement()         -- Returns whether emulator should reset
		}

		-- Compiled Message:
		-- SET x Int 512;
		-- GET x;
		-- UPDATE;
		-- GET controls;
		-- GET restart; SET restart false

		-- Send statements, grab results
		local x_response, controls_response, restart_response = c:sendList(statements)

		-- Send results to the appropriate functions
		local xType, x = c:get(x_response)
		c:updateControls(controls_response)
		c:checkRestart(restart_response)

		print("x: " .. xType .. " " .. x)
	end
end