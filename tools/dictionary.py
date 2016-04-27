import sqlite3
import re

database = '/tmp/wifimap.db'
dico = 'fr-moderne.dic'

dic_raw = open(dico).read()

dic = []

res = re.findall("(.*)\/\d+", dic_raw)
if res is not None:
  for m in res:
    dic.append(m)

res = re.findall("^(\w*)\s\d+", dic_raw, re.M)
if res is not None:
  for m in res:
    dic.append(m)

dic.sort(lambda x,y: cmp(len(x), len(y)))


db = sqlite3.connect(database, check_same_thread=False)
query = db.cursor()

res = {}
res_all = []

for word in reversed(dic):
  if len(word) > 4:
    q = '''select * from wifis where essid like "%%%s%%"'''%word
    query.execute(q)
    networks = query.fetchall()
    count = len(networks)
    if count != 0:
      for n in networks:
        if n[1] not in res_all:
          if not res.has_key(word):
            res[word] = []
          res[word].append(n[1])
          res_all.append(n[1])
    
    q = '''select * from probes where essid like "%%%s%%"'''%word
    query.execute(q)
    networks = query.fetchall()
    count = len(networks)
    if count != 0:
      for n in networks:
        if n[1] not in res_all:
          if not res.has_key(word):
            res[word] = []
          res[word].append(n[1])
          res_all.append(n[1])
  
for word in res:
  print "\n\n==== %s ===="%word
  for n in res[word]:
    print n