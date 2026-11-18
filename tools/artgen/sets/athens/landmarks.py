"""All Athens landmarks (athens.md §2.3, §3.2, §3.7), gathered from the district modules."""

from sets.athens import acropolis, agora, city, piraeus, waypoints

LANDMARKS = {**acropolis.LANDMARKS, **agora.LANDMARKS, **city.LANDMARKS, **piraeus.LANDMARKS, **waypoints.LANDMARKS}
