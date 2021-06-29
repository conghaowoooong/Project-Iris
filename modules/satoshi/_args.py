"""
@Author: Conghao Wong
@Date: 2021-04-01 20:28:00
@LastEditors: Conghao Wong
@LastEditTime: 2021-06-29 19:21:06
@Description: file content
@Github: https://github.com/conghaowoooong
@Copyright 2021 Conghao Wong, All Rights Reserved.
"""

import modules.models as M


class SatoshiArgs(M.prediction.TrainArgs):
    def __init__(self):
        super().__init__()

        self.loada_C = ['null', 'Path for Satoshi Alpha model', 'la']
        self.loadb_C = ['null', 'Path for Satoshi Beta model', 'lb']
        self.loadc_C = ['null', 'Path for Satoshi Gamma model', 'lc']
        self.linear = [0, 'Controls whether use linear prediction in the last stage', 'linear']
        self.H = [3, 'number of observed trajectories used']
        self.force_pred_frames_C = [-1,
                                    'force setting of predict frames when test']
        self.check_C = [0]

    def args(self):
        _args = super().args()
        if _args.force_pred_frames != -1:
            _args.pred_frames = _args.force_pred_frames

        return _args


class SatoshiOnlineArgs(SatoshiArgs, M.prediction.OnlineArgs):
    def __init__(self):
        SatoshiArgs.__init__(self)
        M.prediction.OnlineArgs.__init__(self)
