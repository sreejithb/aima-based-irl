"""
Author: Eren Sezener (erensezener@gmail.com)
Date: April 6, 2014

Description: This implementation is based on "Improving the Efficiency of Bayesian Inverse Reinforcement Learning" by
Michini and How.

Status: Work In Progress

Dependencies: This module is compatible with Python 2.7.5.

Known bugs: -


"""

from mdp import *
from utils import *
from copy import deepcopy
from math import exp


class BIRL():
    def __init__(self, expert_trace, grid_size, terminals, error_func, birl_iteration=2000, step_size=2, r_min=-10, r_max=10):
        self.n_rows, self.n_columns = grid_size
        self.r_min, self.r_max = r_min, r_max
        self.step_size = step_size
        self.expert_trace = expert_trace
        self.birl_iteration = birl_iteration
        self.terminals = terminals
        self.error_func = error_func

    def run_birl(self):
        errors_per_iteration = []
        #This is the core BIRL algorithm
        mdp = self.create_rewards(self.create_rewards)
        pi, u = policy_iteration(mdp)
        q = get_q_values(mdp, u)
        posterior = calculate_posterior(mdp, q, self.expert_trace)
        best_posterior, best_mdp, best_pi = NEGATIVE_SMALL_NUMBER, None, None

        for _ in range(self.birl_iteration):
            new_mdp = deepcopy(mdp)
            new_mdp.modify_rewards_randomly(self.step_size)
            new_u = policy_evaluation(pi, u, new_mdp, 1)

            if pi != best_policy(new_mdp, new_u):
                new_pi, new_u = policy_iteration(new_mdp)
                new_q = get_q_values(new_mdp, new_u)
                new_posterior = calculate_posterior(new_mdp, new_q, self.expert_trace)

                if probability(min(1, exp(new_posterior - posterior))):
                    pi, u, mdp, posterior = new_pi, new_u, deepcopy(new_mdp), new_posterior

            else:
                new_q = get_q_values(new_mdp, new_u)
                new_posterior = calculate_posterior(new_mdp, new_q, self.expert_trace)

                if probability(min(1, exp(new_posterior - posterior))):
                    mdp, posterior = deepcopy(new_mdp), new_posterior

            if posterior > best_posterior:  # Pick the mdp with the best posterior
                best_posterior, best_mdp, best_pi = posterior, deepcopy(mdp), pi

            errors_per_iteration.append(self.error_func(mdp))
        return best_pi, best_mdp, errors_per_iteration


#------------- Reward functions ------------
    #TODO move priors out of the mdp
    def create_rewards(self, reward_function_to_call=None):
        # If no reward function is specified, sets all rewards as 0
        if reward_function_to_call is None:
            return self.create_zero_rewards()
        return reward_function_to_call()

    def create_zero_rewards(self):
        return GridMDP([[0 for _ in range(self.n_columns)] for _ in range(self.n_rows)]
                       , terminals=deepcopy(self.terminals))

    def create_random_rewards(self):
        return GridMDP(
            [[random.uniform(self.r_min, self.r_max) for _ in range(self.n_columns)] for _ in range(self.n_rows)]
            , terminals=deepcopy(self.terminals))

    def create_gaussian_rewards(self):
        mean, stdev = 0, self.r_max / 3
        return GridMDP(
            [[self.bound_rewards(random.gauss(mean, stdev)) for _ in range(self.n_columns)] for _ in range(self.n_rows)]
            , terminals=deepcopy(self.terminals))

    def bound_rewards(self, reward):
        if reward > self.r_max:
            reward = self.r_max
        elif reward < self.r_min:
            reward = self.r_min
        return reward

def calculate_posterior(mdp, q, expert_pi, gamma = 0.95):
    z = []
    e = 0
    for s in mdp.states:
        for a in mdp.actions(s):
            z.append(gamma * q[s, a])
        e += gamma * q[s, expert_pi[s]] - logsumexp(z)
        del z[:] #Removes contents of Z
    return e


def get_q_values(mdp, U):
    Q = {}
    for s in mdp.states:
        for a in mdp.actions(s):
            for (p, sp) in mdp.T(s, a):
                Q[s, a] = mdp.reward[s] + mdp.gamma * p * U[sp]
    return Q


def calculate_beta_prior(R, Rmax=10):
    R = abs(R)
    Rmax += 0.000001
    return 1 / (((R / Rmax) ** 0.5) * ((1 - R / Rmax) ** 0.5))


def uniform_prior(_): return 1