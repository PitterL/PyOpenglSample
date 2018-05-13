import os
import re

class CData():
    PAT_FLOAT = '-?\d+\.?\d*[fF]?'

    def __init__(self, filename=None):
        self.f = None
        self.content = None

        if filename:
            self.open(filename)

    def open(self, filename):
        if not filename:
            return

        path = '\\'.join(os.path.curdir, filename)
        if os.path.exists(path):
            self.f = open(path, 'r')

    def close(self):
        if self.f:
            close(self.f)
            self.f = None

    def load(self):
        self.content = self.f.readlines()

    @classmethod
    def load_c_array(cls, c_arr_content=None):
        output = []

        if not c_arr_content:
            return

        lines = re.split('[\r\n]', c_arr_content)
        pat = re.compile(cls.PAT_FLOAT)
        for line in map(str.strip, lines):
            if not line or line.isspace():
                continue

            words = re.split('[ ,\t]', line)
            for w in map(str.strip, words):
                if not w or w.isspace():
                    continue

                if w.startswith('//'):
                    break

                if pat.match(w):
                    value = float(w[:-1])
                    output.append(value)
                else:
                    print('unknow text:', w)


        return output
