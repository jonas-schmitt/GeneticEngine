from typing import Annotated, Any, Callable

import numpy as np
import pandas as pd
from math import isinf

from geneticengine.algorithms.gp.gp import GP
from geneticengine.grammars.sgp import Plus, Literal, Number, Mul, SafeDiv, Var
from geneticengine.grammars.math import SafeLog, SafeSqrt, Sin, Tanh, Exp
from geneticengine.core.grammar import extract_grammar
from geneticengine.core.representations.treebased import treebased_representation
from geneticengine.metahandlers.vars import VarRange
from geneticengine.metrics.metrics import rmse

DATASET_NAME = "Vladislavleva4"
DATA_FILE_TRAIN = "GeneticEngine/examples/data/{}/Train.txt".format(DATASET_NAME)
DATA_FILE_TEST = "GeneticEngine/examples/data/{}/Test.txt".format(DATASET_NAME)

bunch = pd.read_csv(DATA_FILE_TRAIN, delimiter='\t')
target = bunch.response
data = bunch.drop(["response"], axis=1)

feature_names = list(data.columns.values)
feature_indices = {}
for i, n in enumerate(feature_names):
    feature_indices[n] = i

# Prepare Grammar
Var.__annotations__["name"] = Annotated[str, VarRange(feature_names)]
Var.feature_indices = feature_indices


def preprocess():
    return extract_grammar(
        [Plus, Mul, SafeDiv, Literal, Var, SafeSqrt, Exp, Sin, Tanh, SafeLog],
        Number)


def fitness_function(n: Number):
    X = data.values
    y = target.values

    f = n.evaluate_lines()
    y_pred = np.apply_along_axis(f, 1, X)
    fitness = rmse(y_pred, y)
    if isinf(fitness):
        fitness = 100000000
    return fitness


def evolve(g, seed, mode):
    alg = GP(
        g,
        treebased_representation,
        fitness_function,
        minimize=True,
        selection_method=("tournament", 2),
        max_depth=17,
        population_size=500,
        # max_init_depth=10,
        # mutation uses src.operators.mutation.int_flip_per_ind. As mutation prob is None, the probability becomes 1/genome_length per codon (what is this?). How do we translate that to our method?
        number_of_generations=50,
        probability_crossover=0.75,
        n_elites=5,
        seed=seed,
        timer_stop_criteria=mode,
    )
    (b, bf, bp) = alg.evolve(verbose=0)
    return b, bf


if __name__ == '__main__':
    g = preprocess()
    print("Grammar: {}.".format(repr(g)))
    b, bf = evolve(g, 0, False)
    print(b, bf)
