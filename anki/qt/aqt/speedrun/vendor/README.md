# Vendored front-end libraries (Speedrun dev portal)

- `cytoscape.min.js` - Cytoscape.js v3.30.2, MIT License, (c) 2016-2024 The Cytoscape
  Consortium. Source: https://github.com/cytoscape/cytoscape.js
  Used only by the Speedrun dev portal ([`dev_portal.py`](../dev_portal.py)) to draw the
  interactive AAMC knowledge graph. It is inlined into the portal's HTML at runtime, so it
  is not served as a separate web asset. The full license text is in the file header.
