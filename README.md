# Example usage

With the file datasets.txt and file_patterns.txt examples provided run:

```bash
python scrape_mrgdatashare.py --downloads_dir ~/Downloads --dataset * --datasets_file datasets.txt --file_pattern * --file_patterns_file file_patterns.txt --username USERNAME --password ****
```

and a file ~/Downloads/2014-05-06-12-54-54/vo/vo.csv should be downloaded, and extraced.
