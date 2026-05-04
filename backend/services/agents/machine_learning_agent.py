"""Machine Learning agent definition."""

from .base_agent import BaseAgent


class MachineLearningAgent(BaseAgent):
    label = "Machine Learning"
    system = (
        "You are an expert Machine Learning tutor specializing in "
        "supervised/unsupervised learning, model evaluation, feature engineering, "
        "Scikit-learn, ensemble methods, and classical ML algorithms. "
        "Always explain the intuition before diving into mathematics."
    )
    keywords = [
        'machine learning', 'supervised', 'unsupervised', 'regression',
        'classification', 'clustering', 'random forest', 'decision tree',
        'svm', 'knn', 'k-means', 'pca', 'feature', 'training', 'testing',
        'cross-validation', 'overfitting', 'underfitting', 'scikit', 'sklearn',
        'ensemble', 'boosting', 'bagging', 'xgboost', 'lightgbm',
    ]