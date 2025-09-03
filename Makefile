.PHONY: setup install run run-config update-all clean help

setup: ## Create virtual environment and install dependencies
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

install: ## Install dependencies in existing environment
	pip install -r requirements.txt

run: ## Run the playlist manager (legacy mode, requires ARGS="--playlist-title 'Title' channel1 channel2")
	./venv/bin/python g3k-yt-pl.py $(ARGS)

run-config: ## Run with config file (requires PLAYLIST=name, optional CONFIG=file)
	./venv/bin/python g3k-yt-pl.py --config $(or $(CONFIG),playlists.json) --playlist $(PLAYLIST)

update-all: ## Update all playlists from config file
	./update-all.sh

clean: ## Remove virtual environment and cache files
	rm -rf venv/
	rm -rf json_cache/
	rm -f token.json

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
