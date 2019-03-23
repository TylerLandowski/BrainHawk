require("./BHClient")

c = BHClient:new("http://127.0.0.1:1337")
c:initialize()

while true do
    --
    -- Perform actions from server
    --

    c:useControls()   -- Set the controls to use until the next frame
    c:advanceFrame()  -- Advance a single frame

    --
    -- Retrieve feedback from server
    --

    -- Is it time to communicate with the server?
    if c:timeToUpdate() then
        -- Save a screenshot on the server
        c:saveScreenshot()

        -- Build a list of statements (to send in one request to server)
        local statements = {
            c:setStatement("x", 512, "INT"),  -- Set x = 512 (as a Python Int). No return
            c:getStatement("x"),              -- Get value for x
            c:updateStatement(),              -- Call server's update(). No return
            c:setControlsStatement(),         -- Returns controls from server
            c:checkRestartStatement(),        -- Returns whether emulator should reset
            c:checkExitStatement()            -- Returns whether client should exit
        }

        -- Compiled Message:
        -- SET x Int 512;
        -- GET x;
        -- UPDATE;
        -- GET controls;
        -- GET restart;
        -- GET exit

        -- Send statements, grab results
        local x_response, controls_response, restart_response, exit_response = c:sendList(statements)

        -- Send results to the appropriate functions
        local xType, x = c:get(x_response)
        c:setControls(controls_response)
        c:checkRestart(restart_response)

        -- Note: This will drastically slow learning speed
        --console.writeline("x: " .. xType .. " " .. x)

        -- Did the server tell us to exit?
        if c:checkExit(exit_response) then break end
    end
end