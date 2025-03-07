from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Annotated

import pytest

from geneticengine.algorithms.gp.gp import default_generic_programming_step
from geneticengine.algorithms.gp.individual import Individual
from geneticengine.algorithms.gp.operators.combinators import SequenceStep
from geneticengine.algorithms.gp.operators.crossover import GenericCrossoverStep
from geneticengine.algorithms.gp.operators.mutation import GenericMutationStep
from geneticengine.algorithms.gp.operators.selection import TournamentSelection
from geneticengine.algorithms.gp.structure import GeneticStep
from geneticengine.core.evaluators import Evaluator, SequentialEvaluator
from geneticengine.core.grammar import extract_grammar
from geneticengine.core.problems import Fitness, Problem, SingleObjectiveProblem
from geneticengine.core.random.sources import RandomSource, Source
from geneticengine.core.representations.api import Representation
from geneticengine.core.representations.tree.treebased import TreeBasedRepresentation
from geneticengine.metahandlers.lists import ListSizeBetween


class Alt(ABC):
    pass


@dataclass
class Sub(Alt):
    a: int
    b: int


@dataclass
class Base:
    li: Annotated[list[Alt], ListSizeBetween(1, 2)]


class CacheFitness(GeneticStep):
    def iterate(
        self,
        problem: Problem,
        evaluator: Evaluator,
        representation: Representation,
        random_source: Source,
        population: list[Individual],
        target_size: int,
        generation: int,
    ) -> list[Individual]:
        for ind in population:
            ind.set_fitness(problem, Fitness(-1.0, []))
        return population


class TestPreCache:
    @pytest.mark.parametrize(
        "test_step",
        [
            GenericMutationStep(1.0),
            GenericCrossoverStep(1.0),
            TournamentSelection(3),
            default_generic_programming_step(),
        ],
    )
    def test_immutability(self, test_step):
        g = extract_grammar([Sub], Base)
        rep = TreeBasedRepresentation(g, max_depth=10)
        r = RandomSource(3)

        def fitness_function(x):
            assert False

        problem = SingleObjectiveProblem(fitness_function=fitness_function)
        population_size = 1000

        initial_population = [
            Individual(genotype=rep.create_individual(r, 10), genotype_to_phenotype=rep.genotype_to_phenotype)
            for _ in range(population_size)
        ]

        def encode_population(pop: list[Individual]) -> list[str]:
            return [str(ind.genotype) for ind in pop]

        cpy = encode_population(initial_population)

        step = SequenceStep(CacheFitness(), default_generic_programming_step())

        for i in range(10):
            _ = step.iterate(
                problem=problem,
                evaluator=SequentialEvaluator(),
                representation=rep,
                random_source=r,
                population=initial_population,
                target_size=population_size,
                generation=i,
            )
        for a, b in zip(encode_population(initial_population), cpy):
            assert a == b
