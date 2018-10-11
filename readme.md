# Moodle scraper
## The Basics
This is a basic scraper for Moodle at AAU (Aalborg University).

Currently it supports 

- downloading resources (files)
- downloading texts (page)
- downloading folders (files and description)
- downloading information on each section (summary)
- parsing all semesters and all courses
- sanitizing paths and filenames (fairly good)
- using etags to not download the same file (uses json for database)

What needs to be done

- thread downloading
- cleanup
- make some parser for text download (links)
- maybe pack it up nicely in some markdown

## setup
Create files

`database.json`

```
{"files":[]}
```

`.env`

```
export MOODLE_USERNAME=email@student.aau.dk
export MOODLE_PASSWORD=password
```

Running

```
source .env
python3 moodle.py
```

## How to use with docker
This container just install the requirements (no file currently), so it can use the scraper. 
Nothing fancy..

```
docker build -t moodle .
docker run --rm -it -v $(pwd):/src moodle
python3 /src/moodle.py 
```

