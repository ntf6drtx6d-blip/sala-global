Patch your ui/setup.py airport search block to use core.geocoding.search_airport.

1) Add import:
from core.geocoding import search_airport

2) In your state defaults add:
"last_airport_query": "",
"airport_country": "-",

3) Replace the direct requests.get(...) Nominatim call inside the Find airport button
with the block from AIRPORT_SEARCH_BLOCK.py in this zip.
