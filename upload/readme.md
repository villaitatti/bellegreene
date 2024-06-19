# How to run

The script needs to run venv, and it can be created from the requirements.txt.
After, get docx of documents and stylesheet "BG to BB Letters_Spreadsheet" renamed into control.csv

```
Usage: script.py [OPTIONS]

Options:
  -u            Execute the upload
  -P            Prune output folder
  -direct PATH  Only for development purposes
  -l INTEGER    Subset of letters to iterate
  -I TEXT       Starting URL of images
  -c TEXT       profile to select usr, psw, and endpoint from psw.ini. see
                readme
  --help        Show this message and exit.
```

For upload create a psw.ini file such as the following. The profile should be `belle_greene`
```
[belle_greene]
username = usr
password = psw
endpoint = localhost
```