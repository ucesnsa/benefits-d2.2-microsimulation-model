"""Make the LITE view of the all-country provider tool from the plain-language provider tool of
September 2026 (`plain_language_source.html`, a provider-only page for Spain, Italy, Greece and the
United Kingdom), read-only.

Three sentences name the model and the survey. For a country whose income effect is derived
rather than modelled (D.derived) they say so instead; for the modelled countries every sentence
renders exactly as before. Each patch is asserted to match once.

Run: py make_lite_template.py  ->  lite_template.html (placeholders @@DATA@@ etc. kept)
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import LITE_SOURCE as SRC  # noqa: E402
OUT = os.path.join(HERE, "lite_template.html")
t = io.open(SRC, encoding="utf-8").read()


def sub(old, new):
    global t
    n = t.count(old)
    assert n == 1, "patch anchor found %d times: %r" % (n, old[:90])
    t = t.replace(old, new)


# Home: how extra income is worked out.
sub('It is worked out with <span data-f="engine"></span>, a model of the tax and benefit system run on <span data-f="survey"></span>.',
    '<span data-f="incomehow"></span>')
# Price-base line.
sub('extra income is at <span data-f="incomeyear"></span> prices, the year of the model’s income data, exactly as in the full tool.',
    'extra income is at <span data-f="incomeyear"></span> prices<span data-f="incomeyearwhy"></span>')
# The field values, and the footnote.
sub('    footnote:"Built on the BENEFITS D2.2 Microsimulation Valuation Tool: "+D.engine+", run on "+D.survey+". Costs and outcome values at 2024 prices; extra income at "+D.incomeYear+" prices. Figures only, no personal data.",incomeyear:D.incomeYear};',
    '    footnote:(D.derived'
    '?"Built on the BENEFITS D2.2 Microsimulation Valuation Tool. There is no microsimulation for "+D.countryName+": extra income is estimated from national minimum-income data. Costs and outcome values at 2024 prices; extra income at "+D.incomeYear+" prices. Figures only, no personal data."'
    ':"Built on the BENEFITS D2.2 Microsimulation Valuation Tool: "+D.engine+", run on "+D.survey+". Costs and outcome values at 2024 prices; extra income at "+D.incomeYear+" prices. Figures only, no personal data."),'
    'incomeyear:D.incomeYear,\n'
    '    incomehow:(D.derived'
    '?"For "+D.countryName+" there is no model run, so it is estimated from national data on the minimum-income scheme: what the scheme pays and how many people it reaches. Treat it as an estimate."'
    ':"It is worked out with "+D.engine+", a model of the tax and benefit system run on "+D.survey+"."),\n'
    '    incomeyearwhy:(D.derived?", the year of the national data it is estimated from.":", the model’s 2023 income data brought to 2024 prices on the GDP deflator, exactly as in the full tool.")};')
# Currency label in brackets: the bare code (identical for the euro and the pound).
sub('Yearly running cost (<span data-f="cur"></span>)', 'Yearly running cost (<span data-f="curlabel"></span>)')
sub('F={country:D.countryName,cur:CUR,', 'F={country:D.countryName,cur:CUR,curlabel:CUR.trim(),')

# The running cost follows the service until the user types one (the fix made in the full
# tool, 2026-09-30): filled as people x the cost per person in force.
sub('function render(){', 'var COST_TOUCHED=false;\nfunction render(){\n  (function(){if(COST_TOUCHED)return;var s=svcByName($("f-svc").value);if(!s)return;'
    'var uc=(UC[s.name]!=null&&isFinite(UC[s.name]))?UC[s.name]:s.unitCost;'
    '$("f-cost").value=String(Math.round((+$("f-people").value||0)*uc));})();')
sub('<div><b>Yearly running cost</b>Everything the service costs in a year: staff, rent, materials.</div>',
    '<div><b>Yearly running cost</b>Everything the service costs in a year: staff, rent, materials. Until you type your own, '
    'the tool fills it in as the people you help times our cost per person for the service.</div>')
# The worked example matches the new defaults: 12 staff, not 10, so a new user does not start at 100% full.
sub('For example, 10 staff taking 50 clients each can help 500 people a year.',
    'For example, 12 staff taking 50 clients each can help 600 people a year.')
sub('  ["f-people","f-cost","f-prof","f-eps","f-ref","f-staff","f-casesper","f-shock"].forEach(function(id){',
    '  $("f-cost").addEventListener("input",function(){COST_TOUCHED=true;});\n'
    '  ["f-people","f-cost","f-prof","f-eps","f-ref","f-staff","f-casesper","f-shock"].forEach(function(id){')
# The cash floor at the panel's price base, as in the full tool.
sub('const pbW=bandWt*10/(k*UNITS_M*HH_SIZE),pbU=bandUnwt*10/(k*UNITS_M*HH_SIZE),',
    'const UP=(D.uprate||1),pbW=bandWt*10/(k*UNITS_M*HH_SIZE)*UP,pbU=bandUnwt*10/(k*UNITS_M*HH_SIZE)*UP,')

io.open(OUT, "w", encoding="utf-8", newline="\n").write(t)
print("lite_template.html", len(t.encode("utf-8")), "bytes")
