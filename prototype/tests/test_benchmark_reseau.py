"""Le benchmark lui-même est testé : étiquette, équité (mêmes candidats, même budget), vérité latente cachée."""
from eval import benchmark_reseau as br


def test_benchmark_equitable_et_etiquete():
    d = br.generer(1)
    assert d["etiquette"] == "SYNTHETIC_BENCHMARK"
    cand = set(br.candidats(d))
    assert all(d["consent"][a] and d["consent"][b] and not d["g"].has_edge(a, b) for a, b in cand)
    for nom, f in br.METHODES.items():
        paires = f(d, sorted(cand), 1)
        assert {tuple(sorted(p)) for p in paires} <= {tuple(sorted(p)) for p in cand}, nom      # mêmes candidats
        charge = {}
        for a, b in paires:
            charge[a], charge[b] = charge.get(a, 0) + 1, charge.get(b, 0) + 1
        assert max(charge.values()) <= br.BUDGET_PAR_MEMBRE, nom                                # même budget
        assert len({frozenset(p) for p in paires}) == len(paires), nom


def test_verite_latente_differe_du_declare():
    d = br.generer(2)
    perimees = sum(len(d["offres"][m] - d["vraies"][m]) for m in d["com"])
    assert perimees > 0                          # sinon le benchmark mesurerait ce que les méthodes optimisent
