from bs4 import BeautifulSoup
import urllib

class Modtype(object):
    def __init__(self, p):
        self.p = p

    def getFileid(self, url):
        try:
            par = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            return par["id"][0]
        except:
            return False

    def resource(self, bs):
        # remove accesshide
        resourceAccesshide = bs.find("span", {"class": "accesshide"})
        if resourceAccesshide:
            resourceAccesshide.decompose()

        link = bs.find("a")["href"]
        fileid = self.getFileid(link)
        name = bs.find("span", {"class": "instancename"}).getText()
        name = self.p.utils.sanitizeInput(name)
        
        if not fileid:
            self.p.log.error("Could not get fileid for url - %s", resourceLink)
            return False

        return {"name": name, "link": link, "fileid": fileid}


    def page(self, bs):
        resourceAccesshide = bs.find("span", {"class": "accesshide"})
        if resourceAccesshide:
            resourceAccesshide.decompose()

        link = bs.find("a")["href"]
        name = bs.find("span", {"class": "instancename"}).getText()
        name = self.p.utils.sanitizeInput(name)

        req = self.p.s.get(link)
        bsPage = BeautifulSoup(req.text, "html.parser")
        mainContent = bsPage.find("div", {"role": "main"})

        if not mainContent:
            return False

        return {"link": link, "name": name, "text": mainContent.getText().strip()}

    def folder(self, bs):
        # remove accesshide
        resourceAccesshide = bs.find("span", {"class": "accesshide"})
        if resourceAccesshide:
            resourceAccesshide.decompose()

        link = bs.find("a")["href"]
        name = bs.find("span", {"class": "instancename"}).getText()
        name = self.p.utils.sanitizeInput(name)
        #remove any `.` in foldernames
        name = name.replace(".", "")

        # get folder
        req = self.p.s.get(link)
        bsFolder = BeautifulSoup(req.text, "html.parser")
        mainContent = bsFolder.find("div", {"role": "main"})
        text = mainContent.find("div", {"class": "generalbox"})

        if text:
            text = text.getText()
        else:
            text = ""

        folder = mainContent.find("div", {"class": "foldertree"})
        files = []
        if folder:
            for folderFile in folder.findAll("span", {"class": "fp-filename-icon"}):
                fileLink = folderFile.find("a")["href"]
                fileName = folderFile.find("span", {"class": "fp-filename"}).getText()
                fileName = self.p.utils.sanitizeInput(fileName)
                files.append({"name": fileName, "link": fileLink})


        return {"name": name, "link": link, "files": files, "text": text}

