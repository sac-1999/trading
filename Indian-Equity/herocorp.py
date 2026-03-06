s = "aabbcdddeeeiii"


lastchar = None
count = 0
final = ''
for i in s:
    if lastchar is None:
        lastchar = i
        count = 1
        continue
    if lastchar ==i:
        count +=1
    else:
        final += lastchar + str(count)
        count = 1
        lastchar = i
final += lastchar + str(count)
print(final)


    
