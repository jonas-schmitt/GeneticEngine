from __future__ import annotations

from typing import get_args


from geneticengine.core.grammar import Grammar
from geneticengine.core.random.sources import Source
from geneticengine.core.representations.tree_smt import smt
from geneticengine.core.representations.tree_smt.initializations import is_metahandler
from geneticengine.metahandlers.base import MetaHandlerGenerator
from geneticengine.metahandlers.smt.parser import p_expr


def simplify_type(t: type) -> type:
    if is_metahandler(t):
        return get_args(t)[0]
    return t


class SMT(MetaHandlerGenerator):
    def __init__(self, restriction_as_str="true==true"):
        self.restriction_as_str = restriction_as_str
        self.restriction = p_expr(restriction_as_str)

    def generate(
        self,
        r: Source,
        g: Grammar,
        rec,
        new_symbol,
        depth: int,
        base_type,
        context: dict[str, str],
    ):
        # fix_types(self.restriction, context)
        c = context.copy()

        ident = c["_"]
        smt.SMTResolver.register_type(ident, base_type)

        smt.SMTResolver.add_clause(
            [lambda types: self.restriction.translate(c, types)],
            {},
        )

        if base_type == int or base_type == bool or base_type == float:
            # we need the result, add receiver
            smt.SMTResolver.add_clause(
                [],
                {ident: rec},
            )
        else:
            # just synth normally
            new_symbol(base_type, rec, depth, ident, context)

    def __repr__(self):
        return f"{self.restriction}"
