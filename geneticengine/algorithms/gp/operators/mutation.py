from __future__ import annotations

from typing import Any

from geneticengine.algorithms.gp.individual import Individual
from geneticengine.algorithms.gp.structure import GeneticStep
from geneticengine.core.problems import Problem
from geneticengine.core.random.sources import Source
from geneticengine.core.representations.api import MutationOperator
from geneticengine.core.representations.api import Representation


class GenericMutationStep(GeneticStep):
    """Applies a mutation to individuals with a given probability."""

    def __init__(
        self,
        probability: float,
        operator: MutationOperator | None = None,
    ):
        self.probability = probability
        self.operator = operator

    def iterate(
        self,
        problem: Problem,
        representation: Representation,
        random_source: Source,
        population: list[Individual],
        target_size: int,
    ) -> list[Individual]:
        if not self.operator:
            self.operator = representation.get_mutation()
        return [
            self.wrap(
                representation,
                self.operator.mutate(
                    ind.genotype,
                    problem,
                    representation,
                    random_source,
                    index,
                    0,
                ),  # TODO: generation in API
            )
            for index, ind in enumerate(population[:target_size])
        ]

    def wrap(self, representation: Representation, genotype: Any) -> Individual:
        return Individual(
            genotype=genotype,
            genotype_to_phenotype=representation.genotype_to_phenotype,
        )


# TODO: Refactor into MutationOperator
class HillClimbingMutationIteration(GeneticStep):
    def __init__(
        self,
        probability: float,
        specific_type: type | None = None,
        depth_aware_mut: bool = False,
        n_candidates: int = 5,
    ):
        self.probability = probability
        self.specific_type = specific_type
        self.depth_aware_mut = depth_aware_mut
        self.n_candidates = n_candidates

    def iterate(
        self,
        problem: Problem,
        representation: Representation,
        random_source: Source,
        population: list[Individual],
        target_size: int,
    ) -> list[Individual]:
        assert len(population) == target_size

        return [self.mutate(ind, representation, random_source, problem) for ind in population]

    def mutate(
        self,
        individual: Individual,
        representation: Representation,
        random_source: Source,
        problem: Problem,
    ) -> Individual:
        def creation_new_individual():
            genotype = representation.mutate_individual(
                random_source,
                individual.genotype,
                representation.max_depth,
                representation.grammar.starting_symbol,  # TODO: this does not seem okay
                specific_type=self.specific_type,
                depth_aware_mut=self.depth_aware_mut,
            )

            return Individual(
                genotype=genotype,
                genotype_to_phenotype=representation.genotype_to_phenotype,
            )

        new_individuals = [creation_new_individual() for _ in range(self.n_candidates)]

        best_individual = min(
            (new_individuals + [individual]),
            key=lambda ind: problem.overall_fitness(ind.get_phenotype()),
        )
        return best_individual
