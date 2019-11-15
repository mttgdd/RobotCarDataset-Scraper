# Introduction

This script can be used to perform sequenced downloads of various sensors logs for the robotcar-dataset <https://robotcar-dataset.robots.ox.ac.uk/>.

The code is tested for Python3 on Ubuntu 16.04.

# Getting started

A prebuilt docker image is available with:

```bash
docker pull matthewgadd/robotcar-dataset-scraper:latest
```

Otherwise, you can build the docker image from scratch:

```bash
wget https://raw.githubusercontent.com/matthewgadd/RobotCarDataset-Scraper/master/Dockerfile
docker build -t matthewgadd/robotcar-dataset-scraper:latest .
```

# Example usage

Mount your downloads dir through the docker image:

```bash
docker run --rm -it -w /RobotCarDataset-Scraper -v $HOME/Downloads:/Downloads matthewgadd/robotcar-dataset-scraper:latest
```

The script

```bash
python get_datasets.py
```

parses the html for the complete dataset listing and scrapes each dataset page and retrieves the available files (tar) for download. With the example output file datasets.csv provided, you should then run:

```bash
python scrape_mrgdatashare.py --downloads_dir /Downloads --datasets_file datasets.csv --username USERNAME --password PASSWORD
```
