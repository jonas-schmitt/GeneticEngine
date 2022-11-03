from __future__ import annotations

from typing import Annotated

from utils import get_data
from utils import import_embedded

from geneticengine.algorithms.gp.gp import GP
from geneticengine.core.grammar import extract_grammar
from geneticengine.core.problems import SingleObjectiveProblem
from geneticengine.core.representations.grammatical_evolution.ge import (
    ge_representation,
)
from geneticengine.core.representations.grammatical_evolution.structured_ge import (
    sge_representation,
)
from geneticengine.core.representations.tree.treebased import treebased_representation
from geneticengine.grammars.coding.classes import Number
from geneticengine.grammars.coding.classes import Statement
from geneticengine.grammars.coding.classes import XAssign
from geneticengine.grammars.coding.conditions import Equals
from geneticengine.grammars.coding.conditions import GreaterOrEqualThan
from geneticengine.grammars.coding.conditions import GreaterThan
from geneticengine.grammars.coding.conditions import Is
from geneticengine.grammars.coding.conditions import IsNot
from geneticengine.grammars.coding.conditions import LessOrEqualThan
from geneticengine.grammars.coding.conditions import LessThan
from geneticengine.grammars.coding.conditions import NotEquals
from geneticengine.grammars.coding.control_flow import IfThen
from geneticengine.grammars.coding.control_flow import IfThenElse
from geneticengine.grammars.coding.control_flow import While
from geneticengine.grammars.coding.logical_ops import And
from geneticengine.grammars.coding.logical_ops import Or
from geneticengine.grammars.coding.numbers import Abs
from geneticengine.grammars.coding.numbers import Literal
from geneticengine.grammars.coding.numbers import Max
from geneticengine.grammars.coding.numbers import Min
from geneticengine.grammars.coding.numbers import Mul
from geneticengine.grammars.coding.numbers import Plus
from geneticengine.grammars.coding.numbers import SafeDiv
from geneticengine.grammars.coding.numbers import Var
from geneticengine.metahandlers.vars import VarRange

# ===================================
# This is a simple example on how to use GeneticEngine to solve a GP problem.
# We define the tree structure of the representation and then we define the fitness function for our problem
# This Smallest example is a combinatorial optimization problem, given 4 integers, get the smallest of them.
# We used the Smallest dataset stored in examples/progsys/data folder
# Problem taken from the following paper: https://dl.acm.org/doi/abs/10.1145/2739480.2754769
# ===================================

FILE_NAME = "Smallest"
DATA_FILE_TRAIN = f"./examples/progsys/data/{FILE_NAME}/Train.txt"
DATA_FILE_TEST = f"./examples/progsys/data/{FILE_NAME}/Test.txt"

inval, outval = get_data(DATA_FILE_TRAIN, DATA_FILE_TEST)
imported = import_embedded(FILE_NAME)

vars = ["in0", "in1", "in2", "in3"]
variables = {}
for i, n in enumerate(vars):
    variables[n] = i

XAssign.__init__.__annotations__["value"] = Number
Var.__init__.__annotations__["name"] = Annotated[str, VarRange(vars)]
Var.feature_indices = variables  # type: ignore
g = extract_grammar(
    [
        Plus,
        Literal,
        Mul,
        SafeDiv,
        Max,
        Min,
        Abs,
        And,
        Or,
        Var,
        Equals,
        NotEquals,
        GreaterOrEqualThan,
        GreaterThan,
        LessOrEqualThan,
        LessThan,
        Is,
        IsNot,
        XAssign,
        IfThen,
        IfThenElse,  # , While
    ],
    Statement,
)
print(f"Grammar: {repr(g)}.")


def fitness_function(n: Statement):
    fitness, error, cases = imported.fitness(inval, outval, n.evaluate_lines())
    return fitness


def preprocess():
    return extract_grammar(
        [
            Plus,
            Literal,
            Mul,
            SafeDiv,
            Max,
            Min,
            Abs,
            And,
            Or,
            Var,
            Equals,
            NotEquals,
            GreaterOrEqualThan,
            GreaterThan,
            LessOrEqualThan,
            LessThan,
            Is,
            IsNot,
            XAssign,
            IfThen,
            IfThenElse,  # , While
        ],
        Statement,
    )


def evolve(g, seed, mode, representation=""):
    if representation == "ge":
        representation = ge_representation
    elif representation == "sge":
        representation = sge_representation
    else:
        representation = treebased_representation
    alg = GP(
        g,
        representation=representation,
        problem=SingleObjectiveProblem(
            minimize=True,
            fitness_function=fitness_function,
            target_fitness=None,
        ),
        number_of_generations=5,
        seed=seed,
        max_depth=10,
        population_size=50,
        probability_crossover=0.9,
        timer_stop_criteria=mode,
    )
    (b, bf, bp) = alg.evolve(verbose=1)
    return b, bf


if __name__ == "__main__":
    g = preprocess()
    bf, b = evolve(g, 0, False)
    print(b)
    print(f"With fitness: {bf}")
