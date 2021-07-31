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
Installing and running `fdrtd_server` with the `protocol_DataSHIELD` is very simple and takes only 4 commands:
```shell
git clone https://github.com/fdrtd/server
cd server
git clone https://github.com/fdrtd/server/protocol_DataSHIELD
python3 -m openapi_server -port:5000 
```
And that's all! You now have a `fdrtd_server` running on `http://localhost:5000`!

For a detailed example on how to use the `protocol_DataSHIELD` on the client side, please refer `protocol_DataSHIELD/examples/example.py`.
