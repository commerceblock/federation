#!/usr/bin/env python3
from importlib import import_module
from abc import ABC
from .messenger import Messenger

class MessengerFactory(ABC):
    @staticmethod
    def get_messenger(name, *args, **kwargs):
        try:
            module_name = name + 'messenger'
            class_name = name.capitalize() + 'Messenger'
            messenger_module = import_module('.' + module_name, package='federation')
            messenger_class = getattr(messenger_module, class_name)
            instance = messenger_class(*args, **kwargs)

        except (AttributeError, ModuleNotFoundError):
            raise ImportError('{} messenger type not supported'.format(name))
        else:
            if not issubclass(messenger_class, Messenger):
                raise ImportError("currently don't have {}.".format(animal_class))

        return instance

