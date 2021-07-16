"""
@Author: Conghao Wong
@Date: 2021-07-09 09:50:49
@LastEditors: Conghao Wong
@LastEditTime: 2021-07-15 16:25:40
@Description: file content
@Github: https://github.com/conghaowoooong
@Copyright 2021 Conghao Wong, All Rights Reserved.
"""

from argparse import Namespace
from typing import List, Tuple

import tensorflow as tf
from tqdm.std import tqdm

from ._args import VArgs
from ._VirisAlpha import VIrisAlpha, VIrisAlphaModel
from ._VirisBeta import VIrisBeta, VIrisBetaModel
from ._utils import Utils as U


class _VIrisAlphaModelPlus(VIrisAlphaModel):
    def __init__(self, Args: VArgs,
                 pred_number: int,
                 linear_prediction=False,
                 training_structure: VIrisAlpha = None,
                 *args, **kwargs):

        super().__init__(Args, pred_number,
                         training_structure,
                         *args, **kwargs)

        self.linear = linear_prediction

    def post_process(self, outputs: Tuple[tf.Tensor],
                     training=None,
                     **kwargs) -> Tuple[tf.Tensor]:

        # shape = ((batch, Kc, n, 2))
        outputs = super().post_process(outputs, training, **kwargs)

        if training:
            return outputs

        batch, Kc = outputs[0].shape[:2]
        n = self.n_pred
        pos = self.training_structure.p_index
        pred = self.args.pred_frames
        K = self.args.K

        # shape = (batch, Kc, n, 2)
        proposals = outputs[0]
        current_inputs = kwargs['model_inputs']

        if self.linear:
            # Piecewise linear interpolation
            pos = tf.cast(pos, tf.float32)
            pos = tf.concat([[-1], pos], axis=0)
            obs = current_inputs[0][:, tf.newaxis, -1:, :]
            proposals = tf.concat([tf.repeat(obs, Kc, 1), proposals], axis=-2)

            return (U.LinearInterpolation(x=pos, y=proposals),)

        else:
            # prepare new inputs into beta model
            # new batch_size (total) is batch*Kc
            batch_size = self.args.max_batch_size // Kc
            batch_index = BatchIndex(batch_size, batch)

            proposals = tf.reshape(proposals, [batch*Kc, n, 2])

            beta_results = []
            for index in tqdm(batch_index.index):
                [start, end, length] = index
                beta_inputs = [tf.repeat(inp[start:end], Kc, axis=0)
                               for inp in current_inputs]
                beta_inputs.append(proposals[start*Kc: end*Kc])

                # beta outputs shape = (batch*Kc, pred, 2)
                beta_results.append(self.training_structure.beta(
                    beta_inputs,
                    return_numpy=False)[0])

            beta_results = tf.concat(beta_results, axis=0)
            beta_results = tf.reshape(beta_results, [batch, Kc, pred, 2])
            return (beta_results,)


class VIris(VIrisAlpha):
    """
    Structure for Vertical prediction
    ---------------------------------

    """

    def __init__(self, Args: List[str], *args, **kwargs):
        super().__init__(Args, *args, **kwargs)

        self.args = VArgs(Args)

        # set inputs and groundtruths
        self.set_model_inputs('trajs', 'maps', 'map_paras')
        self.set_model_groundtruths('gt')

        # set metrics
        self.set_metrics('ade', 'fde')
        self.set_metrics_weights(1.0, 0.0)

        # assign alpha model and beta model containers
        self.alpha = self
        self.beta = VIrisBeta(Args)
        self.linear_predict = False

        # load weights
        if 'null' in [self.args.loada, self.args.loadb]:
            raise ('`IrisAlpha` or `IrisBeta` not found!' +
                   ' Please specific their paths via `--loada` or `--loadb`.')

        self.alpha.args = VArgs(
            args=self.alpha.load_args(Args, self.args.loada),
            default_args=self.args._args
        )

        if self.args.loadb.startswith('l'):
            self.linear_predict = True
        
        else:
            self.beta.args = VArgs(self.beta.load_args(Args, self.args.loadb))
            self.beta.model = self.beta.load_from_checkpoint(
                self.args.loadb,
                asSecondStage=True,
                p_index=self.alpha.args.p_index)

        self.alpha.model = self.alpha.load_from_checkpoint(
            self.args.loada,
            linear_prediction=self.linear_predict
        )

    def run_train_or_test(self):
        self.run_test()

    def create_model(self, *args, **kwargs):
        return super().create_model(model_type=_VIrisAlphaModelPlus,
                                    *args, **kwargs)

    def print_test_result_info(self, loss_dict, **kwargs):
        dataset = kwargs['dataset_name']
        self.log_parameters(title='test results', **
                            dict({'dataset': dataset}, **loss_dict))
        self.logger.info('Results from {}, {}, {}, {}, {}'.format(
            self.args.loada,
            self.args.loadb,
            self.args.p_index,
            dataset,
            loss_dict))


class BatchIndex():
    def __init__(self, batch_size, length):
        super().__init__()

        self.bs = batch_size
        self.l = length

        self.start = 0
        self.end = 0
        
        self.index = []
        while (i := self.get_new()) is not None:
            self.index.append(i)

    def init(self):
        self.start = 0
        self.end = 0

    def get_new(self):
        """
        Get batch index

        :return index: (start, end, length)
        """
        if self.start >= self.l:
            return None

        start = self.start
        self.end = self.start + self.bs
        if self.end > self.l:
            self.end = self.l

        self.start += self.bs

        return [start, self.end, self.end - self.start]
