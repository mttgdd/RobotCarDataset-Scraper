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

If you do not need the full dataset, you can use `--choice_sensors` and `--choice_runs_file` options to download parts of the dataset on your own needs. 

* `--choice_sensors` option can receive multiple sensor names in `tags, stereo_centre, stereo_left, stereo_right, vo, mono_left, mono_right, mono_rear, lms_front, lms_rear, ldmrs, gps, all. `
* `--choice_runs_file` option receive a `.txt` file that contains the names of runs you want to download, we provide an example filea sample file `example_list.txt` .

for example you can download "stereo_centre", "vo" and "lms_front" data of  "2014-05-19-13-20-57" and "2014-06-26-09-31-18" by the following command:

```bash
python scrape_mrgdatashare.py --choice_sensors stereo_centre,vo,lms_front --choice_runs_file example_list.txt --downloads_dir /Downloads --datasets_file datasets.csv --username USERNAME --password PASSWORD
```

