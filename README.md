![license](https://img.shields.io/github/license/fdrtd/datashield)
![CodeQL](https://github.com/fdrtd/datashield/workflows/CodeQL/badge.svg)
![Pylint](https://raw.githubusercontent.com/fdrtd/datashield/main/.github/badges/pylint.svg)


# description

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


# server-side installation

    pip install fdrtd
    pip install fdrtd-datashield
    python -m fdrtd.webserver --port=...


# client-side usage

For a detailed example on how to use the `protocol_DataSHIELD` plugin on the client side, please refer to `protocol_DataSHIELD/examples/example.py`.
