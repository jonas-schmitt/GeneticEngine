from abc import ABC, abstractmethod
from typing import Any


from geneticengine.algorithms.gp.individual import Individual
from geneticengine.core.problems import Problem


class Evaluator(ABC):
    def __init__(self):
        self.count = 0

    @abstractmethod
    def eval(self, p: Problem, indivs: list[Individual[Any, Any]]):
        ...

    def register_evaluation(self):
        self.count += 1

    def get_count(self):
        return self.count

    def eval_single(self, p: Problem, individual: Individual):
        if not individual.has_fitness(p):
            phenotype = individual.get_phenotype()
            individual.set_fitness(p, p.evaluate(phenotype=phenotype))
            self.register_evaluation()


class SequentialEvaluator(Evaluator):
    """Default evaluator for individuals, executes sequentially."""

    def eval(self, p: Problem, indivs: list[Individual[Any, Any]]):
        for individual in indivs:
            self.eval_single(p, individual)