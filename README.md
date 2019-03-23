# Introduction

This script can be used to perform sequenced downloads of various sensors logs for the robotcar-dataset <https://robotcar-dataset.robots.ox.ac.uk/>.

The code is tested for Python2 on macOS High Sierra 10.13.4 and Ubuntu 16.04.

# Getting started

```bash
wget https://raw.githubusercontent.com/matthewgadd/RobotCarDataset-Scraper/master/Dockerfile
docker build -t robotcar-dataset-scraper .
```

# Example usage

Mount your downloads dir through the docker image:

```bash
docker run --rm -it -w /RobotCarDataset-Scraper -v $HOME/Downloads:/Downloads robotcar-dataset-scraper:latest
```

The script

```bash
python get_datasets.py
```

parses the html for the complete dataset listing and scrapes each dataset page and retrieves the available files (tar) for download. With the example output file datasets.csv provided, you should then run:

```bash
python scrape_mrgdatashare.py --downloads_dir /Downloads --datasets_file datasets.csv --username USERNAME --password PASSWORD
```