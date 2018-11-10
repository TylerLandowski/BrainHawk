green = 0x6600FF00
red = 0x66FF0000

while true do
    gui.drawBox(0,0, 0, 0, RED, RED)
    emu.frameadvance()
end

--[[
ctls = {}
ctls["P1 X Axis"] = "-129"  --[-128, 127]

joypad.set(ctls)
joypad.setanalog(ctls)

for i = 1, 500, 1 do
    joypad.set(ctls)
    joypad.setanalog(ctls)
    emu.frameadvance()
end

ctls["P1 X Axis"] = "0"
joypad.set(ctls)
joypad.setanalog(ctls)
]]