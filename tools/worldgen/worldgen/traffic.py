"""Traffic on every road, river and sea lane (docs/design/living-world.md §7.3; cities/world.md
§5.3, §6): who travels each route, in which months and hours, where they stop for the night.

Traffic is lane tokens in the region files (`lanes_tokens`): far traffic stays abstract (a
position that is a function of time), and a token becomes actors only near the camera. This
module owns the table of what moves on each route, files each entry in the region it belongs to
(with the groups it names), and finishes every token of every region file the same way:

  `id`       stable name (`<region>.<n>`), the seed of its spacing
  `hours`    when its instances are under way ([from, to], game hours); outside them they wait
  `rest`     where a waiting instance stands: the route's relay stations, inns, towns and
             harbours in order along its path (`layer:node`), or a lane's ports (port ids)
  `offsets`  each instance's share of the period (irregular, so a road never carries a
             clockwork stream)
  `when.months`, `by_month` (a climate row name or twelve factors): the months it runs and the
             share of its instances under way each month

Historical basis per entry is in its `note`. Routes are found on the joined graph of all layers
(portals of one id meet), exactly the path the engine walks.
"""

from __future__ import annotations

import heapq
import re

from .coords import to_plan
from .graph import Graph
from .raster import path_tiles
from .rng import hash64

ALL_DAY = ["00:00", "24:00"]
DAY = ["05:00", "19:30"]            # walkers, carts and caravans: first light to dusk
DROVE = ["05:00", "18:00"]
SHORT_SEA = ["05:00", "20:00"]      # coasters and triremes put in for the night
FISHING = ["03:30", "11:00"]        # out before dawn, back with the catch by late morning
LAMP_FISHING = ["20:30", "03:30"]   # fishing by torchlight on calm summer nights
COURT = ["06:00", "17:00"]

# Groups that travel together (leader first); filed in the region of the token naming them.
GROUPS = {
    "caravan": {"formation": "line", "spacing": 1.0, "leader": {"actor": "parsa.caravan_driver"},
                "members": [{"actor": "parsa.dromedary", "count": 4},
                            {"actor": "world.donkey", "variant": 1, "count": 2}]},
    "mule_train": {"formation": "line", "spacing": 0.8, "leader": {"actor": "world.muleteer"},
                   "members": [{"actor": "world.mule", "variant": 1, "count": 3}]},
    "pack_donkeys": {"formation": "line", "spacing": 0.8, "leader": {"actor": "world.muleteer"},
                     "members": [{"actor": "world.donkey", "variant": 1, "count": 3}]},
    "farm_to_market_g": {"formation": "line", "spacing": 0.9, "leader": {"actor": "athens.farmer"},
                         "members": [{"actor": "athens.donkey", "count": 1}]},
    "farm_to_market_r": {"formation": "line", "spacing": 0.9, "leader": {"actor": "rome.farmer"},
                         "members": [{"actor": "rome.donkey", "count": 1}]},
    "travellers_r": {"formation": "pairs", "spacing": 0.9, "leader": {"actor": "world.traveller"},
                     "members": [{"actor": "rome.freedman", "count": 1}]},
    "pilgrims_g": {"formation": "line", "spacing": 1.0, "leader": {"actor": "athens.citizen"},
                   "members": [{"actor": "athens.woman", "count": 1},
                               {"actor": "athens.citizen", "count": 1},
                               {"actor": "athens.donkey", "count": 1}]},
    "athletes_g": {"formation": "line", "spacing": 1.0, "leader": {"actor": "athens.athlete"},
                   "members": [{"actor": "athens.athlete", "count": 1},
                               {"actor": "athens.citizen", "count": 2}]},
    "court": {"formation": "line", "spacing": 1.2, "leader": {"actor": "parsa.cavalryman"},
              "members": [{"actor": "parsa.guard_spear", "count": 4},
                          {"actor": "parsa.chariot", "count": 1},
                          {"actor": "parsa.guard_mede", "count": 2},
                          {"actor": "parsa.p_cart", "count": 1}]},
    "donkeys_home": {"formation": "line", "spacing": 0.8, "leader": {"actor": "world.muleteer"},
                     "members": [{"actor": "world.donkey", "count": 4}]},
    "thracian_riders": {"formation": "pairs", "spacing": 1.0, "leader": {"actor": "athens.thracian"},
                        "members": [{"actor": "athens.horse", "count": 2}]},
}
for _people, _gift in (("lydians", 2), ("cappadocians", 2), ("babylonians", 2), ("elamites", 2),
                       ("syrians", 2), ("armenians", 2), ("arabs", 2)):
    GROUPS[f"del_{_people}"] = {"formation": "line", "spacing": 1.0,
                                "leader": {"actor": f"parsa.del_{_people}_lead"},
                                "members": [{"actor": f"parsa.del_{_people}_bearer",
                                             "count": _gift}]}


def R(region, actor, start, end, count, **kw):
    return dict(region=region, actor=actor, route=(start, end), count=count, **kw)


def L(region, actor, lane, count, **kw):
    return dict(region=region, actor=actor, lane=lane, count=count, **kw)


SPRING_AUDIENCE = ["jan", "feb", "mar", "apr"]
SAIL = "sailing"

# What moves on each route. `row` names the climate's traffic row that becomes `by_month`
# (seasonlife.tokens), `months` limits the months; `hours` defaults by kind (`default_hours`).
TRAFFIC = [
    # -- the corner's old road and the Via Appia (AD 126) ------------------------------------
    R("latium_italy", "world.traveller", "corner:corner_road_s", "rome:aurelia_w", 2, row="road",
      note="walkers on the corner's old road to Rome's western gate"),
    R("latium_italy", "world.muleteer", "corner:corner_road_s", "rome:aurelia_w", 1,
      group="pack_donkeys", row="road", note="a pedlar with pack donkeys between the corner and Rome"),
    R("latium_italy", "world.traveller", "rome:appia_se", "brundisium:appia_brund_w", 4, row="road",
      note="travellers on the Via Appia, the road to Brundisium and the ships for Greece "
           "(Horace's journey, Satires 1.5)"),
    R("latium_italy", "world.traveller", "rome:appia_se", "capua:capua_station", 2,
      group="travellers_r", row="road", note="travellers with a freedman companion, staying at "
                                             "the mansiones and the inns of the Appia"),
    R("latium_italy", "world.muleteer", "rome:appia_se", "brundisium:appia_brund_w", 2,
      group="mule_train", row="caravan", note="mule trains of the Appia"),
    R("latium_italy", "rome.cart", "rome:appia_se", "beneventum:beneventum_fork", 2,
      carry="rome.goods_wine_amphora", row="road",
      note="ox carts with Campanian wine for Rome"),
    R("latium_italy", "rome.carriage", "rome:appia_se", "brundisium:appia_brund_w", 1,
      row="courier", note="a carriage of the cursus publicus, the state's post, changing mules "
                          "at each mutatio"),
    R("latium_italy", "rome.cart", "tibur:tibur_farm", "rome:appia_se", 1,
      carry="rome.goods_marble", row="road",
      note="travertine from the quarries below Tibur, carted to Rome"),
    R("latium_italy", "rome.farmer", "tibur:tibur_farm", "rome:appia_se", 1,
      group="farm_to_market_r", carry="rome.goods_oil_amphora", row="road",
      note="olive oil of Tibur taken down to Rome"),
    # -- Greece (432 BC) -----------------------------------------------------------------------
    R("attica_north", "athens.youth", "athens:academy_road_n", "academy:academy", 2, row="road",
      hours=["06:00", "18:30"], note="young men walking out to the gymnasium in the Academy"),
    R("attica_north", "athens.farmer", "base:acharnai_road_farm_625_176", "athens:acharnai_n", 1,
      group="farm_to_market_g", carry="world.goods_firewood", row="road",
      note="Acharnian farmers with firewood for the city"),
    R("attica_north", "world.donkey", "base:acharnai_road_yard_637_185", "athens:acharnai_n", 2,
      variant=1, carry="world.goods_charcoal",
      note="charcoal from the burners on Parnes carried down to Athens (Aristophanes, "
           "Acharnians)"),
    R("attica_north", "athens.farmer", "base:mesogeia_road_738_258", "athens:mesogeia_e", 1,
      group="farm_to_market_g", carry="world.goods_fish", row="road",
      note="fish from the east coast carried up to the city's market"),
    R("greece", "world.traveller", "eleusis:eleusis_w", "corinth:corinth_n", 2, row="road",
      note="travellers on the Megarid road between Eleusis and the Isthmus"),
    R("greece", "athens.cart", "corinth:corinth_n", "eleusis:eleusis_town", 1, row="road",
      carry="world.goods_amphorae", note="an ox cart with Corinthian pots for Attica"),
    R("greece", "athens.citizen", "corinth:corinth_n", "delphi:temple", 2, group="pilgrims_g",
      row="road", months=["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov"],
      note="consultants on the way to Delphi; the oracle was silent in the winter months "
           "(Plutarch)"),
    R("greece", "world.traveller", "corinth:corinth_s", "sparta:sparta_shrine", 2, row="road",
      note="travellers on the road from the Isthmus to Lakedaimon"),
    R("greece", "athens.cart", "corinth:corinth_s", "sparta:sparta_shrine", 1, row="road",
      carry="world.goods_sacks", note="grain carts in the Peloponnese"),
    R("greece", "athens.athlete", "corinth:corinth_s", "olympia:altis", 2, group="athletes_g",
      row="road", months=["may", "jun", "jul"],
      note="athletes and their trainers on the way to Olympia: the 87th games are this summer "
           "(432 BC), and athletes trained there for a month first"),
    R("greece", "world.traveller", "corinth:corinth_s", "olympia:altis", 1, row="road",
      note="travellers on the road west to Elis and Olympia"),
    R("ionia_lydia", "athens.ionian", "ephesus:ephesus_e", "base:ionian_road_856_228", 2,
      row="road", note="Ephesians on the road up the Kaystros valley; they turn back in the haze "
                       "of the seam, where the Greek years end"),
    # -- the Royal Road and the roads off it (c. 470 BC) ----------------------------------------
    R("anatolia", "parsa.courier", "sardis:sardis_station", "parsa:royal_road_station", 4,
      row="courier", hours=ALL_DAY,
      note="royal riders by relays, a fresh horse at every station; 'neither snow nor rain nor "
           "heat nor darkness' stops them (Herodotus 8.98)"),
    R("anatolia", "parsa.caravan_driver", "sardis:sardis_station", "babylon:etemenanki_court", 2,
      group="caravan", row="caravan", note="caravans on the Royal Road, stopping at the "
                                           "stations' inns (Herodotus 5.52)"),
    R("anatolia", "parsa.caravan_driver", "babylon:etemenanki_court", "parsa:royal_road_station",
      2, group="caravan", row="caravan", note="caravans from Babylon to Susa and Pārsa"),
    R("anatolia", "world.muleteer", "halys:halys_station", "euphrates_crossing:euph_station", 1,
      group="mule_train", row="caravan", note="mule trains over the Cappadocian plateau"),
    R("anatolia", "world.muleteer", "sardis:sardis_station", "halys:halys_station", 1,
      group="mule_train", row="caravan", note="mule trains from Lydia to the Halys"),
    R("anatolia", "world.traveller", "sardis:sardis_station", "susa:susa_town", 3, row="road",
      note="travellers with sealed travel documents, fed at the stations (Persepolis "
           "Fortification tablets)"),
    R("anatolia", "parsa.p_cart", "babylon:etemenanki_court", "susa:susa_town", 1, row="road",
      carry="world.goods_sacks", note="ox carts with barley for the king's stores"),
    R("anatolia", "parsa.p_cart", "susa:susa_town", "parsa:royal_road_station", 1, row="road",
      carry="world.goods_dates", note="carts with dates and grain for Pārsa's rations"),
    R("anatolia", "world.merchant", "euphrates_crossing:euph_station", "babylon:babylon_quay", 1,
      row="road", note="merchants following the Euphrates down to Babylon"),
    R("anatolia", "world.muleteer", "babylon:babylon_n", "euphrates_crossing:euph_station", 1,
      group="donkeys_home", row="caravan",
      note="boatmen walking their donkeys back upstream after selling their boats in Babylon "
           "(Herodotus 1.194)"),
    R("anatolia", "parsa.cavalryman", "babylon:etemenanki_court", "parsa:royal_road_station", 1,
      group="court", months=["mar", "nov"], hours=COURT,
      note="the court on the move: out of Babylon in spring, back for the winter, as Greek "
           "writers say (Xenophon, Cyropaedia 8.6.22)"),
    R("anatolia", "parsa.del_lydians_lead", "sardis:sardis_station", "parsa:royal_road_station",
      1, group="del_lydians", months=SPRING_AUDIENCE, hours=DAY,
      note="the Lydians' delegation travelling to Pārsa before the spring audience"),
    R("anatolia", "parsa.del_cappadocians_lead", "halys:halys_station",
      "parsa:royal_road_station", 1, group="del_cappadocians", months=SPRING_AUDIENCE, hours=DAY,
      note="the Cappadocians' delegation on the way to the spring audience"),
    R("anatolia", "parsa.del_armenians_lead", "euphrates_crossing:euph_station",
      "parsa:royal_road_station", 1, group="del_armenians", months=SPRING_AUDIENCE, hours=DAY,
      note="the Armenians' delegation coming down to the spring audience"),
    R("anatolia", "parsa.del_babylonians_lead", "babylon:etemenanki_court",
      "parsa:royal_road_station", 1, group="del_babylonians", months=SPRING_AUDIENCE, hours=DAY,
      note="the Babylonians' delegation on the way to the spring audience"),
    R("anatolia", "parsa.del_elamites_lead", "susa:susa_town", "parsa:royal_road_station", 1,
      group="del_elamites", months=SPRING_AUDIENCE, hours=DAY,
      note="the Elamites' delegation from Susa"),
    R("anatolia", "parsa.del_syrians_lead", "sidon:sidon_quay", "parsa:royal_road_station", 1,
      group="del_syrians", months=SPRING_AUDIENCE, hours=DAY,
      note="the Syrians' delegation from the coast"),
    R("anatolia", "world.traveller", "gordion:gordion_citadel", "base:royal_road_station_916_157",
      1, row="road", note="Phrygians on the way from Gordion to the Royal Road"),
    R("taurus", "world.muleteer", "base:cilician_road_station_985_163",
      "base:cilician_road_983_283", 1, group="mule_train", row="caravan",
      note="mule trains over the Cilician Gates between the plateau and the coast"),
    R("taurus", "world.traveller", "base:cilician_road_station_985_163",
      "base:cilician_road_983_283", 1, row="road", note="travellers through the Taurus pass"),
    R("east_med", "parsa.caravan_driver", "sidon:sidon_quay", "babylon:etemenanki_court", 1,
      group="caravan", row="caravan",
      note="a caravan with Phoenician goods (glass, purple cloth, cedar) bound for Babylon"),
    R("east_med", "parsa.del_arabs_lead", "sidon:sidon_quay", "babylon:etemenanki_court", 1,
      group="del_arabs", row="caravan",
      note="Arabs with dromedaries bringing frankincense, a gift Herodotus says they gave each "
           "year (3.97)"),
    R("east_med", "parsa.p_cart", "base:cilician_road_980_266", "sidon:sidon_quay", 1,
      carry="world.goods_logs", row="road",
      note="cedar from the mountains carted down to Sidon's ship-sheds"),
    R("iran_plateau", "parsa.p_cart", "parsa:pasargadae_n", "pasargadae:pasargadae_garden", 1,
      row="road", carry="world.goods_sacks", note="carts between Pārsa and Pasargadae"),
    R("iran_plateau", "parsa.cavalryman", "parsa:pasargadae_n", "pasargadae:cyrus_tomb", 1,
      row="road", note="riders on the cypress road to Pasargadae"),
    R("iran_plateau", "parsa.magus", "parsa:pasargadae_n", "pasargadae:cyrus_tomb", 1,
      row="road", hours=["06:00", "17:00"],
      note="a magus with the month's horse for Cyrus' tomb (Arrian 6.29)"),
    # -- sea lanes ---------------------------------------------------------------------------
    L("tyrrhenian", "world.fishing_boat", "base:corner_portus", 1, hours=SHORT_SEA,
      note="the corner's small coasting boat down to Portus"),
    L("tyrrhenian", "rome.merchantman", "base:corner_portus", 1, row=SAIL, hours=SHORT_SEA,
      note="a coaster calling at the corner's jetty"),
    L("tyrrhenian", "rome.merchantman", "base:grain_fleet", 3, row="grain", hours=ALL_DAY,
      carry="rome.goods_grain_sack",
      note="the Alexandrian grain fleet for Portus, sailing from late spring to early autumn"),
    L("tyrrhenian", "rome.merchantman", "base:ostia_brundisium", 3, row=SAIL, hours=ALL_DAY,
      note="merchantmen round the toe of Italy between Portus and Brundisium"),
    L("adriatic", "rome.merchantman", "base:ionian_crossing", 2, row=SAIL, hours=ALL_DAY,
      note="the passage from Brundisium to Greece; ships sail into the mist and the years"),
    L("seam_ionian", "athens.merchant", "base:ionian_greek", 3, row=SAIL, hours=SHORT_SEA,
      note="Greek merchant ships between the gulf, Kerkyra and the west"),
    L("seam_ionian", "athens.trireme", "base:ionian_greek", 1, row=SAIL, hours=SHORT_SEA,
      note="an Athenian trireme on its way to Kerkyra, Athens' ally since 433"),
    L("saronic", "athens.trireme", "base:saronic", 2, row=SAIL, hours=SHORT_SEA,
      note="triremes exercising in the gulf: the fleet trained through the sailing season "
           "(Thucydides 1.80, 2.85)"),
    L("saronic", "athens.merchant", "base:saronic", 2, row=SAIL, hours=SHORT_SEA,
      note="merchant ships between Kenchreai and Piraeus"),
    L("aegean", "athens.merchant", "base:aegean_delos", 2, row=SAIL, hours=SHORT_SEA,
      note="ships for Delos and Ephesus, island to island"),
    L("aegean", "athens.trireme", "base:aegean_delos", 1, row=SAIL, months=["may"],
      hours=SHORT_SEA, note="the sacred ship carrying Athens' delegation to Apollo's festival "
                            "on Delos"),
    L("aegean", "athens.merchant", "base:hellespont", 4, row="grain", hours=ALL_DAY,
      carry="world.goods_sacks",
      note="grain ships from the Black Sea through the Hellespont for Piraeus"),
    L("east_med", "world.phoenician", "base:levant", 3, row=SAIL, hours=SHORT_SEA,
      note="Phoenician ships of Sidon along the coast"),
    L("persian_gulf", "world.reed_boat", "base:gulf_lane", 2, row="barge", hours=SHORT_SEA,
      carry="world.goods_dates", note="boats with dates from the head of the Gulf"),
    L("persian_gulf", "world.kelek", "base:karun_boats", 1, row="barge", hours=DAY,
      note="a raft on skins floating goods down to Susa's river"),
    L("mesopotamia", "world.quffa", "base:euphrates_boats", 2, row="barge", hours=DAY,
      carry="world.goods_amphorae",
      note="round leather boats bringing wine down to Babylon (Herodotus 1.194)"),
]


# -- the joined graph ---------------------------------------------------------------------------

class Joined:
    """Every layer's graph as one: nodes `layer:id`, edges weighted by their course in tiles,
    portals of one id across layers joined (the engine's road graph)."""

    def __init__(self, graphs: dict[str, Graph]):
        self.adj: dict[str, list[tuple[str, int]]] = {}
        self.kind: dict[str, str | None] = {}
        self.via: dict[tuple[str, str], list[tuple[int, int]]] = {}
        portals: dict[str, list[str]] = {}
        for name, g in sorted(graphs.items()):
            for n in g.nodes:
                key = f"{name}:{n.id}"
                self.kind[key] = n.kind
                self.adj.setdefault(key, [])
                if n.kind == "portal":
                    portals.setdefault(n.id, []).append(key)
            for e in g.edges:
                a, b = g.node(e.a), g.node(e.b)
                if a is None or b is None:
                    continue
                pts = [to_plan(*a.at), *[to_plan(*v) for v in e.via], to_plan(*b.at)]
                w = max(1, len(path_tiles(pts)) - 1)
                ka, kb = f"{name}:{e.a}", f"{name}:{e.b}"
                self.adj[ka].append((kb, w))
                self.adj[kb].append((ka, w))
                self.via[(ka, kb)], self.via[(kb, ka)] = pts, pts[::-1]
        for keys in portals.values():
            for a in keys:
                for b in keys:
                    if a != b:
                        self.adj[a].append((b, 0))

    def course(self, path: list[str]) -> list[tuple[int, int]]:
        """The plan tiles a path walks, edge by edge (portal joins add none)."""
        out: list[tuple[int, int]] = []
        for a, b in zip(path, path[1:]):
            pts = self.via.get((a, b))
            if pts:
                out += path_tiles(pts)
        return out

    def path(self, a: str, b: str) -> tuple[list[str], int] | None:
        if a not in self.adj or b not in self.adj:
            return None
        dist, prev, q = {a: 0}, {}, [(0, a)]
        while q:
            d, n = heapq.heappop(q)
            if n == b:
                break
            if d > dist[n]:
                continue
            for m, w in self.adj[n]:
                if d + w < dist.get(m, 1 << 60):
                    dist[m], prev[m] = d + w, n
                    heapq.heappush(q, (d + w, m))
        if b not in dist:
            return None
        out = [b]
        while out[-1] != a:
            out.append(prev[out[-1]])
        return out[::-1], dist[b]


REST = re.compile(r"(station|_town$|quay|harbour|landing|_farm_|_yard_|court|garden|altis|"
                  r"citadel|shrine|temple|academy$|lechaion|kenchreai|fork|tomb)")


def rest_stops(path: list[str], kind: dict[str, str | None]) -> list[str]:
    """Where travellers on this path stop for the night, in order: relay stations and inns,
    farms that take in travellers, towns, sanctuaries and harbours (never a bare junction)."""
    out = []
    for n in path:
        layer, nid = n.split(":", 1)
        if kind.get(n) == "station" or REST.search(nid) or \
                (layer != "base" and kind.get(n) == "dest"):
            if n not in out:
                out.append(n)
    return out


def offsets(tid: str, count: int) -> list[float]:
    """Irregular shares of the period for `count` instances: evenly spaced, each moved by up to
    a third of the gap (a stable hash), so instances never pass at a clockwork beat."""
    out = []
    for k in range(count):
        j = (hash64(f"{tid}:{k}") % 1000) / 1000.0 - 0.5
        out.append(round(((k + 0.66 * j) / count) % 1.0, 3))
    return out


def default_hours(tk: dict) -> list[str]:
    a = tk.get("actor", "")
    name = a.split(".")[-1]
    if name == "courier":
        return ALL_DAY
    if "fishing" in name:
        return FISHING
    if tk.get("lane"):
        return SHORT_SEA
    if tk.get("group") in ("drove", "transhumance"):
        return DROVE
    return DAY


def finish(doc: dict, graphs: dict[str, Graph], joined: Joined | None = None) -> None:
    """`id`, `hours`, `rest` and `offsets` on every token of a region file (any file: city,
    town, stretch), from its own route or lane."""
    joined = joined or Joined(graphs)
    for i, tk in enumerate(doc.get("lanes_tokens", [])):
        tk.setdefault("id", f"{doc['id']}.{i}")
        tk.setdefault("hours", default_hours(tk))
        if "lane" in tk:
            layer, lid = tk["lane"].split(":", 1)
            ln = next((x for x in graphs[layer].lanes if x.id == lid), None) if layer in graphs else None
            ports = [p.id for p in ln.ports if p.id not in ("start", "end")] if ln else []
            tk.setdefault("rest", ports or ["start"])
        elif "route" in tk:
            p = joined.path(tk["route"]["start"], tk["route"]["end"])
            if p:
                tk.setdefault("rest", rest_stops(p[0], joined.kind) or
                              [tk["route"]["start"], tk["route"]["end"]])
        tk["offsets"] = offsets(tk["id"], int(tk.get("count", 1)))


def apply(docs: dict, graphs: dict[str, Graph]) -> None:
    """File the TRAFFIC table's entries (and the groups they name) in their regions."""
    for e in TRAFFIC:
        if e["region"] not in docs:
            continue
        doc = docs[e["region"]]
        tk = {"actor": e["actor"]}
        if "lane" in e:
            tk["lane"] = e["lane"]
        else:
            tk["route"] = {"start": e["route"][0], "end": e["route"][1]}
        tk["count"] = e["count"]
        for k in ("group", "carry", "variant", "hours"):
            if k in e:
                tk[k] = e[k]
        if "months" in e:
            tk["when"] = {"months": list(e["months"])}
        if e.get("row"):
            tk["_row"] = e["row"]     # resolved against the region's climate by seasonlife
        tk["note"] = e["note"]
        doc["lanes_tokens"].append(tk)
        g = e.get("group")
        if g and not any(x["id"] == g for x in doc["groups"]):
            doc["groups"].append({"id": g, **GROUPS[g]})


def routes_named(doc: dict) -> list[tuple[str, str]]:
    return [(tk["route"]["start"], tk["route"]["end"]) for tk in doc.get("lanes_tokens", [])
            if "route" in tk]
