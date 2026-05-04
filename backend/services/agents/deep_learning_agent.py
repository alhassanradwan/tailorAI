"""Deep Learning agent definition."""

from .base_agent import BaseAgent


class DeepLearningAgent(BaseAgent):
    label = "Deep Learning"
    system = (
        "You are an expert Deep Learning tutor specializing in neural networks, "
        "backpropagation, CNNs, RNNs/LSTMs, Transformers, TensorFlow, PyTorch, "
        "transfer learning, and modern architectures (ResNet, BERT, GPT). "
        "Balance mathematical rigor with practical intuition."
    )
    keywords = [
        'deep learning', 'neural network', 'cnn', 'rnn', 'lstm', 'transformer',
        'backpropagation', 'gradient descent', 'activation', 'relu', 'sigmoid',
        'tensorflow', 'pytorch', 'keras', 'epoch', 'batch', 'dropout', 'layer',
        'convolution', 'attention', 'bert', 'gpt', 'embedding', 'gan',
    ]