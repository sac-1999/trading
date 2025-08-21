from sklearn.utils import shuffle
import utils
import pandas as pd
import financetrainer

label = ['label']
balance = 1
risk = 1
reportlist = []
bestrr = 2

def mymatric(y_test, y_pred):
    if isinstance(y_test, pd.Series):
        y_test = y_test.to_frame(name='label')
    elif 'label' not in y_test.columns:
        y_test = y_test.rename(columns={y_test.columns[0]: 'label'})
    y_test['pred'] = y_pred.astype(bool)
    y_test = y_test[y_test['pred']]
    favoourtrade = y_test[y_test['label']]
    print(f"Accuracy of my system : {round(len(favoourtrade)/len(y_test)*100,2)} % in trade :{len(y_test)}")

def report_builder(y_test, y_pred):
    global balance
    y_test = y_test.values.ravel()
    for i in range(len(y_pred)):
        actual = y_test[i]
        predicted = y_pred[i]
        if predicted:
            if actual:
                balance = balance + bestrr * risk
            else:
                balance = balance - risk
            reportlist.append(balance)    

def run(df_train, df_test, features, label, params = None, optimizer_type = 'grid'):
    x_train = df_train[features]
    y_train = df_train[label]
    x_test = df_test[features]
    y_test = df_test[label]
    
    x_train, y_train = shuffle(x_train, y_train, random_state=42)
    x_test, y_test = shuffle(x_test, y_test, random_state=42)

    mymodel = financetrainer.XGBClassifierModel(gridparams=params)
    mymodel.train(x_train, y_train, optimizer_type=optimizer_type, cv=5, n_iter = 100)
    y_pred = mymodel.predict(x_test)
    # report_builder(y_test.copy(), y_pred)
    mymatric(y_test.copy(),y_pred)