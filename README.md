### Consignment Store

Custom app for running our consignment store

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app consignment_store
```

### Setting up a dev environment

1. Create dirs
- `sudo mkdir -p /opt/shared/frappe`
- `cd /opt/shared`

2. Create frappe user and add to docker group, do not skip this.
- `sudo useradd frappe`
- `sudo usermod -aG docker frappe`
- `sudo chown -R frappe:frappe frappe`

3. Change into the user and download containers
- `sudo su frappe`
- `cd frappe`
- `git clone https://github.com/frappe/frappe_docker.git`
- `cd frappe_docker`
- `cp -R devcontainer-example .devcontainer`

4. Start Docker Daemon and go!
- `sudo systemctl start docker` (from different terminal, frappe isn't in sudoers list)
- `docker-compose -f .devcontainer/docker-compose.yml up -d` (from frappe user it is in docker group as we added it)
- `docker exec -e "TERM=xterm-256color" -w /workspace/development -it devcontainer-frappe-1 bash`
You are now in the container and can run bench commands

5. Install ERPNext + Frappe
- `sudo chown -R frappe:frappe /workspace`
- `python installer.py -n 20 -d mariadb`
- `cd frappe-bench`
- `bench use development.localhost`
- `bench start`

Congratulations you are now running an ERPNEXT development instance. Do the
install on 127.0.0.1:8000/app and create a company the consignment_store expects
a company for the postinstall. You can log in with Administrator admin

6. Clone the repo and install it
- cd into apps directory from your user that has access to your ssh key, i.e. outside the docker container
- `git clone git@github.com:0x01d/erpnext_consignment_store.git ./consignment_store`
- TODO

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/consignment_store
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

gpl-2.0
