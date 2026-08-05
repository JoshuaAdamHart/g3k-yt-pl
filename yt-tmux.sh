#!/bin/bash
SESSION="g3k-yt"

# Check if session already exists; if not, create it detached (-d)
tmux has-session -t $SESSION 2>/dev/null
if [ $? != 0 ]; then
  tmux new-session -d -s $SESSION -n "loop"
  tmux send-keys -t $SESSION:loop "g3k-yt-session-current" C-m
fi

# Attach to the session
tmux attach -t $SESSION
