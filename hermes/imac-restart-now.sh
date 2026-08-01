#!/bin/bash
# macOS Restart — No Password Required
# Nutzt AppleScript statt sudo

osascript << 'APPLESCRIPT'
tell application "System Events"
    restart
end tell
APPLESCRIPT
