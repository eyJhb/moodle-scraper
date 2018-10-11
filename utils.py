import hashlib
import string
import os
import re

class Utils(object):
    def __init__(self, p):
        self.p = p

    def makeDir(self, path):
        os.makedirs(self.p.files_output+path, exist_ok=True)

    def fileWrite(self, filePath, text):
        with open(self.p.files_output+filePath, "w") as f:
            f.write(text)
        return True

    def fileExists(self, filePath):
        if os.path.isfile(filePath):
            return True
        return False

    def folderExists(self, path):
        if os.path.isdir(path):
            return True
        return False

    def getSha1(self, filePath):
        filePath = filePath
        if not self.fileExists(filePath):
            return False

        hashSha1 = hashlib.sha1()
        with open(filePath, 'rb') as afile:
            buf = afile.read()
            hashSha1.update(buf)
        return hashSha1.hexdigest()

    def findFile(self, fileid = None, href = None, etag = None, sha1 = None):
        for mFile in self.p.db["files"]:
            if (href and mFile["href"] == href or
                etag and mFile["etag"] == etag or 
                fileid and mFile["fileid"] == fileid or
                sha1 and mFile["sha1"] == sha1):

                return mFile

        return False

    def sanitizeInput(self, inputText):
        self.p.log.debug("sanitizeInput: input %s",inputText)

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

        self.p.log.debug("sanitizeInput: output %s",inputText)

        return inputText

    def getFile(self, url, outputFolder):
        self.p.log.debug("Getting file with url - %s", url)
        # fileUrl = self.url_base+"mod/resource/view.php?id="+fileid
        fileUrl = url
        local_filename = 'tmp-file.unknown'

        headers = {}
        fileInfo = self.findFile(href = fileUrl)

        if fileInfo:
            headers["If-None-Match"] = fileInfo["etag"]
            self.p.log.debug("Using etag - %s", fileInfo["etag"])

        r = self.p.s.get(fileUrl, stream=True, headers=headers)

        if r.status_code == 304:
            self.p.log.debug("getFile: server responded with status_code 304, do nothing")
            return False

        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    #f.flush() commented by recommendation from J.F.Sebastian

        if r.status_code != 200:
            self.p.log.error("Could not get file..")
            print(r.text)
            print(r.status_code)
            return False

        d = r.headers["content-disposition"]
        fname = re.findall("filename=(.+)", d)
        fname = fname[0][1:-1]
        
        # exists
        if fileInfo:
            fileInfo["name"] = fname
            fileInfo["path"] = self.p.files_output+outputFolder
            fileInfo["sha1"] = self.getSha1(local_filename)
            fileInfo["etag"] = r.headers["Etag"]
            fileInfo["href"] = fileUrl
        # add entry
        else:
            self.p.db["files"].append({
                "fileid": "",
                "name": fname,
                "path": self.p.files_output+outputFolder,
                "sha1": self.getSha1(local_filename),
                "etag": r.headers["Etag"],
                "href": fileUrl,
            })

        output = self.p.files_output+outputFolder+"/"+fname 
        output = output
        os.rename(local_filename, output)
        self.p.log.debug("Got files, renaming from %s to %s", local_filename, output)

        return True
