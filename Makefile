.PHONY: format lint build launch

XCODEBUILD ?= xcodebuild
PROJECT ?= Teleport.xcodeproj
SCHEME ?= Teleport
CONFIGURATION ?= Debug
DESTINATION ?= platform=macOS
CODE_SIGN_FLAGS ?= CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO

TARGET_BUILD_DIR := $(shell $(XCODEBUILD) -project $(PROJECT) -scheme $(SCHEME) -configuration $(CONFIGURATION) -destination '$(DESTINATION)' $(CODE_SIGN_FLAGS) -showBuildSettings | awk -F' = ' '/TARGET_BUILD_DIR/{print $$2; exit}')
APP_BUNDLE := $(TARGET_BUILD_DIR)/$(SCHEME).app

format:
	swift format -r -p -i .

lint:
	swift format lint -r -p .

build:
	$(XCODEBUILD) -project $(PROJECT) -scheme $(SCHEME) -configuration $(CONFIGURATION) -destination '$(DESTINATION)' $(CODE_SIGN_FLAGS) build

launch: build
	pkill -x "$(SCHEME)" || true
	sleep 0.5
	open "$(APP_BUNDLE)"

install-cli:
	mkdir -p $(HOME)/.local/bin
	ln -sf $(CURDIR)/bin/teleport $(HOME)/.local/bin/teleport
	@echo "Installed teleport CLI to $(HOME)/.local/bin/teleport"
