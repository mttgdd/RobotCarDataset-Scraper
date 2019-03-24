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
    text_locations = [text_location.end()
                      for text_location in re.finditer(datasets_url, text)]
    datasets = [str(text[text_location:text_location + 19])
                for text_location in text_locations]

    # ignore metadata and sort unique datasets
    datasets = datasets[2:]
    datasets = sorted(list(set(datasets)))

    # write output text file
    datasets_file = "datasets.csv"
    with open(datasets_file, "w") as file_handle:
        # iterate datasets
        for dataset in datasets:
            # url to dataset page
            dataset_url = datasets_url + dataset
            result = session_requests.get(dataset_url)
            text = result.text

            # parse text for sensor type
            start = [
                text_location.end() for text_location in re.finditer(
                    "download/\?filename=datasets", text)]
            sensor_types = []
            for s in start:
                ss = s
                while text[ss + 40:ss + 44] != ".tar":
                    ss += 1
                sensor_type = text[s + 41:ss + 40]
                sensor_types.append(str(sensor_type))

            # write dataset entry
            file_handle.write(dataset + "," + ",".join(sensor_types) + "\n")


if __name__ == "__main__":
    main()
