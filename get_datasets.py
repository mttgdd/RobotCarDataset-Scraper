#!/usr/bin/env python

'''
Gets a list of available datasets from the Oxford Robotcar Dataset website.

Matt Gadd
Mar 2019
Oxford Robotics Institute, Oxford University.

'''

import requests
import re

from scrape_mrgdatashare import datasets_url

def main():
    # open session
    session_requests = requests.session()

    # get http response from website
    result = session_requests.get(datasets_url)
    text = result.text

    # parse response text
    text_locations = [text_location.end() for text_location in re.finditer(datasets_url, text)]
    datasets = [str(text[text_location:text_location + 19]) for text_location in text_locations]

    # ignore metadata and sort unique datasets
    datasets = datasets[2:]
    datasets = sorted(list(set(datasets)))

    # write output text file
    datasets_file = "datasets-long.txt"
    with open(datasets_file, "w") as file_handle:
        for dataset in datasets:
            file_handle.write(dataset + "\n")


if __name__ == "__main__":
    main()
