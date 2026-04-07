SHELL := /bin/bash

COMPOSE := docker compose
BASE_FILE := -f docker-compose.yml
LANGFUSE_FILE := -f docker-compose.langfuse.yml

.PHONY: help setup setup-all setup-langfuse up down ps logs \
        langfuse-up langfuse-down langfuse-ps langfuse-logs \
        stack-up stack-down stack-ps stack-logs

help:
	@echo "Available targets:"
	@echo "  make setup            # Start full project (app + langfuse)"
	@echo "  make setup-all        # Same as setup"
	@echo "  make setup-langfuse   # Start only langfuse stack"
	@echo "  make up               # Start full project (app + langfuse)"
	@echo "  make down             # Stop full project (app + langfuse)"
	@echo "  make ps               # Show status for app + langfuse"
	@echo "  make logs             # Tail logs for app + langfuse"
	@echo ""
	@echo "App stack only:"
	@echo "  make stack-up|stack-down|stack-ps|stack-logs"
	@echo ""
	@echo "Langfuse only:"
	@echo "  make langfuse-up|langfuse-down|langfuse-ps|langfuse-logs"

setup: up

setup-all: up

setup-langfuse: langfuse-up

up:
	$(COMPOSE) $(BASE_FILE) $(LANGFUSE_FILE) up -d

down:
	$(COMPOSE) $(BASE_FILE) $(LANGFUSE_FILE) down

ps:
	$(COMPOSE) $(BASE_FILE) $(LANGFUSE_FILE) ps

logs:
	$(COMPOSE) $(BASE_FILE) $(LANGFUSE_FILE) logs -f --tail=200

stack-up:
	$(COMPOSE) $(BASE_FILE) up -d

stack-down:
	$(COMPOSE) $(BASE_FILE) down

stack-ps:
	$(COMPOSE) $(BASE_FILE) ps

stack-logs:
	$(COMPOSE) $(BASE_FILE) logs -f --tail=200

langfuse-up:
	$(COMPOSE) $(LANGFUSE_FILE) up -d

langfuse-down:
	$(COMPOSE) $(LANGFUSE_FILE) down

langfuse-ps:
	$(COMPOSE) $(LANGFUSE_FILE) ps

langfuse-logs:
	$(COMPOSE) $(LANGFUSE_FILE) logs -f --tail=200
