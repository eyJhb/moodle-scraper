import json

class Database(object):
    def __init__(self, p):
        self.p = p

    def load(self):
        self.p.log.debug("databaseLoad: loading database")

        f = open(self.p.files_database, "r")
        data = f.read()
        f.close()

        return json.loads(data)

    def save(self):
        self.p.log.debug("databaseSave: saving database")
        data = json.dumps(self.p.db)

        f = open(self.p.files_database, "w")
        f.write(data)
        f.close()

