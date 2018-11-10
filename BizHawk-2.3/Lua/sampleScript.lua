

frames = 0

while true do
	emu.frameadvance()
	frames = frames + 1
	
	if frames == 20 then
		comm.httpPostScreenshot()
		frames = 0
	end
end