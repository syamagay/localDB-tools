import datetime

def setTime(date):
    DIFF_FROM_UTC = 9
    time = (date+datetime.timedelta(hours=DIFF_FROM_UTC)).strftime("%Y/%m/%d %H:%M:%S")
    return time
