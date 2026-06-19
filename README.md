# AggV3 IGV URLs
Construct IGV URLs in CloudOS.

Run this tool in any interactive CloudOS environment. The tab-separated output
includes an IGV URL for each participant. 

## Installation

Open a terminal in any interactive CloudOS session.

### Global install
Install uv (a Conda install is necessitated by CloudOS):

`conda install uv` 

Install aggv3_igv:

`uv tool install git+https://github.com/alexblakes/aggv3_igv.git`

(You might need to update your path and/or restart your shell if prompted by uv):

```bash
uv tool update-shell
bash
```

Run the tool:

`aggv3_igv -h`

### Install to a Pixi project
Within an existing Pixi project:

```bash
pixi add --pypi 'aggv3_igv @ https://github.com/alexblakes/aggv3_igv.git'
pixi run aggv3_igv -h
```

## Usage

**Note that IGV must be open prior to using a URL**

Click the URL, or copy/paste it into a browser, to launch an IGV session zoomed to the 
given region. IGV will include tracks for the given participant and all other 
participants sharing that family ID.
