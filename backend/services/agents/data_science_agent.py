"""Data Science agent definition."""

from .base_agent import BaseAgent


class DataScienceAgent(BaseAgent):
    label = "Data Science"
    system = (
        "You are an expert Data Science tutor specializing in EDA, "
        "data cleaning, statistics, visualization (Matplotlib, Seaborn, Plotly), "
        "Pandas, NumPy, and feature engineering. "
        "You are the SUPERVISOR agent that oversees the learning path. "
        "Always provide practical Python code examples when relevant."
    )
    keywords = [
        'data', 'pandas', 'numpy', 'visualization', 'eda', 'exploratory',
        'statistics', 'correlation', 'distribution', 'cleaning', 'preprocessing',
        'matplotlib', 'seaborn', 'plotly', 'csv', 'dataframe', 'analysis',
        'sql', 'query', 'database', 'join', 'missing values', 'outlier',
    ]