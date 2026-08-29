# Second ollama instance, installed in user space because updating the system
# service needs root. Runs on port 11435 with its own model store so the
# 0.17.6 instance and the 127 cells already measured against it stay untouched.
export OLLAMA_NEW_DIR=/home/dgx1/.local/ollama-new
export OLLAMA_NEW_HOST=127.0.0.1:11435
export OLLAMA_NEW_MODELS=/home/dgx1/.local/ollama-new-models
