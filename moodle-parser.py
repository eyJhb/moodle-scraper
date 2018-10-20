from moodle import Moodle
import string
import json
import os
import re

class Moodle_parser(object):
    def __init__(self, username, password):
        self.output_dir = "output/"
        self.database = "database.json"
        self.db = {}

        self.moodle = Moodle(username, password)
        if not self.moodle.login():
            exit()

        self.initDatabase()

    def makeDir(self, path):
        os.makedirs(path, exist_ok=True)

    def fileWrite(self, filePath, text):
        with open(filePath, "w") as f:
            f.write(text)
        return True

    def sanitizeInput(self, inputText):
        #specialchars list (excluding `-`, `_`, `/` and `.`)
        punc = string.punctuation. \
            replace("-", ""). \
            replace("_", ""). \
            replace(".", ""). \
            replace("/", "")

        #replacement chars
        reps = [
            ["æ", "ae"],
            ["ø", "oe"],
            ["å", "aa"],
            [" ", "-"],
            ["_", "-"],
        ]

        # lowercase it
        inputText = inputText.lower()

        # remove all puncution chars
        for char in punc:
            inputText = inputText.replace(char, "")

        # replace chars
        for rep in reps:
            inputText = inputText.replace(rep[0], rep[1])

        # replace double `-`
        strLen = len(inputText)
        while True:
            inputText = inputText.replace("--", "-")
            
            if len(inputText) == strLen:
                break
            strLen = len(inputText)

        return inputText

    def initDatabase(self):
        if not os.path.isfile(self.database):
            self.fileWrite(self.database, '{"files": []}')
        data = open(self.database, "r").read()
        self.db = json.loads(data)
        return True

    def saveDatabase(self):
        self.fileWrite(self.database, json.dumps(self.db))

    def findFile(self, fileid = None, href = None, etag = None, sha1 = None):
        for mFile in self.db["files"]:
            if (href and mFile["href"] == href or
                etag and mFile["etag"] == etag or 
                fileid and mFile["fileid"] == fileid or
                sha1 and mFile["sha1"] == sha1):
                return mFile
        return False

    def getFile(self, href, folder):
        headers = {}
        fileDb = self.findFile(href=href)
        if fileDb:
            headers["If-None-Match"] = fileDb["etag"]

        r = self.moodle.getFile(href, tempfile = "file.tmp", headers=headers)
        
        if not r:
            return False

        if r.status_code == 304:
            return True

        d = r.headers["content-disposition"]
        fname = re.findall("filename=(.+)", d)
        fname = fname[0][1:-1]

        self.db["files"].append({
            "etag": r.headers["Etag"],
            "href": href,
        })

        os.rename("file.tmp", folder+"/"+self.sanitizeInput(fname))

        return True

    def download_files(self):
        semesters = self.moodle.semesters()

        if not semesters:
            return False

        for semester in semesters:
            if not semester["name"] == "Autumn 2018":
                continue

            self.getSemester(semester)

    def getSemester(self, semester):
        semesterName = self.sanitizeInput(semester["name"])
        semesterFolder = self.output_dir+semesterName
        self.makeDir(semesterFolder)

        for course in semester["courses"]:
            courseDict = self.moodle.course(course["href"])
            if not courseDict:
                continue

            self.getCourse(semesterFolder, course, courseDict)

    def getCourse(self, folder, course, sections):
        courseName = self.sanitizeInput(course["name"][:course["name"].rfind("(")-1])
        courseFolder = folder+"/"+courseName
        self.makeDir(courseFolder)

        for section in sections:
            self.getSection(courseFolder, section)

    def getSection(self, folder, section):
        sectionName = self.sanitizeInput(section["name"]).replace(".", "")
        sectionFolder = folder+"/"+section["number"]+"-"+sectionName
        self.makeDir(sectionFolder)

        if section["summary"]:
            self.fileWrite(sectionFolder+"/summary.txt", section["summary"])

        for child in section["children"]:
            if child["type"] == "resource":
                self.getFile(child["href"], sectionFolder)
            elif child["type"] == "folder":
                folderName = self.sanitizeInput(child["name"])
                folderFolder = sectionFolder+"/"+folderName
                self.makeDir(folderFolder)
                if child["text"]:
                    self.fileWrite(folderFolder+"/summary.txt", child["text"])

                for f in child["files"]:
                    self.getFile(f["href"], folderFolder)
            elif child["type"] == "page":
                pageName = self.sanitizeInput(child["name"])
                if child["text"]:
                    self.fileWrite(sectionFolder+"/"+pageName, child["text"])


username = os.getenv("MOODLE_USERNAME", "username")
password = os.getenv("MOODLE_PASSWORD", "password")

x = Moodle_parser(username, password)
x.download_files()
x.saveDatabase()
