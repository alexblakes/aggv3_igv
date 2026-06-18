# AggV3 IGV URLs
Construct IGV URLs in CloudOS.

Run this tool in any interactive CloudOS environment. The tab-separated output
includes an IGV URL for each participant. Click the URL, or copy/paste it into a
browser, to launch an IGV session zoomed to the given region, and showing IGV 
tracks for the given participant and their family members.

## Running the tool

From any interactive CloudOS workstation.

Install uv
`conda install uv`

Run the tool
`uvx --from git+https://github.com/alexblakes/aggv3_igv.git aggv3_igv -h`