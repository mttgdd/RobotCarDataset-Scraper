# Introduction

This script can be used to perform sequenced downloads of various sensors logs for the robotcar-dataset <https://robotcar-dataset.robots.ox.ac.uk/>.

The code is tested for Python2 on macOS High Sierra 10.13.4.

# Example usage

With the abbreviated file datasets.txt and file_patterns.txt examples provided run:

```bash
python scrape_mrgdatashare.py --downloads_dir ~/Downloads --dataset "*" --datasets_file datasets.txt --file_pattern "*" --file_patterns_file file_patterns.txt --username USERNAME --password PASSWORD
```

and a file ~/Downloads/2014-05-06-12-54-54/vo/vo.csv should be downloaded, and extracted.

A more thorough example is provided in the files datasets-long.txt and file-patterns-long.txt, capturing many datasets and sensor types.
