from __future__ import annotations

from operator import concat
from typing import Union

from geneticengine.algorithms.gp.individual import Individual
from geneticengine.algorithms.gp.structure import GeneticStep
from geneticengine.core.problems import Problem
from geneticengine.core.random.sources import Source
from geneticengine.core.representations.api import Representation


class SequenceStep(GeneticStep):
    """Applies multiple steps in order."""

    def __init__(self, *steps: GeneticStep):
        self.steps = steps

    def iterate(
        self,
        problem: Problem,
        representation: Representation,
        random_source: Source,
        population: list[Individual],
        target_size: int,
    ) -> list[Individual]:
        for step in self.steps:
            population = step.iterate(
                problem,
                representation,
                random_source,
                population,
                target_size,
            )
            print(step)
            assert isinstance(population, list)
            assert len(population) == target_size
        return population


class ParallelStep(GeneticStep):
    """Splits the population according to weights, and applies a different step
    to each part."""

    def __init__(
        self,
        steps: list[GeneticStep],
        weights: list[float] | None = None,
    ):
        self.steps = steps
        self.weights = weights or [1 for _ in steps]
        assert len(self.steps) == len(self.weights)

    def iterate(
        self,
        problem: Problem,
        representation: Representation,
        random_source: Source,
        population: list[Individual],
        target_size: int,
    ) -> list[Individual]:
        total = sum(self.weights)
        indices = self.cumsum(
            [round(w * len(population) / total, 0) for w in self.weights],
        )
        ranges = zip(indices, indices[1:])

        return self.concat(
            [
                step.iterate(
                    problem,
                    representation,
                    random_source,
                    population[start:end],
                    end - start,
                )
                for ((start, end), step) in zip(ranges, self.steps)
            ],
        )

    def concat(self, ls):
        rl = []
        for l in ls:
            rl.extend(l)
        return rl

    def cumsum(self, l):
        v = 0
        nl = []
        for i in l:
            v = v + i
            nl.append(v)
        return nl
