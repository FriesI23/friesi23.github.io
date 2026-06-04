SHELL := /bin/bash

JEKYLL_SERVE := bundle exec jekyll serve
JEKYLL_FLAGS :=
LOCAL_CONFIG := _config.yml,_config.local.yml
PROD_CONFIG := _config.yml
JEKYLL_CONFIG := $(LOCAL_CONFIG)

ifeq ($(DRAFT),1)
JEKYLL_FLAGS += --drafts
endif

ifeq ($(PROD),1)
export JEKYLL_ENV := production
JEKYLL_CONFIG := $(PROD_CONFIG)
endif

.PHONY: help serve serve-prod serve-drafts serve-prod-drafts

help:
	@echo "Usage:"
	@echo "  make serve                     # local config (_config.yml,_config.local.yml)"
	@echo "  make serve PROD=1              # production config (_config.yml)"
	@echo "  make serve DRAFT=1"
	@echo "  make serve PROD=1 DRAFT=1"

serve:
	@$(JEKYLL_SERVE) --config $(JEKYLL_CONFIG) $(JEKYLL_FLAGS)

serve-prod: PROD=1
serve-prod: serve

serve-drafts: DRAFT=1
serve-drafts: serve

serve-prod-drafts: PROD=1
serve-prod-drafts: DRAFT=1
serve-prod-drafts: serve