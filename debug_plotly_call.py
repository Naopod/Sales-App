"""Check how Plotly.newPlot is called in the generated HTML."""
from client_analytics.services.visualizations import viz_clients
import re

records = [
    {'period': 'Q1', 'family': 'A', 'value': 10},
    {'period': 'Q2', 'family': 'A', 'value': 20},
]
html = viz_clients.create_client_period_family_stacked(records, 'value', 'Test')

# Find the Plotly.newPlot call
idx = html.find('Plotly.newPlot')
if idx >= 0:
    snippet = html[idx:idx+300]
    print("Plotly.newPlot call:")
    print(snippet)
    print()
    
# Check if data is stored on the div element after newPlot
# Plotly.newPlot automatically stores data and layout on the div
print("Contains 'responsive':", 'responsive' in html)
print("Contains 'config':", 'config' in html)

# Check the full script section
script_start = html.find('<script type="text/javascript">', html.find('plotly-graph-div'))
script_end = html.find('</script>', script_start)
if script_start > 0 and script_end > 0:
    script = html[script_start:script_end+9]
    print("\nFull script section:")
    print(script)
