"""
@Author: Conghao Wong
@Date: 2020-11-20 09:11:33
@LastEditors: Conghao Wong
@LastEditTime: 2021-07-22 16:27:00
@Description: file content
@Github: https://github.com/conghaowoooong
@Copyright 2021 Conghao Wong, All Rights Reserved.
"""

import os
import time
from argparse import Namespace
from typing import Any, List, Union

from ...helpmethods import dir_check
from . import argParse as ArgParse
from .base import BaseArgs

TIME = time.strftime('%Y%m%d-%H%M%S', time.localtime(time.time()))


class BaseTrainArgs(BaseArgs):
    """
    BaseTrainArgs
    -------------
    The arg class that contains basic args for training universal models.
    """
    def __init__(self, args: Union[Namespace, List[str]],
                 default_args: Union[Namespace, dict] = None):

        super().__init__()

        self._arg_list = [s for s in self.__dir__() if not s.startswith('_')]
        self._arg_list.sort()

        self._args_load = None
        self._force_args = default_args

        if type(args) == Namespace:
            arg_list = ['main.py']
            for key, value in args.__dict__.items():
                arg_list.append('--{}'.format(key))
                arg_list.append('{}'.format(value))
            args = arg_list

        self._args = ArgParse.parse(
            argv=args,
            names=self._arg_list,
            values=[getattr(self, s) for s in self._arg_list])

        if (p := self.load) != 'null':
            try:
                arg_paths = [os.path.join(p, item) for item in os.listdir(p) if (
                    item.endswith('args.npy') or item.endswith('args.json'))]
                self._args_load = ArgParse.load(arg_paths)
            except:
                raise FileNotFoundError('Arg file {} not found'.format(p))

        if self._args.log_dir == 'null':
            log_dir_current = (TIME +
                               self.model_name +
                               self.model +
                               self.test_set)
            self._args.log_dir = os.path.join(dir_check(self.save_base_dir),
                                log_dir_current)
        else:
            dir_check(self._args.log_dir)
    
    def __str__(self) -> str:
        text = ''
        for key, value in self._args.__dict__.items():
            text += '{}: {}, '.format(key, value)
        return text

    @property
    def force_set(self) -> str:
        """
        Force test dataset. 
        Only works on ETH-UCY dataset when arg `load` is not `null`.
        """
        return self._get('force_set', 'null', changeable=True)

    @property
    def gpu(self) -> str:
        """
        Speed up training or test if you have at least one nvidia GPU. 
        Use `_` to separate if you want to use more than one gpus. 
        If you have no GPUs or want to run the code on your CPU, 
        please set it to `-1`.
        """
        return self._get('gpu', '0', changeable=True)

    @property
    def verbose(self) -> int:
        """
        Set if print logs
        """
        return self._get('verbose', 1, changeable=True)

    @property
    def save_base_dir(self) -> str:
        """
        Base saving dir of logs.
        """
        return self._get('save_base_dir', './logs', changeable=False)

    @property
    def save_format(self) -> str:
        """
        Model save format, canbe `tf` or `h5`.
        """
        return self._get('save_format', 'tf', changeable=False)

    @property
    def log_dir(self) -> str:
        """
        Log dir for saving logs. If set to `null`,
        logs will save at `save_base_dir/current_model`.
        """
        return self._get('log_dir', 'null', changeable=False)

    @property
    def load(self) -> str:
        """
        Log folder to load model. If set to `null`,
        it will start training new models according to other args.
        """
        return self._get('load', 'null', changeable=True)

    @property
    def model(self) -> str:
        """
        Model used to train.
        """
        return self._get('model', 'none', changeable=False)

    @property
    def model_name(self) -> str:
        """
        Model's name when saving.
        """
        return self._get('model_name', 'model', changeable=False)

    @property
    def restore(self) -> str:
        """
        Path to the pre-trained models before training.
        """
        return self._get('restore', 'null', changeable=True)

    @property
    def test_set(self) -> str:
        """
        Test dataset. Only works on ETH-UCY dataset.
        """
        if (fs := self.force_set) != 'null':
            return fs
        else:
            return self._get('test_set', 'zara1', changeable=False)

    def _get(self, name: str, default: Any, changeable=False):
        try:
            if (not changeable) and (self._args_load):
                value = getattr(self._args_load, name)
            elif changeable and self._force_args:
                value = getattr(self._force_args, name)
            else:
                value = getattr(self._args, name)

        except:
            value = default

        return value

    def _print(self, log_function=print):
        dic = {}
        for arg in self._arg_list:
            dic[arg] = getattr(self, arg)

        log_function(dic)
