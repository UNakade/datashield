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
Installing and running `fdrtd_server` with `protocol_DataSHIELD` is very simple and takes only 3 commands:
```shell
git clone https://github.com/fdrtd/fdrtd
git clone https://github.com/fdrtd/protocol_DataSHIELD ./fdrtd/protocol_DataSHIELD
python -m fdrtd.webserver --port=5000 
```
And that's all! You now have a `fdrtd_server` running on `http://localhost:5000`!

Please note that the directory structure is important for the internal imports to work. The protocol_DataSHIELD repository should be cloned directly inside the fdrtd directory and the webserver should be started from the directory containing the fdrtd repository.  

For a detailed example on how to use the `protocol_DataSHIELD` plugin on the client side, please refer to `protocol_DataSHIELD/examples/example.py`.
