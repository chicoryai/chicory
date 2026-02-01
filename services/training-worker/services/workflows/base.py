import abc


class BaseAgent(metaclass=abc.ABCMeta):
    def __init__(self):
        pass

    @abc.abstractmethod
    def talk(self, message: dict):
        pass