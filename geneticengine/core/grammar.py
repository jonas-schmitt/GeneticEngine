from __future__ import annotations

import inspect
import warnings
from abc import ABC
from abc import ABCMeta
from collections import defaultdict
from typing import Any
from typing import Generic
from typing import NamedTuple

from geneticengine.core.decorators import get_gengy
from geneticengine.core.utils import all_init_arguments_typed
from geneticengine.core.utils import get_arguments
from geneticengine.core.utils import get_generic_parameter
from geneticengine.core.utils import get_generic_parameters
from geneticengine.core.utils import is_abstract
from geneticengine.core.utils import is_annotated
from geneticengine.core.utils import is_generic
from geneticengine.core.utils import is_generic_list
from geneticengine.core.utils import is_terminal
from geneticengine.core.utils import strip_annotations
from geneticengine.core.utils import strip_dependencies


class InvalidGrammarException(Exception):
    """Exception to be raised when a passed node is neither abstract nor
    typed."""

    pass


class DepthRange(NamedTuple):
    depth_min: int
    depth_max: int


class ProductionSummary(NamedTuple):
    production_frequencies: dict[int, int]
    number_of_recursive_productions: int
    alternatives: dict[Any, list]
    total_productions: int
    average_productions_per_non_terminal: float
    average_non_terminals_per_production: dict


class GrammarSummary(NamedTuple):
    depth_range: DepthRange
    number_of_non_terminals: int
    production_stats: ProductionSummary


class Grammar:
    starting_symbol: type
    alternatives: dict[type, list[type]]
    distanceToTerminal: dict[Any, int]
    all_nodes: set[type]
    recursive_prods: set[type]
    terminals: set[
        type
    ]  # todo: both terminals and non_terminals can be obtained by checking if disttoterminal == or!= 0
    non_terminals: set[type]
    abstract_dist_to_t: dict[type, dict[type, int]]

    def __init__(
        self,
        starting_symbol: type,
        considered_subtypes: list[type] | None = None,
        expansion_depthing: bool = False,
    ) -> None:
        self.alternatives: dict[type, list[type]] = {}
        self.starting_symbol = starting_symbol
        self.distanceToTerminal = {int: 0, str: 0, float: 0}
        self.all_nodes = set()
        self.recursive_prods = set()
        self.terminals = set()
        self.non_terminals = set()
        self.abstract_dist_to_t = defaultdict(
            lambda: defaultdict(lambda: 1000000),
        )
        self.considered_subtypes = considered_subtypes or []
        self.expansion_depthing = expansion_depthing

        self.validate()

    def validate(self):
        for c in self.considered_subtypes:
            if is_abstract(c):
                continue
            elif all_init_arguments_typed(c):
                # Raise a warning if there are annotated elements, but no __init__ method.
                d = {x[0]: x[1] for x in inspect.getmembers(c)}
                if "__annotations__" in d and d["__annotations__"] and d["__init__"].__qualname__ == "object.__init__":
                    warnings.warn(
                        f"Warning: class {c} looks like it should be a dataclass, but isn't.",
                    )
                else:
                    continue
            else:
                raise InvalidGrammarException(
                    f"Type {c} is not abstract nor has a type-annotated constructor",
                )

    def register_alternative(self, nonterminal: type, nodetype: type):
        """Register a production A->B Call multiple times with same A to
        register many possible alternatives."""
        if not is_abstract(nonterminal):
            raise Exception(
                f"Trying to register an alternative on a non-abstract class: {nonterminal} -> {nodetype}\n"
                f"You may have meant for {nonterminal.__name__} to be abstract. If so, decorate it with @abstract.\n"
                f"(Found in geneticengine.core.decorators)",
            )
        if nonterminal not in self.alternatives:
            self.alternatives[nonterminal] = []
        self.alternatives[nonterminal].append(nodetype)

    def register_type(self, ty: type):
        if ty in self.all_nodes:
            return
        elif is_generic_list(ty):
            gty = get_generic_parameter(ty)
            self.register_type(gty)
            return
        elif is_annotated(ty):
            gty = get_generic_parameter(ty)
            self.register_type(gty)
            return
        elif is_generic(ty):
            for p in get_generic_parameters(ty):
                self.register_type(p)
            return
        self.all_nodes.add(ty)

        parent = ty.mro()[1]
        if parent not in [object, ABC, Generic, int, bool, float, str]:
            assert isinstance(parent, type)
            self.register_type(parent)
            self.register_alternative(parent, ty)

        terminal = False
        if not is_abstract(ty):
            terminal = True
            for arg, argt in get_arguments(ty):
                terminal = False
                if isinstance(argt, type) or isinstance(argt, ABCMeta):
                    self.register_type(argt)
                if is_annotated(argt):
                    gen = get_generic_parameter(argt)
                    if is_generic_list(gen):
                        self.register_type(get_generic_parameter(gen))
                    else:
                        self.register_type(gen)

        for st in self.considered_subtypes:
            if issubclass(st, ty):
                self.register_type(st)

        if terminal:
            self.terminals.add(ty)
        else:
            self.non_terminals.add(ty)

    def __repr__(self):
        def wrap(n):
            if hasattr(n, "__name__"):
                return n.__name__
            if hasattr(n, "__metadata__"):
                if is_generic_list(get_generic_parameter(n)):
                    return f"{n.__metadata__[0]} of {wrap(strip_annotations(n))}"
                else:
                    return f"{n.__metadata__[0]}"
            return n

        def format(x):
            def add_weight(prod):
                if "weight" in get_gengy(prod):
                    return f'<{get_gengy(prod)["weight"]}>'
                return ""

            args = ", ".join(
                [f"{a}: {wrap(at)}" for (a, at) in get_arguments(x)],
            )
            return f"{x.__name__}({args}){add_weight(x)}"

        prods = ";".join(
            [
                str(p.__name__) + " -> " + ("|".join([format(p) for p in self.alternatives[p]]))
                for p in self.alternatives
            ],
        )
        return f"Grammar<Starting={self.starting_symbol.__name__},Productions=[{prods}]>"

    def get_all_symbols(self) -> tuple[set[type], set[type], set[type]]:
        """All symbols in the current grammar, including terminals."""
        keys = {k for k in self.alternatives.keys()}
        sequence = {v for vv in self.alternatives.values() for v in vv}
        return (keys, sequence, sequence.union(keys).union(self.all_nodes))

    def get_distance_to_terminal(self, ty: type) -> int:
        """Returns the current distance to terminal of a given type."""
        if is_annotated(ty):
            ta = get_generic_parameter(ty)
            return self.get_distance_to_terminal(ta)
        elif is_generic_list(ty):
            ta = get_generic_parameter(ty)
            return int(self.expansion_depthing) + self.get_distance_to_terminal(ta)
        elif is_generic(ty):
            return int(self.expansion_depthing) + max(
                self.get_distance_to_terminal(t) for t in get_generic_parameters(ty)
            )
        else:
            return self.distanceToTerminal[ty]

    def get_min_tree_depth(self):
        """Returns the minimum depth a tree must have."""
        return self.distanceToTerminal[self.starting_symbol]

    def get_max_node_depth(self):
        """Returns the maximum minimum depth a node can have."""

        def dist(x):
            return self.distanceToTerminal[x]

        return max(list(map(dist, self.all_nodes)))

    def preprocess(self) -> None:
        """Computes distanceToTerminal via a fixpoint algorithm."""
        (keys, _, all_sym) = self.get_all_symbols()
        for s in all_sym:
            self.distanceToTerminal[s] = 1000000
        changed = True

        reachability: dict[type, set[type]] = defaultdict(lambda: set())

        def process_reachability(src: type, dsts: list[type]):
            src = strip_annotations(src)
            ch = False
            src_reach = reachability[src]
            for prod in dsts:
                prod = strip_annotations(prod)
                reach = reachability[prod]
                oldlen = len(reach)
                reach.add(src)
                reach.update(src_reach)
                ch |= len(reach) != oldlen
            return ch

        while changed:
            changed = False
            for sym in all_sym:
                old_val = self.distanceToTerminal[sym]
                val = old_val

                if is_abstract(sym):
                    if sym in self.alternatives:
                        prods = self.alternatives[sym]
                        for prod in prods:
                            val = min(
                                val,
                                int(self.expansion_depthing) + self.distanceToTerminal[prod],
                            )
                            old = self.abstract_dist_to_t[sym][prod]
                            if 1 < old:
                                self.abstract_dist_to_t[sym][prod] = 1
                                changed = True
                            if prod in self.abstract_dist_to_t:
                                for subprod, dist in self.abstract_dist_to_t[prod].items():
                                    currdist = self.abstract_dist_to_t[sym][subprod]
                                    candidate = dist + 1
                                    if candidate < currdist:
                                        self.abstract_dist_to_t[sym][subprod] = candidate
                                        changed = True
                        changed |= process_reachability(sym, prods)
                else:
                    if is_terminal(sym, self.non_terminals):
                        if (sym == int or sym == float or sym == str) and not self.expansion_depthing:
                            val = 0
                        else:
                            val = 1
                    else:
                        args = get_arguments(sym)
                        assert args
                        val = max(1 + self.get_distance_to_terminal(argt) for (_, argt) in args)

                        changed |= process_reachability(
                            sym,
                            [argt for (_, argt) in args],
                        )

                if val < old_val:
                    changed = True
                    self.distanceToTerminal[sym] = val

        for sym in all_sym:
            if sym in reachability[sym]:  # symbol is recursive
                self.recursive_prods.add(sym)
            else:
                pass

    def get_weights(self):
        weights = {prod: get_gengy(prod).get("weight", 1.0) for prod in self.all_nodes}
        return weights

    def update_weights(self, learning_rate, extra_weights):
        weights = self.get_weights()
        for rule in self.alternatives:
            prods = self.alternatives[rule]
            total_weights = 0
            for prod in prods:
                weights[prod] += learning_rate * extra_weights[prod]
                total_weights += weights[prod]
            for prod in prods:
                weights[prod] = weights[prod] / total_weights

        for weight in weights:
            assert weights[weight] >= 0 and weights[weight] <= 1

        starting_symbol = self.starting_symbol
        starting_symbol.__dict__["__gengy__"]["weight"] = weights[starting_symbol]
        nodes = list()
        for node in self.considered_subtypes:
            node.__dict__["__gengy__"]["weight"] = weights[node]
            nodes.append(node)
        self.__init__(starting_symbol, nodes, self.expansion_depthing)
        self.register_type(starting_symbol)
        self.preprocess()
        return self

    def get_branching_average_proxy(self, r, get_nodes_depth_specific, n_individuals:int = 100, max_depth:int = 17):
        """
        Get a proxy for the average branching factor of a grammar. This proxy is a dictionary with the number of non-terminals in each depth of the grammar, obtained by generating <n_individuals> random individuals with depth <max_depth> and analyzing those.
        """
        max_depth = max(max_depth, self.get_min_tree_depth())
        branching_factors = dict()
        for i in range(max_depth + 1):
            branching_factors[str(i)] = 0
        for idx in range(n_individuals):
            n_d_specs = get_nodes_depth_specific(r, self, max_depth)
            for key in n_d_specs.keys():
                branching_factors[key] = (branching_factors[key] * idx + n_d_specs[key]) / (idx + 1)
        
        return branching_factors

    def get_grammar_properties_summary(self) -> GrammarSummary:
        """Returns a summary of grammar properties:

        - A depth range (minimum depth and maximum depth of the grammar)
        - The number of Non-Terminal symbols in the grammar
        - A summary of production statistics:
            - Frequency of Productions in the Right Hand side
            - The number of recursive productions
            - Per non-terminal, all the alternative productions
            - The total number of productions
            - The average number of productions per non-terminal
            - The average non-terminals per production for each non-terminal
        """
        depth_min = self.get_min_tree_depth()
        depth_max = self.get_max_node_depth()
        n_non_terminals = len(self.alternatives)
        n_prods_per_nt = list(map(lambda x: len(x), self.alternatives.values()))
        n_prods_occurrences: dict[int, int] = dict()
        for i in n_prods_per_nt:
            n_prods_occurrences[i] = n_prods_occurrences.get(i, 0) + 1
        n_prods_occurrences = {k: n_prods_occurrences[k] for k in sorted(n_prods_occurrences.keys())}
        recursive_prods = [r_prod for r_prod in self.recursive_prods if r_prod not in self.alternatives.keys()]
        n_recursive_prods = len(recursive_prods)
        total_productions = sum(len(x) for x in self.alternatives.values())
        average_productions = total_productions / len(self.alternatives.keys()) if self.alternatives else 0

        stripped_non_terminals = [strip_dependencies(str(nt)) for nt in self.non_terminals]
        avg_non_terminals_per_production = dict()
        for key in self.alternatives.keys():
            avg_nts_pp = 0
            alternatives = self.alternatives[key]
            for alternative in alternatives:
                nts = 0
                for value in alternative.__annotations__.values():
                    if value in stripped_non_terminals:
                        nts += 1
                avg_nts_pp += nts * self.get_weights()[alternative]
            avg_non_terminals_per_production[key] = avg_nts_pp

        return GrammarSummary(
            DepthRange(depth_min, depth_max),
            n_non_terminals,
            ProductionSummary(
                n_prods_occurrences,
                n_recursive_prods,
                self.alternatives,
                total_productions,
                average_productions,
                avg_non_terminals_per_production,
            ),
        )


def extract_grammar(
    considered_subtypes: list[type],
    starting_symbol: type,
    expansion_depthing: bool = False,
):
    """The extract_grammar takes in all the productions of the grammar (nodes)
    and a starting symbol (starting_symbol). It goes through all the nodes and
    constructs a complete grammar that can then be used for search algorithms
    such as Genetic Programming and Hill Climbing.

    Args:
        nodes (list): A list of objects representing tree nodes. Make sure that any node can be produced be the starting
            symbol.
        starting_symbol (object): The starting symbol of each tree. Makes sure every generated tree by the returned
            grammar starts with this symbol. Make sure that the starting symbol can produce any object of nodes.

    Returns:
        The grammar
    """
    g = Grammar(starting_symbol, considered_subtypes, expansion_depthing)
    g.register_type(starting_symbol)
    g.preprocess()
    if any(["weight" in get_gengy(p) for p in considered_subtypes]):
        g.update_weights(1, g.get_weights())
    return g
