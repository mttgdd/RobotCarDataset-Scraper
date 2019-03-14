Example usage:

with file datasets.txt containing

2014-05-06-12-54-54

and file file_patterns.txt containing

vo

run this script like

python scrape_mrgdatashare.py --downloads_dir ~/Downloads --dataset * --datasets_file datasets.txt --file_pattern * --file_patterns_file file_patterns.txt --username USERNAME --password ****
and ~/Downloads/2014-05-06-12-54-54/vo/vo.csv should be downloaded