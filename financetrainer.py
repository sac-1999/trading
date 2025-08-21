from abc import ABC, abstractmethod
from sklearn.tree import DecisionTreeClassifier
import optmizers

class FinanceTrainer(ABC):
    @abstractmethod
    def train(self):
        pass

    @abstractmethod
    def predict(self):
        pass

class DecisionTree(FinanceTrainer):
    def __init__(self, gridparams = None):
        self.model = DecisionTreeClassifier(class_weight='balanced', random_state=42)
        self.gridparams = gridparams

    def train(self, x_train, y_train, scoring = 'recall', cv = 5, optimizer_type = "random", n_iter = 100):
        myoptimizer = None
        if optimizer_type == "grid":
            myoptimizer = optmizers.M_GridSearchCV()
            myoptimizer.optimize(x_train, y_train, self.model, self.gridparams, scoring, cv = 5)
        elif optimizer_type == "random":
            myoptimizer = optmizers.M_RandomSearchCV()
            myoptimizer.optimize(x_train, y_train, self.model, self.gridparams, scoring, cv = 5, n_iter= n_iter)
        else:
            raise ValueError("Enter correct search method : options ['random', 'grid']")

        self.model = myoptimizer.bestmodel
        # print(f"[optimizer used ::{optimizer_type}]  best params :", myoptimizer.bestparams)

    def predict(self, x_test):
        return self.model.predict(x_test)

    
       
from sklearn.ensemble import RandomForestClassifier

class RandomForest(FinanceTrainer):
    def __init__(self, gridparams=None):
        self.model = RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1)
        self.gridparams = gridparams

    def train(self, x_train, y_train, scoring='recall', cv=5, optimizer_type="random", n_iter=100):
        myoptimizer = None
        y_train = y_train.values.ravel()

        if optimizer_type == "grid":
            myoptimizer = optmizers.M_GridSearchCV()
            myoptimizer.optimize(x_train, y_train, self.model, self.gridparams, scoring, cv=cv)
        elif optimizer_type == "random":
            myoptimizer = optmizers.M_RandomSearchCV()
            myoptimizer.optimize(x_train, y_train, self.model, self.gridparams, scoring, cv=cv, n_iter=n_iter)
        else:
            raise ValueError("Enter correct search method: options ['random', 'grid']")

        self.model = myoptimizer.bestmodel
        # print(f"[optimizer used ::{optimizer_type}]  best params :", myoptimizer.bestparams)

    def predict(self, x_test):
        return self.model.predict(x_test)
    

from xgboost import XGBClassifier

class XGBClassifierModel(FinanceTrainer):
    def __init__(self, gridparams=None):
        self.model = XGBClassifier(
                        objective='binary:logistic',
                        eval_metric='logloss',
                        n_jobs=-1,
                        random_state=42
                    )

        self.gridparams = gridparams

    def train(self, x_train, y_train, scoring='recall', cv=5, optimizer_type="random", n_iter=100):
        myoptimizer = None
        y_train = y_train.values.ravel()

        if optimizer_type == "grid":
            myoptimizer = optmizers.M_GridSearchCV()
            myoptimizer.optimize(x_train, y_train, self.model, self.gridparams, scoring, cv=cv)
        elif optimizer_type == "random":
            myoptimizer = optmizers.M_RandomSearchCV()
            myoptimizer.optimize(x_train, y_train, self.model, self.gridparams, scoring, cv=cv, n_iter=n_iter)
        else:
            raise ValueError("Enter correct search method: options ['random', 'grid']")

        self.model = myoptimizer.bestmodel

    def predict(self, x_test):
        return self.model.predict(x_test)