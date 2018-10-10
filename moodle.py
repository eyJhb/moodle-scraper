import requests
from bs4 import BeautifulSoup
import logging
import hashlib
import string
import json
import os
import re
from modtypeParser import modtype

logging.basicConfig()

class moodle(object):
    def __init__(self, username, password):
        self.s = requests.session()

        self.url_base = "https://www.moodle.aau.dk/"

        self.loggedin = False
        self.username = username
        self.password = password

        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)


        self.modtype = modtype(self.s, self.log, self.url_base)


        '''
        files: [
            {
                "fileid": "id-of-file",
                "name": "filename",
                "path": "files/path/to/file/",
                "sha1": "sha1-of-file",
                "etag": "etag-of-file",
                "href": "link-to-the-file",
            }
        ]
        '''

        self.files_database = "database.json"
        self.files_output = "files/"
        self.db = self.databaseLoad()
        self.log.debug("test")
        if not self.initCheck():
            logging.error("Could not initialize Moodle")
            exit()

    def initCheck(self):
        #check that we have our database file
        if not self.fileExists(self.files_database):
            self.log.error("Our database file '%s' does not exists", self.files_database)
            return False
        #check for our {files: []} in our json
        try:
            self.db["files"]
        except:
            self.log.error("Our database does not contain {\"files\": []}")
            return False
        
        #check that our files_output exist
        if not self.folderExists(self.files_output):
            self.log.error("Output folder '%s' does not exists", self.files_output)
            return False

        return True

    def makeDir(self, path):
        os.makedirs(self.sanitizeFilenames(self.files_output+path), exist_ok=True)

    '''
    findDict = {
        "fileid": "id-of-file",
        "href": "http",
        "etag": "ouretag",
        "sha1"" "oursha",
    }

    '''
    def findFile(self, fileid = None, href = None, etag = None, sha1 = None):
        for mFile in self.db["files"]:
            if (href and mFile["href"] == href or
                etag and mFile["etag"] == etag or 
                fileid and mFile["fileid"] == fileid or
                sha1 and mFile["sha1"] == sha1):
                return mFile

        return False

    def fileWrite(self, filePath, text):
        with open(self.sanitizeFilenames(self.files_output+filePath), "w") as f:
            f.write(text)
        return True


    def fileExists(self, filePath):
        if os.path.isfile(self.sanitizeFilenames(filePath)):
            return True
        return False

    def folderExists(self, path):
        if os.path.isdir(self.sanitizeFilenames(path)):
            return True
        return False

    def getSha1(self, filePath):
        filePath = self.sanitizeFilenames(filePath)
        if not self.fileExists(filePath):
            return False

        hashSha1 = hashlib.sha1()
        with open(filePath, 'rb') as afile:
            buf = afile.read()
            hashSha1.update(buf)
        return hashSha1.hexdigest()

    def databaseLoad(self):
        self.log.debug("databaseLoad: loading database")

        f = open(self.files_database, "r")
        data = f.read()
        f.close()

        return json.loads(data)

    def databaseSave(self):
        self.log.debug("databaseSave: saving database")
        data = json.dumps(self.db)

        f = open(self.files_database, "w")
        f.write(data)
        f.close()


    def databaseUpdate(self):
        self.log.debug("databaseUpdate: updating our stuff - not used")
        # first get all our files into a dict
        print(self.files_output)
        filesDict = []
        for root, dirs, files in os.walk(self.files_output):
            for name in files:
                sha1 = self.getSha1(root+"/"+name)
                
                if not sha1:
                    print("Could not get sha1")
                    continue

                filesDict.append({
                    "root": root,
                    "name": name,
                    "sha1": sha1,
                })
                print(self.getSha1(root+"/"+name))

        # loop over our config
        print(self.db)
        for mFile in self.db["files"]:
            # if the files does not exists, check our filesDict for the same
            # NOT IMPLEMENTED
            if not self.fileExists(mFile["path"]+mFile["name"]):
                print("File "+mFile["name"]+" might have been moved")

    def databaseFileExists(self, fileid):
        if self.findFile(fileid = fileid):
            return True
        else:
            return False

    def sanitizeFilenames(self, filename):
        self.log.debug("input filename: %s",filename)
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
        filename = filename.lower()

        # remove all puncution chars
        for char in punc:
            filename = filename.replace(char, "")

        # replace chars
        for rep in reps:
            filename = filename.replace(rep[0], rep[1])

        # replace double `-`
        strLen = len(filename)
        while True:
            filename = filename.replace("--", "-")
            
            if len(filename) == strLen:
                break
            strLen = len(filename)

        self.log.debug("new filename: %s",filename)

        return filename


    def getFile(self, url, outputFolder):
        self.log.debug("Getting file with url - %s", url)
        # fileUrl = self.url_base+"mod/resource/view.php?id="+fileid
        fileUrl = url
        local_filename = 'tmp-file.unknown'

        headers = {}
        fileInfo = self.findFile(href = fileUrl)

        if fileInfo:
            headers["If-None-Match"] = fileInfo["etag"]
            self.log.debug("Using etag - %s", fileInfo["etag"])

        r = self.s.get(fileUrl, stream=True, headers=headers)

        if r.status_code == 304:
            self.log.debug("getFile: server responded with status_code 304, do nothing")
            return False

        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    #f.flush() commented by recommendation from J.F.Sebastian

        if r.status_code != 200:
            self.log.error("Could not get file..")
            print(r.text)
            print(r.status_code)
            return False

        d = r.headers["content-disposition"]
        fname = re.findall("filename=(.+)", d)
        fname = fname[0][1:-1]
        
        # exists
        if fileInfo:
            fileInfo["name"] = fname
            fileInfo["path"] = self.files_output+outputFolder
            fileInfo["sha1"] = self.getSha1(local_filename)
            fileInfo["etag"] = r.headers["Etag"]
            fileInfo["href"] = fileUrl
        # add entry
        else:
            self.db["files"].append({
                "fileid": "",
                "name": fname,
                "path": self.files_output+outputFolder,
                "sha1": self.getSha1(local_filename),
                "etag": r.headers["Etag"],
                "href": fileUrl,
            })

        output = self.files_output+outputFolder+"/"+fname 
        output = self.sanitizeFilenames(output)
        print(output)
        os.rename(local_filename, output)
        self.log.debug("Got files, renaming from %s to %s", local_filename, output)

        return True

    def login(self):
        url = self.url_base+"my"

        req = self.s.get(url)
        loginUrl = req.url
        bs = BeautifulSoup(req.text, "html.parser")

        fieldExecution = bs.find("input", {"type": "hidden", "name": "execution"}, "html.parser")
        fieldExecution= fieldExecution['value']

        data = {
            "username": self.username,
            "password": self.password,
            "execution": fieldExecution,
            "_eventId": "submit",
            "geolocation": "",
            "submit": "LOGIN",
        }

        req = self.s.post(loginUrl, data=data)

        if req.url.startswith("https://moodle.aau.dk"):
            self.loggedin = True
            return True
        return False


    def parseCourse(self, semesterTitle, courseTitle, courseHref):
        outputFolder = semesterTitle+"/"+courseTitle
        self.makeDir(outputFolder)
        courseUrl = self.url_base+courseHref

        req = self.s.get(courseUrl)
        
        bs = BeautifulSoup(req.text, "html.parser")

        for section in bs.findAll("li", {"class": "section"}):
            sectionContent = section.find("div", {"class": "content"})
            sectionSummary = sectionContent.find("div", {"class": "summary"}).getText().strip()
            sectionName = sectionContent.find("h3", {"class": "sectionname"}).getText().strip()
            sectionNumber = section["id"][8:]
            print("- "+sectionNumber+"-"+sectionName)
            sectionOutput = outputFolder+"/"+sectionNumber+"-"+sectionName+"/"
            self.makeDir(sectionOutput)

            if sectionSummary:
                self.fileWrite(sectionOutput+"summary.txt", sectionSummary)

            for r in sectionContent.findAll("li", {"class": "modtype_resource"}):
                resource = self.modtype.resource(r)
                self.getFile(resource["link"], sectionOutput)

            for r in sectionContent.findAll("li", {"class": "modtype_page"}):
                resource = self.modtype.page(r)
                if resource:
                    self.fileWrite(sectionOutput+resource["name"], resource["text"]) 

            for r in sectionContent.findAll("li", {"class": "modtype_folder"}):
                resource = self.modtype.folder(r)

                if not resource:
                    continue

                resourceDir = sectionOutput+resource["name"]+"/"

                self.makeDir(resourceDir)
                if resource["text"]:
                    self.fileWrite(resourceDir+"summary.txt", resource["text"])

                for fFile in resource["files"]:
                    self.getFile(fFile["link"], resourceDir)


    def parseSemesters(self):
        req = self.s.get(self.url_base+"my")
        bs = BeautifulSoup(req.text, "html.parser")
        semesterUl = bs.find("ul", {"id": "semester_category_header"})
        semesters = []

        for semester in semesterUl.findAll("li"):
            semesterLink = semester.find("a")
            semesterText = semesterLink.getText()
            semesterHref = semesterLink["href"]
            semesterHref = semesterHref[1:]
            semesterDict = {
                    "text": semesterText,
                    "href": semesterHref,
                    "courses": [],
            }
            print("- "+semesterDict["text"])

            semesterContent = bs.find("div", {"class": "semester_category", "id": semesterHref})

            for course in semesterContent.findAll("div", {"class": "box coursebox"}):
                courseInfo = course.find("h2", {"class": "title"})
                courseTitle = courseInfo.getText()
                courseTitleSan = courseTitle[:courseTitle.rfind("(")-1]

                courseLink = courseInfo.find("a")["href"][1:]
                courseTeachers = course.find("div", {"class": "teacher_info"}).getText()[10:].split(", ")
                courseDict = {
                        "title": courseTitle,
                        "link": courseLink,
                        "teachers": courseTeachers,
                }
                semesterDict["courses"].append(courseDict)

                print("\t - "+courseTitleSan)
                self.parseCourse(semesterText, courseTitleSan, courseLink)


            semesters.append(semesterDict)

        return semesters

    # def parseSemesterClasses(self, semesterHref):


        


username = os.getenv("MOODLE_USERNAME", "username")
password = os.getenv("MOODLE_PASSWORD", "password")

x = moodle(username, password)
x.login()
try: 
    semesters = x.parseSemesters()
except KeyboardInterrupt:
    raise
except:
    raise
finally:
    x.databaseSave()
# x.parseCourse("test", "test2", "course/view.php?id=27104")
# x.test()
# x.getFile("https://www.moodle.aau.dk/pluginfile.php/1358289/mod_resource/content/1/LinCir18_pres.pdf")
