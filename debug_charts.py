"""Debug script to verify charts are rendered in the HTML."""
import django, os, re
os.environ['DJANGO_SETTINGS_MODULE'] = 'analytics_portal.settings'
django.setup()

from django.test import RequestFactory
from client_analytics.views import stats
from django.contrib.sessions.middleware import SessionMiddleware

factory = RequestFactory()
request = factory.get('/dataset/26/stats/', {'active_tab': 'clients', 'client': 'BEVDBN'})
middleware = SessionMiddleware(lambda req: None)
middleware.process_request(request)
request.session.save()

response = stats(request, pk=26)
content = response.content.decode('utf-8')

# Count plotly-graph-div occurrences
divs = re.findall(r'class="plotly-graph-div"', content)
print(f"Total plotly-graph-div in page: {len(divs)}")

# Check Plotly.newPlot calls
newplots_total = len(re.findall(r'Plotly\.newPlot', content))
print(f"Total Plotly.newPlot calls: {newplots_total}")

# Check in trend tab section specifically
trend_start = content.find('id="powerbi-trend"')
if trend_start > 0:
    # Find the end of the trend section (next major section or end)
    trend_section = content[trend_start:trend_start + 300000]
    graph_divs = len(re.findall(r'plotly-graph-div', trend_section))
    newplots = len(re.findall(r'Plotly\.newPlot', trend_section))
    aucun_msg = len(re.findall(r'Aucun graphique disponible', trend_section))
    print(f"\nIn powerbi-trend section:")
    print(f"  plotly-graph-div: {graph_divs}")
    print(f"  Plotly.newPlot: {newplots}")
    print(f"  'Aucun graphique disponible': {aucun_msg}")
    
    # Check which specific chart blocks exist
    for label in ['Montant par EF', 'Quantit', 'Prix Unitaire Net']:
        count = len(re.findall(label, trend_section))
        print(f"  '{label}': {count} occurrences")
else:
    print("ERROR: powerbi-trend section NOT FOUND in HTML!")

# Check for the "Vue Table" section
table_start = content.find('id="powerbi-table"')
if table_start > 0:
    table_section = content[table_start:table_start + 100000]
    print(f"\nIn powerbi-table section:")
    print(f"  plotly-graph-div: {len(re.findall(r'plotly-graph-div', table_section))}")
else:
    print("ERROR: powerbi-table section NOT FOUND!")

# Save a snippet around the trend section for inspection
if trend_start > 0:
    snippet = content[trend_start:trend_start + 2000]
    with open('debug_trend_snippet.html', 'w', encoding='utf-8') as f:
        f.write(snippet)
    print("\nSaved first 2000 chars of trend section to debug_trend_snippet.html")
