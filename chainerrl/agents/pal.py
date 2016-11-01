from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import super
from future import standard_library
standard_library.install_aliases()

import numpy as np

from chainer import Variable
from chainer import functions as F

from chainerrl.agents import dqn


class PAL(dqn.DQN):
    """Persistent Advantage Learning.

    See: http://arxiv.org/abs/1512.04860.
    """

    def __init__(self, *args, **kwargs):
        """
        Args:
          alpha (float): Weight of (persistent) advantages. Convergence
            is guaranteed only for alpha in [0, 1).

        For other arguments, see DQN.
        """
        super().__init__(*args, **kwargs)
        self.alpha = kwargs.get('alpha', 0.9)

    def _compute_y_and_t(self, experiences, gamma):

        batch_size = len(experiences)

        batch_state = self._batch_states(
            [elem['state'] for elem in experiences])

        qout = self.q_function(batch_state, test=False)

        batch_actions = Variable(
            self.xp.asarray([elem['action'] for elem in experiences]))
        batch_q = qout.evaluate_actions(batch_actions)

        # Compute target values

        target_qout = self.target_q_function(batch_state, test=True)

        batch_next_state = self._batch_states(
            [elem['next_state'] for elem in experiences])

        target_next_qout = self.target_q_function(batch_next_state, test=True)
        next_q_max = target_next_qout.max
        next_q_max.creator = None

        batch_rewards = self.xp.asarray(
            [elem['reward'] for elem in experiences], dtype=np.float32)

        batch_terminal = self.xp.asarray(
            [elem['is_state_terminal'] for elem in experiences],
            dtype=np.float32)

        # T Q: Bellman operator
        t_q = batch_rewards + self.gamma * (1.0 - batch_terminal) * next_q_max

        # T_PAL Q: persistent advantage learning operator
        cur_advantage = target_qout.compute_advantage(batch_actions)
        next_advantage = target_next_qout.compute_advantage(batch_actions)
        tpal_q = t_q + self.alpha * F.maximum(cur_advantage, next_advantage)

        batch_q = F.reshape(batch_q, (batch_size, 1))
        tpal_q = F.reshape(tpal_q, (batch_size, 1))
        tpal_q.creator = None

        return batch_q, tpal_q