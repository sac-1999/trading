input_list = [[1,2],[3,4], [[4],[6]]]
# input_list = [1,2]                               
# output = [1,2,3,4,4,6]



def create(input):
    print(input)
    if input is None:
        return []
    if type(input)!=list:
        return [input]
    if len(input) == 0:
        return []
    
    final1 = create(input[0])
    final2 = create(input[1:])
    final1.extend(final2)
    return final1 
    

print(create(input_list))


# lst1 = [1,2,3,4]
# lst2 = ['IT','Ops','IT','Ops']
# lst3 = [5000,5500,6000,4000]
# lst4 = ['BLR','CHN','DLH','HYD']
# columns = ['EmpID', 'Dept', 'Sal', 'City']

# dict = {}
# allelem = [lst1, lst2, lst3, lst4]
# for i, col in enumerate(columns):
#     dict[col] = allelem[i]

# import pandas as pd
# df = pd.DataFrame(dict)
# print(df)
# print('---'*10)
# print(df.groupby('Dept').agg('Sal').sum())

