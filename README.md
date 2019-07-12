# Local DB tools for ITk

It contains,
- DB Viewer (/viewer)
- Synchronization tool (/sync-tool)
- Archive tool (`/archive-tool`)

# Requirements
- Need `python3` >= 3.7.3 and its pip.
- Install required packages with root `pip install -r requirements-pip.txt`.
- Or, install on local `pip install -r Requirements.txt --user`.

* [Setting](#Setting_script)
* [Viewer Application](#Start_up_Viewer_Application)

# Setting script 
`setting/db_server_install.sh` can...
- Install libraries by yum
  - `requirements-yum.txt`
  - python36 and pip3
  - MongoDB
  - httpd
- Install Modules by pip3
  - `requirements-pip.txt`
- Start services
  - MongoDB
  - httpd
- Open firewall port for accessing to Viewer Application from other machine
  - port=80/tcp for appache
  - port=5000/tcp for viewer application
- Initialize MongoDB data set
  - clone into /var/lib/mongo and store the previous one to /var/lib/mongo-${today}.tar.gz as backup

## Pre Requirement
- centOS7
- sudo user account
- net-tools
```bash
$ sudo yum install -y net-tools
```

## Usage
```bash
$ cd setting
$ sudo ./db_server_install.sh

Local DB Server IP address: XXX.XXX.XXX.XXX

Are you sure that's correct? [y/n]
# answer 'y' and move on to the installation
y
```


# Start up Viewer Application

Check detail in `viewer/README.md`

