from Contants import SETTINGS_FILE

def getParameter(key):
    with open(SETTINGS_FILE) as f:
        res=list(filter(lambda l: key in l,f.readlines()))
        if len(res)>0:
            return res[0].split('=')[-1].replace('"','')
    return ''

def setParameter(key, value):
    with open(SETTINGS_FILE,'a') as f:
        f.write(f'\n{key}="{value}"')

def getLogFile(log):
    return getParameter(log)