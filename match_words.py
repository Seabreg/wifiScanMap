dico = 'dico.txt'
db = 'sorted.csv'
min_length = 4

from multiprocessing import Pool

content = []
with open(dico) as f:
  content = f.readlines()

words = []
for c in content:
  words.append(c.rstrip('\r\n'))


essids = []
with open(db) as f:
  content = f.readlines()

for c in content:
  essids.append(c.rstrip('\r\n'))


words.sort() # sorts normally by alphabetical order
words.sort(key=len, reverse=True) # sorts by descending length

essids.sort() # sorts normally by alphabetical order
essids.sort(key=len, reverse=True) # sorts by descending length

#words = words[:100]

def check_word(w):
  result = []
  for e in essids:
    if len(w) < min_length:
      break
    
    if len(e) < len(w):
      break
    
    if w in e:
      print e
      result.append(e)
      essids.remove(e)
  return result

pool = Pool(processes=3)

res = []
for w in words:
  res.append(pool.apply_async(check_word, [w]))
  #check_word(w)

results = []
for r in res:
  partial = r.get(timeout=1)
  results = results + partial
  
print "========================================="
for r in results:
  print r