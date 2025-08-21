from abc import ABC, abstractmethod
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

class Optimizers(ABC):
    @abstractmethod
    def optimize(self):
        pass
    
    @abstractmethod
    def getBestParmas(self):
        pass

    @abstractmethod
    def predict():
        pass
    

class M_GridSearchCV(Optimizers):
    def __init__(self):
        self.bestmodel = None
        self.bestparams = None

    def optimize(self, x_train, y_train, model, params, scoring, cv):
        grid_search = GridSearchCV(estimator=model, param_grid=params, 
                           cv=cv, n_jobs=-1, verbose=1, scoring=scoring)
        grid_search.fit(x_train, y_train)
        best_dtree_reg = grid_search.best_estimator_
        self.bestmodel = best_dtree_reg
        self.bestparams = grid_search.best_params_

    def getBestParmas(self):
        return self.bestparams
    
    def predict(self, x_test):
        return self.bestmodel.predict(x_test)


class M_RandomSearchCV(Optimizers):
    def __init__(self):
        self.bestmodel = None
        self.bestparams = None

    def optimize(self, x_train, y_train, model, params, scoring, cv , n_iter):
        random_search = RandomizedSearchCV(model, params,n_iter=n_iter, 
                                          cv = cv, verbose=1, scoring=scoring)
        random_search.fit(x_train, y_train)
        self.bestmodel = random_search.best_estimator_
        self.bestparams = random_search.best_params_

    def getBestParmas(self):
        return self.bestparams
    
    def predict(self, x_test):
        return self.bestmodel.predict(x_test)
    