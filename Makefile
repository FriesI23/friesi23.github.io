SHELL := /bin/bash

JEKYLL_SERVE := bundle exec jekyll serve
LOCAL_CONFIG := _config.yml,_config.local.yml
PROD_CONFIG := _config.yml
JEKYLL_FLAGS = $(if $(filter 1,$(DRAFT)),--drafts,)
JEKYLL_CONFIG = $(if $(filter 1,$(PROD)),$(PROD_CONFIG),$(LOCAL_CONFIG))
JEKYLL_ENV = $(if $(filter 1,$(PROD)),production,)
export JEKYLL_ENV

.PHONY: help serve serve-prod serve-drafts serve-prod-drafts sync-prompts

help:
	@echo "Usage:"
	@echo "  make serve                     # local config (_config.yml,_config.local.yml)"
	@echo "  make serve PROD=1              # production config (_config.yml)"
	@echo "  make serve DRAFT=1"
	@echo "  make serve PROD=1 DRAFT=1"
	@echo "  make sync-prompts              # sync assets/prompts/ stubs with _prompts/*.md"

serve:
	@$(JEKYLL_SERVE) --config $(JEKYLL_CONFIG) $(JEKYLL_FLAGS)

serve-prod: PROD=1
serve-prod: serve

serve-drafts: DRAFT=1
serve-drafts: serve

serve-prod-drafts: PROD=1
serve-prod-drafts: DRAFT=1
serve-prod-drafts: serve

sync-prompts:
	@python3 ci/sync_prompt_assets.py