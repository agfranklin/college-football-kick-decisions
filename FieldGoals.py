import pandas as pd
import csv
import numpy as np
from sklearn.externals import joblib
import os.path
import matplotlib.pyplot as plt
import glob
from ImportFiles import SelectColumnsFromMultipleFiles
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import f_regression
from sklearn.metrics import classification_report

#sklearn.svm.LinearSVC
#from sas7bdat import SAS7BDAT

#sudo pip install pandas
def GetFieldGoalDrives():
    driveFiles = glob.glob("./data/drives/*.csv")

    drives = SelectColumnsFromMultipleFiles(driveFiles, ["End Period", "End Clock", "End Spot", "End Reason"]) #usecols=["End Period", "End Clock", "End Spot", "End Reason", "Plays", "Yards", "Time Of Possession"]

    fieldGoalDrives = drives.loc[(drives["End Reason"] == "FIELD GOAL") | (drives["End Reason"] == "MISSED FIELD GOAL")]

    fieldGoalDrives["End Reason"].replace(["FIELD GOAL", "MISSED FIELD GOAL"], [1, 0], inplace=True)
    fieldGoalDrives.fillna({"End Clock":0}, inplace=True)

    return fieldGoalDrives

def GetTestAndTrainSets():
    fieldGoalDrives = GetFieldGoalDrives()

    y = fieldGoalDrives["End Reason"].values
    X = fieldGoalDrives.drop("End Reason", axis=1).values

    #X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state=42, stratify=y)
    return train_test_split(X, y, test_size = 0.2, random_state=42, stratify=y)

#svc = SVC(kernel="linear",probability=True)
#svc.fit(X_train, y_train)
#prediction = svc.predict(X_test)
#expectedValueOfKick = pd.DataFrame(svc.predict_proba(X_test))[1]*3.0

def ModelExistence(usePersistedModel, filename):
    currentModelExists = True
    if usePersistedModel:
        if not os.path.isfile(filename):
            print(filename+" does not exist so model being created and saved")
            currentModelExists = False
    return currentModelExists

def FieldGoalExpectedValueLogisticRegression(situation, usePersistedModel = False):
    filename = "./models/FieldGoalExpectedValueLogisticRegression.sav"
    currentModelExists = ModelExistence(usePersistedModel,filename)

    if (not usePersistedModel) or (not currentModelExists):
        X_train, X_test, y_train, y_test = GetTestAndTrainSets()
        logistic = LogisticRegression(C=100000)
        logistic.fit(X_train,y_train)
        #persist model
        joblib.dump(logistic, filename)
    else:
        logistic = joblib.load(filename)

    prediction = pd.DataFrame(logistic.predict_proba(np.asarray(situation).reshape(1,-1)))[1]*3
    return prediction.iloc[0]

def FieldGoalExpectedValueKnn(situation, usePersistedModel = False):
    filename = "./models/FieldGoalExpectedValueKnn.sav"
    currentModelExists = ModelExistence(usePersistedModel,filename)

    if (not usePersistedModel) or (not currentModelExists):
        X_train, X_test, y_train, y_test = GetTestAndTrainSets()
        knn = KNeighborsClassifier(n_neighbors=12)
        knn.fit(X_train,y_train)
        #persist model
        joblib.dump(knn, filename)
    else:
        knn = joblib.load(filename)

    prediction = pd.DataFrame(knn.predict_proba(np.asarray(situation).reshape(1,-1)))[1]*3
    return prediction.iloc[0]

def GraphFieldGoalPercentByDistance():
    kicks = {}
    fieldGoalDrives = GetFieldGoalDrives()
    spotCounts = fieldGoalDrives["End Spot"].value_counts()
    for i, drive in fieldGoalDrives.iterrows():
        if drive["End Spot"] in kicks:
            kicks[drive["End Spot"]] += 1.0 if drive["End Reason"] == 1 else 0
        else:
            kicks[drive["End Spot"]] = 1.0 if drive["End Reason"] == 1 else 0

    for key, value in kicks.items():
        kicks[key] = round(kicks[key]/spotCounts[key],3)

    plt.plot(*zip(*sorted(kicks.items()[0:40])))
    plt.title("Percent kicks made from spot of ball")
    plt.legend()
    plt.xlabel("Ball Spot")
    plt.ylabel("Percent of FGs made")
    plt.savefig("./imgs/FieldGoalsMadeEachSpot.png")
    plt.show()

def GraphKnnFieldGoalAccuracy(neighborsCount, usePersistedModel = False):

    # Setup arrays to store train and test accuracies
    neighbors = np.arange(1, neighborsCount)
    train_accuracy = np.empty(len(neighbors))
    test_accuracy = np.empty(len(neighbors))
    X_train, X_test, y_train, y_test = GetTestAndTrainSets()

    # Loop over different values of k
    for i, k in enumerate(neighbors):
        filename = "./models/GraphKnnFieldGoalAccuracy_"+str(k)+".sav"
        currentModelExists = ModelExistence(usePersistedModel,filename)

        if (not usePersistedModel) or (not currentModelExists):
            # Setup a k-NN Classifier with k neighbors: knn
            knn = KNeighborsClassifier(n_neighbors=k)

            # Fit the classifier to the training data
            knn.fit(X_train, y_train)

            #persist model
            joblib.dump(knn, filename)
        else:
            knn = joblib.load(filename)

        #Compute accuracy on the training set
        train_accuracy[i] = knn.score(X_train, y_train)

        #Compute accuracy on the testing set
        test_accuracy[i] = knn.score(X_test, y_test)

    # Generate plot
    plt.title("Kicking Field Goal k-NN: Varying Number of Neighbors")
    plt.plot(neighbors, test_accuracy, label = "Testing Accuracy")
    plt.plot(neighbors, train_accuracy, label = "Training Accuracy")
    plt.legend()
    plt.xlabel("Number of Neighbors")
    plt.ylabel("Accuracy")
    plt.savefig("./imgs/FieldGoalsKnn"+str(neighborsCount)+"Neighbors.png")
    plt.show()

def GraphNaiveBayesFieldGoalAccuracy(maxAlpha, usePersistedModel = False):

    # Setup arrays to store train and test accuracies
    alphas = np.arange(0, (maxAlpha+1))
    train_accuracy = np.empty(len(alphas))
    test_accuracy = np.empty(len(alphas))
    X_train, X_test, y_train, y_test = GetTestAndTrainSets()

    # Loop over different values of k
    for i, a in enumerate(alphas):
        filename = "./models/GraphNaiveBayesFieldGoalAccuracy_"+str(10**float(-a))+".sav"
        currentModelExists = ModelExistence(usePersistedModel,filename)

        if (not usePersistedModel) or (not currentModelExists):
            # Setup a k-NN Classifier with k neighbors: knn
            naiveBayes = MultinomialNB(alpha=10**float(-a))

            # Fit the classifier to the training data
            naiveBayes.fit(X_train, y_train)

            #persist model
            joblib.dump(naiveBayes, filename)
        else:
            naiveBayes = joblib.load(filename)

        #Compute accuracy on the training set
        train_accuracy[i] = naiveBayes.score(X_train, y_train)

        #Compute accuracy on the testing set
        test_accuracy[i] = naiveBayes.score(X_test, y_test)

    # Generate plot
    plt.title("Kicking Field Goal Naive Bayes: Varying alpha")
    plt.plot(alphas, test_accuracy, label = "Testing Accuracy")
    plt.plot(alphas, train_accuracy, label = "Training Accuracy")
    plt.legend()
    plt.xlabel("Alpha")
    plt.ylabel("Accuracy")
    plt.savefig("./imgs/FieldGoalsNaiveBayes"+str(maxAlpha)+"Alphas.png")
    plt.show()

def GraphRandomForestFieldGoalAccuracy(maxEstimators, usePersistedModel = False):

    # Setup arrays to store train and test accuracies
    estimators = np.arange(1, (maxEstimators+1))
    train_accuracy = np.empty(len(estimators))
    test_accuracy = np.empty(len(estimators))
    X_train, X_test, y_train, y_test = GetTestAndTrainSets()

    # Loop over different values of n
    for i, n in enumerate(estimators):
        filename = "./models/GraphRandomForestFieldGoalAccuracy_"+str(n)+".sav"
        currentModelExists = ModelExistence(usePersistedModel,filename)

        if (not usePersistedModel) or (not currentModelExists):

            # Setup a k-NN Classifier with k neighbors: knn
            randomForest = RandomForestClassifier(n_estimators=n, criterion="gini")

            # Fit the classifier to the training data
            randomForest.fit(X_train, y_train)

            #persist model
            joblib.dump(randomForest, filename)
        else:
            randomForest = joblib.load(filename)

        #Compute accuracy on the training set
        train_accuracy[i] = randomForest.score(X_train, y_train)

        #Compute accuracy on the testing set
        test_accuracy[i] = randomForest.score(X_test, y_test)

    # Generate plot
    plt.title("Kicking Field Goal Random Forest Classifier: Varying alpha")
    plt.plot(estimators, test_accuracy, label = "Testing Accuracy")
    plt.plot(estimators, train_accuracy, label = "Training Accuracy")
    plt.legend()
    plt.xlabel("Max Estimators")
    plt.ylabel("Accuracy")
    plt.savefig("./imgs/FieldGoalsRandomForestClassifier"+str(maxEstimators)+"MaxEstimators.png")
    plt.show()

def GraphGaussianProcessFieldGoalAccuracy(kernels, usePersistedModel = False):

    # Setup arrays to store train and test accuracies
    kernels = np.arange(1, (kernels+1))
    train_accuracy = np.empty(len(kernels))
    test_accuracy = np.empty(len(kernels))
    X_train, X_test, y_train, y_test = GetTestAndTrainSets()

    # Loop over different values of k
    for i, k in enumerate(kernels):
        filename = "./models/GraphGaussianProcessFieldGoalAccuracy_"+str(k)+".sav"
        currentModelExists = ModelExistence(usePersistedModel,filename)

        if (not usePersistedModel) or (not currentModelExists):

            # Setup a k-NN Classifier with k neighbors: knn
            gaussianProcess = GaussianProcessClassifier(kernel=k * RBF(length_scale=1.0), optimizer = None)

            # Fit the classifier to the training data
            gaussianProcess.fit(X_train, y_train)

            #persist model
            joblib.dump(gaussianProcess, filename)
        else:
            gaussianProcess = joblib.load(filename)


        #Compute accuracy on the training set
        train_accuracy[i] = gaussianProcess.score(X_train, y_train)

        #Compute accuracy on the testing set
        test_accuracy[i] = gaussianProcess.score(X_test, y_test)

    # Generate plot
    plt.title("Kicking Field Goal Gaussian Process Classifier: Varying alpha")
    plt.plot(kernels, test_accuracy, label = "Testing Accuracy")
    plt.plot(kernels, train_accuracy, label = "Training Accuracy")
    plt.legend()
    plt.xlabel("Alpha")
    plt.ylabel("Accuracy")
    plt.savefig("./imgs/FieldGoalsGaussianProcess"+str(kernels)+"Kernels.png")
    plt.show()

def GraphLogisticRegressionFieldGoalAccuracy(maxC, usePersistedModel = False):
    Cs = np.arange(1, maxC)
    train_accuracy2 = np.empty(len(Cs))
    test_accuracy2 = np.empty(len(Cs))
    X_train, X_test, y_train, y_test = GetTestAndTrainSets()
    # Loop over different values of C
    for i, c in enumerate(Cs):
        filename = "./models/GraphLogisticRegressionFieldGoalAccuracy_"+str(10**c)+".sav"
        currentModelExists = ModelExistence(usePersistedModel,filename)

        if (not usePersistedModel) or (not currentModelExists):

            # Setup a k-NN Classifier with k neighbors: knn
            logistic = LogisticRegression(C=10**c)

            # Fit the classifier to the training data
            logistic.fit(X_train, y_train)

            #persist model
            joblib.dump(logistic, filename)
        else:
            logistic = joblib.load(filename)

        #Compute accuracy on the training set
        train_accuracy2[i] = logistic.score(X_train, y_train)

        #Compute accuracy on the testing set
        test_accuracy2[i] = logistic.score(X_test, y_test)

    # Generate plot
    plt.title("Kicking Field Goal Logistic Regression: Varying value of C")
    plt.plot(Cs, test_accuracy2, label = "Testing Accuracy")
    plt.plot(Cs, train_accuracy2, label = "Training Accuracy")
    plt.legend()
    plt.xlabel("C = 10^x")
    plt.ylabel("Accuracy")
    plt.savefig("./imgs/FieldGoalsLogisticRegression"+str(maxC)+"MaxC.png")
    plt.show()
