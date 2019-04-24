BIN=bin

TARGET_FILE=localdb-tool.py

TARGET=$(BIN)/$(TARGET_FILE)

all: $(TARGET)

$(TARGET): check src/*
	@echo -e "[LDB] Welcome!"
	grep -vh -e "imports" imports/imports.py > $(TARGET)
	grep -vh -e "^\s*#" -e "import" -e "__main__" imports/*.py >> $(TARGET)
	grep -vh -e "^\s*#" -e "import" -e "__main__" src/*.py >> $(TARGET)
	cat tools/main.py >> $(TARGET)
	@chmod +x $(TARGET)
	@echo -e "[LDB] Compile done, type 'make install'"

.PHONY: check
check:
	@python3 tools/check.py

cron: $(CONFIG)
	crontab mycron

$(CONFIG): 
	@echo "* * 3 * * $(PWD)/$(TARGET) sync --config $(PWD)/$(CONFIG)" > mycron
	"$$[EDITOR]" $(CONFIG)

install: $(TARGET)
	@echo "Install Local DB Tool ..."
	@[ "$(whoami)" != "root" ] && exec sudo -- "$0" "$@"
	cp $(TARGET) /usr/$(BIN)/.
	mkdir -p /etc/mongo.d
	cp ./conf/mongo.d/mongosync.yml /etc/mongo.d/.
	cp ./conf/cron.d/mongosync.cron /etc/cron.d/.

config-backup:
	@echo "Config auto backup"
	"$${EDITOR:-vi}" /etc/mongo.d/mongobackup.conf
	"$${EDITOR:-vi}" /etc/cron.d/mongobackup.cron

uninstall:
	@[ "$(whoami)" != "root" ] && exec sudo -- "$0" "$@"
	rm -f /usr/$(TARGET) /etc/mongo.d/mongobackup.conf /etc/cron.d/mongosync.cron

.PHONY: clean
clean:
	rm -f $(TARGET)

