import requests
from bs4 import BeautifulSoup
import logging
import json
import os
import re
from modtypeParser import Modtype
from utils import Utils 
from database import Database

logging.basicConfig()

class moodle(object):
    def __init__(self, username, password):
        self.s = requests.session()

        self.url_base = "https://www.moodle.aau.dk/"

        self.username = username
        self.password = password
        self.loggedin = False

        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)

        self.modtype = Modtype(self)
        self.utils = Utils(self)
        self.database = Database(self)


        self.files_database = "database.json"
        self.files_output = "files/"

        self.db = self.database.load()
        self.log.debug("test")
        if not self.initCheck():
            logging.error("Could not initialize Moodle")
            exit()

    def initCheck(self):
        #check that we have our database file
        if not self.utils.fileExists(self.files_database):
            self.log.error("Our database file '%s' does not exists", self.files_database)
            return False
        #check for our {files: []} in our json
        try:
            self.db["files"]
        except:
            self.log.error("Our database does not contain {\"files\": []}")
            return False
        
        #check that our files_output exist
        if not self.utils.folderExists(self.files_output):
            self.log.error("Output folder '%s' does not exists", self.files_output)
            return False

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

        if req.url.startswith("https://www.moodle.aau.dk"):
            self.loggedin = True
            return True
        return False


    def parseCourse(self, semesterTitle, courseTitle, courseHref):
        if self.loggedin == False:
            return False

        outputFolder = semesterTitle+"/"+courseTitle
        self.utils.makeDir(outputFolder)

        courseUrl = self.url_base+courseHref
        req = self.s.get(courseUrl)
        bs = BeautifulSoup(req.text, "html.parser")

        for section in bs.findAll("li", {"class": "section"}):
            sectionContent = section.find("div", {"class": "content"})
            sectionSummary = sectionContent.find("div", {"class": "summary"}).getText().strip()
            sectionName = sectionContent.find("h3", {"class": "sectionname"}).getText().strip()
            sectionName = self.utils.sanitizeInput(sectionName)
            # replace all `.` in sectionNames
            sectionName = sectionName.replace(".", "")
            sectionNumber = section["id"][8:]

            sectionOutput = outputFolder+"/"+sectionNumber+"-"+sectionName+"/"
            self.utils.makeDir(sectionOutput)

            if sectionSummary:
                self.utils.fileWrite(sectionOutput+"summary.txt", sectionSummary)

            for r in sectionContent.findAll("li", {"class": "modtype_resource"}):
                resource = self.modtype.resource(r)
                self.utils.getFile(resource["link"], sectionOutput)

            for r in sectionContent.findAll("li", {"class": "modtype_page"}):
                resource = self.modtype.page(r)
                if resource:
                    self.utils.fileWrite(sectionOutput+resource["name"], resource["text"]) 

            for r in sectionContent.findAll("li", {"class": "modtype_folder"}):
                resource = self.modtype.folder(r)

                if not resource:
                    continue

                resourceDir = sectionOutput+resource["name"]+"/"

                self.utils.makeDir(resourceDir)
                if resource["text"]:
                    self.utils.fileWrite(resourceDir+"summary.txt", resource["text"])

                for fFile in resource["files"]:
                    self.utils.getFile(fFile["link"], resourceDir)


    def parseSemesters(self):
        if self.loggedin == False:
            return False

        req = self.s.get(self.url_base+"my")
        bs = BeautifulSoup(req.text, "html.parser")
        semesterUl = bs.find("ul", {"id": "semester_category_header"})
        semesters = []

        for semester in semesterUl.findAll("li"):
            semesterLink = semester.find("a")
            semesterName = semesterLink.getText()
            semesterName = self.utils.sanitizeInput(semesterName)
            semesterHref = semesterLink["href"]
            semesterHref = semesterHref[1:]
            semesterDict = {
                    "name": semesterName,
                    "href": semesterHref,
                    "courses": [],
            }
            print("- "+semesterDict["name"])

            semesterContent = bs.find("div", {"class": "semester_category", "id": semesterHref})

            for course in semesterContent.findAll("div", {"class": "box coursebox"}):
                courseInfo = course.find("h2", {"class": "title"})
                courseName = courseInfo.getText()
                courseNameSan = courseName[:courseName.rfind("(")-1]
                courseName = self.utils.sanitizeInput(courseName)
                courseNameSan = self.utils.sanitizeInput(courseNameSan)

                courseLink = courseInfo.find("a")["href"][1:]
                courseTeachers = course.find("div", {"class": "teacher_info"}).getText()[10:].split(", ")
                courseDict = {
                        "name": courseName,
                        "link": courseLink,
                        "teachers": courseTeachers,
                }
                semesterDict["courses"].append(courseDict)

                print("\t - "+courseNameSan)
                self.parseCourse(semesterName, courseNameSan, courseLink)


            semesters.append(semesterDict)

        return semesters

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
    x.database.save()
