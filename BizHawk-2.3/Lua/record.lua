handle = forms.newform(250, 250, "Recorder")
recording = false
recordBtn = 0

function recordClick()
    if recording then
        recording = false
        forms.settext(recordBtn, "Start Recording")
    else
        recording = true
        forms.settext(recordBtn, "Stop Recording")
    end
end

recordBtn = forms.button(handle, "Start Recording", recordClick, 0, 0, 200, 200)

while true do
    emu.frameadvance()
end