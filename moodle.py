import requests
from bs4 import BeautifulSoup
import logging
from modtype import Modtype

logging.basicConfig()

class Moodle(object):
    def __init__(self, username, password):
        self.s = requests.session()

        self.url_base = "https://www.moodle.aau.dk/"

        self.username = username
        self.password = password
        self.loggedin = False

        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)

        self.modtype = Modtype(self)

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


    def course(self, coursehref):
        if self.loggedin == False:
            return False

        courseUrl = self.url_base+coursehref
        req = self.s.get(courseUrl)
        bs = BeautifulSoup(req.text, "html.parser")

        courseDict = []

        for section in bs.findAll("li", {"class": "section"}):
            sectionContent = section.find("div", {"class": "content"})
            sectionSummary = sectionContent.find("div", {"class": "summary"}).getText().strip()
            sectionName = sectionContent.find("h3", {"class": "sectionname"}).getText().strip()
            sectionNumber = section["id"][8:]

            sectionDict = {
                "name": sectionName,
                "number": sectionNumber,
                "summary": sectionSummary,
                "children": [],
            } 


            for r in sectionContent.findAll("li", {"class": "modtype_resource"}):
                resource = self.modtype.resource(r)
                if resource:
                    sectionDict["children"].append(resource)

            for r in sectionContent.findAll("li", {"class": "modtype_page"}):
                resource = self.modtype.page(r)
                if resource:
                    sectionDict["children"].append(resource)

            for r in sectionContent.findAll("li", {"class": "modtype_folder"}):
                resource = self.modtype.folder(r)
                if resource:
                    sectionDict["children"].append(resource)

            courseDict.append(sectionDict)

        return courseDict

    def semesters(self):
        if self.loggedin == False:
            return False

        req = self.s.get(self.url_base+"my")
        bs = BeautifulSoup(req.text, "html.parser")
        semesterUl = bs.find("ul", {"id": "semester_category_header"})
        semesters = []

        for semester in semesterUl.findAll("li"):
            semesterLink = semester.find("a")
            semesterName = semesterLink.getText()
            semesterName = semesterName
            semesterHref = semesterLink["href"]
            semesterHref = semesterHref[1:]
            semesterDict = {
                    "name": semesterName,
                    "href": semesterHref,
                    "courses": [],
            }

            semesterContent = bs.find("div", {"class": "semester_category", "id": semesterHref})

            for course in semesterContent.findAll("div", {"class": "box coursebox"}):
                courseInfo = course.find("h2", {"class": "title"})
                courseName = courseInfo.getText()
                courseNameSan = courseName[:courseName.rfind("(")-1]
                courseName = courseName

                courseLink = courseInfo.find("a")["href"][1:]
                courseTeachers = course.find("div", {"class": "teacher_info"}).getText()[10:].split(", ")
                courseDict = {
                        "name": courseName,
                        "href": courseLink,
                        "teachers": courseTeachers,
                }
                semesterDict["courses"].append(courseDict)

            semesters.append(semesterDict)

        return semesters

    def get(self, url, headers={}):
        req = self.s.get(url, headers=headers)
        return req
        
    def getFile(self, url, tempfile="file.tmp", headers={}):
        self.log.debug("Getting file with url - %s", url)

        r = self.s.get(url, stream=True, headers=headers)

        with open(tempfile, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return r

