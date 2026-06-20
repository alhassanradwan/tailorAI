_TOPIC_TO_AGENT: list[tuple[list[str], str]] = [
    (["deep learning", "neural network", "cnn", "rnn", "lstm", "transformer",
      "backpropagation", "convolutional", "recurrent", "attention", "bert",
      "gpt", "autoencoder", "gan"], "deep_learning"),
    (["machine learning", "regression", "classification", "clustering",
      "svm", "decision tree", "random forest", "gradient boosting", "xgboost",
      "knn", "naive bayes", "ensemble", "cross-validation", "overfitting",
      "underfitting", "bias variance"], "machine_learning"),
    (["data science", "pandas", "numpy", "matplotlib", "seaborn",
      "exploratory data analysis", "eda", "data cleaning", "feature engineering",
      "statistics", "hypothesis testing", "sql", "data wrangling",
      "visualization"], "data_science"),
]

_DEFAULT_AGENT_KEY = "machine_learning"


def topic_to_agent_key(topic: str) -> str:
    tl = topic.lower()
    for keywords, key in _TOPIC_TO_AGENT:
        if any(kw in tl for kw in keywords):
            return key
    return _DEFAULT_AGENT_KEY