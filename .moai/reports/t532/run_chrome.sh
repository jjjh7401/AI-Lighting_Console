#!/bin/bash
set -e
APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$APP" --headless=new --disable-gpu --screenshot="$1" --window-size="$2" --default-background-color=14161a "$3"
