# Synchronization tool

## Usage

### Case of usage on local user
```
source setup_sync_tool.sh
```
It will create ./bin/localdbtool-sync.py and `my_configure.yml`, and open to edit `my_configure.yml` automatically. Then type below to see what will be happened.
```
./bin/localdbtool-sync.py --config my_configure.yml
```

If there is no problem, type `y` to continue.

### Install for automatic synchronization
```
sudo make install
```
Edit `/etc/localdbtools/default.yml` for configuration, and `/etc/cron.d/localdbtool-sync` to change date-time for auto sync.
