![license](https://img.shields.io/github/license/fdrtd/datashield)
![CodeQL](https://github.com/fdrtd/datashield/workflows/CodeQL/badge.svg)
![Pylint](https://raw.githubusercontent.com/fdrtd/datashield/main/.github/badges/pylint.svg)


## `DataSHIELD` plugin for `fdrtd` server

This plugin allows `fdrtd` clients to use `DataSHIELD`.
The plugin is written in `Python` and uses the `rpy2` library.


### Requirements:
- These `Python` libraries:
  - `rpy2` (`pip install rpy2[all]`)
  - `numpy`
  - `json`
- `libcurl` and `openssl` libraries for your operating system
- In addition to `R (>= v3.5.0)`, these `R` packages:
  - `curl` and `openssl`
  - `DSI`, `DSOpal`
  - `fields`, `metafor`, `ggplot2`, `gridExtra` and `data.table` (dependencies of `dsBaseClient`)
  - `dsBaseClient` (from the `http://cran.obiba.org` repository. For installation instructions, please visit the [DataSHIELD website](https://www.datashield.org/) and the [DataSHIELD wiki](https://data2knowledge.atlassian.net/wiki/spaces/DSDEV/overview))


### Installation:
Installing and running `fdrtd webserver` with `protocol_DataSHIELD` is very simple and takes only 3 commands:
```shell
git clone https://github.com/fdrtd/fdrtd
git clone https://github.com/fdrtd/protocol_DataSHIELD ./fdrtd/plugins/protocol_DataSHIELD
python -m fdrtd.webserver --port=5000 
```
And that's all! You now have a `fdrtd webserver` running on `http://localhost:5000`!

This command will result in a module not found error if the `fdrtd` client side library is installed in your system. To avoid this issue, the `fdrtd` client library should be installed in a separate virtual environment if you wish to have the server and the client running on the same machine.

For a detailed example on how to use the `protocol_DataSHIELD` plugin on the client side, please refer to `protocol_DataSHIELD/examples/example.py`.
