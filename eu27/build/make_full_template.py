"""Make the FULL view of the all-country provider tool from the shipped D2.2 template.

The full view IS the Provider tab of the shipped four-tab tool: the same markup, the same
renderProvider and helpers, the same provenance marks. This script reads the shipped template
read-only and applies a short list of patches, each asserted to match exactly once, so a change
to the shipped template that moves a patched line stops the build instead of silently producing
a different tool.

What the patches do:
  1. Drop the tab bar and the Home, Analyst and Scenarios panels; show the Provider panel.
  2. Replace init() with a provider-only init (no dials, no scenarios).
  3. Guard baselineMag() so a country with no modelled unemployment dial renders no poverty rows
     instead of throwing. Countries with a surface behave exactly as before.
  4. For countries whose income effect is DERIVED rather than modelled (COUNTRY.income_basis ===
     "derived"), say so wherever the panel says "engine" or "surface". Modelled countries keep the
     shipped wording word for word.
  5. The citable export describes a provider tool (no analyst reform lines) and cites the page
     the user is on rather than the frame.

Run: py make_full_template.py  ->  full_template.html (placeholder __COUNTRY_JSON__ kept)
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import MACH  # noqa: E402
SRC = os.path.join(MACH, "template.html")
OUT = os.path.join(HERE, "full_template.html")

t = io.open(SRC, encoding="utf-8").read()


def sub(old, new, count=1):
    global t
    n = t.count(old)
    assert n == count, "patch anchor found %d times, expected %d: %r" % (n, count, old[:90])
    t = t.replace(old, new)


def cut(start, end):
    """Remove from the first occurrence of start up to (not including) end."""
    global t
    i = t.index(start)
    j = t.index(end, i)
    assert t.count(start) == 1, "cut start not unique: %r" % start[:80]
    t = t[:i] + t[j:]


# 1. Tab bar and the three other panels.
cut('<nav class="modes" role="tablist" aria-label="Tool mode">', '<main>')
cut('<section id="home" class="home" role="tabpanel"', '<section id="provider"')
cut('<section id="scenarios" role="tabpanel"', '</main>')
sub('<section id="provider" role="tabpanel" aria-labelledby="tab-provider" hidden>',
    '<section id="provider">')

# 2. Provider-only init.
old_init_start = 'function init(){\n  buildDials();setupExtras();\n'
old_init_end = '  renderAnalyst();renderProvider();renderScenarios();mode("home");\n}\ninit();'
i = t.index(old_init_start)
j = t.index(old_init_end, i) + len(old_init_end)
body = t[i:j]
assert t.count(old_init_start) == 1 and t.count(old_init_end) == 1
# setupExtras() also filled the page title, the currency labels and the footer note; the provider
# page needs those three, and none of its analyst or scenario parts.
body = body.replace('  buildDials();setupExtras();\n',
                    '  if(COUNTRY.title)document.title=COUNTRY.title;\n'
                    '  [].forEach.call(document.querySelectorAll(".cursym"),function(e){e.textContent=CUR.trim();});\n'
                    '  var fn=document.getElementById("foot-note");if(fn&&COUNTRY.provenance)fn.innerHTML=COUNTRY.provenance+" WEVM is median-anchored and AROP-floored. Service-demand response parameters are evidence-informed estimates with uncertainty bands.";\n')
k = body.index('  const tabs={home:')
body = body[:k] + '  renderProvider();\n}\ninit();'
t = t[:i] + body + t[j:]

# 3. No modelled unemployment dial -> no poverty rows, not an exception.
sub('function baselineMag(id){return GRID.dials[id].baseline_magnitude;}',
    'function baselineMag(id){return GRID.dials[id]?GRID.dials[id].baseline_magnitude:null;}')

# 4. Derived income effect: say so. DERIVED is false for the three modelled countries, so every
#    string below reduces to the shipped one for them.
sub('const lbl=k=>LABELS[k]||k;',
    'const lbl=k=>LABELS[k]||k;\nconst DERIVED=(COUNTRY.income_basis==="derived");')
sub("<span>Engine income (unweighted)<span class=\"rowgloss\">the same income effect counted pound-for-pound, before any distributional weighting</span></span>",
    "<span>'+(DERIVED?'Income effect (unweighted)':'Engine income (unweighted)')+'<span class=\"rowgloss\">the same income effect counted pound-for-pound, before any distributional weighting'+(DERIVED?'. For '+COUNTRY.name+' it is derived from national minimum-income data, not modelled: see the note below':'')+'</span></span>")
sub('$("#p-method").innerHTML="Headline = cash floor (engine income, welfare-weighted)',
    '$("#p-method").innerHTML="Headline = cash floor ("+(DERIVED?"the derived income effect":"engine income")+", welfare-weighted)')
sub("+HH_SIZE.toFixed(2)+' people per '+UNITN_ONE+', read from the surface rather than '\n      +'assumed.",
    "+HH_SIZE.toFixed(2)+' people per '+UNITN_ONE+(DERIVED?', from Eurostat household statistics rather than '\n      +'assumed.':', read from the surface rather than '\n      +'assumed.')+'")
sub("<b>ENGINE</b> (income effects from the microsimulation)",
    "<b>ENGINE</b> (income effects '+(DERIVED?'derived from national minimum-income data; there is no microsimulation for '+COUNTRY.name:'from the microsimulation')+')")

# 5. Export: a provider tool, citing the page the user is on.
sub('    "BENEFITS D2.2 "+COUNTRY.name+" microsimulation tool\\n"\n'
    '    +"Reform: "+_lab+" at "+_mag+"\\n"\n'
    '    +"Epsilon (inequality aversion): "+aEps+"\\n"\n'
    '    +"WEVM (welfare effect, "+CUR+"m vs baseline): "+((lastWevm==null)?"n/a":fmtM(lastWevm))+"\\n"\n'
    '    +"Fiscal cost (net to the public purse, "+CUR+"m): "+((_fis&&COUNTRY.fiscal_field)?money_m(_fis[COUNTRY.fiscal_field]):"not carried on this surface")+"\\n"\n',
    '    "BENEFITS D2.2 provider tool, "+COUNTRY.name+"\\n"\n'
    '    +"Epsilon (inequality aversion): "+pe+"\\n"\n')
sub('    +"Engine: "+(COUNTRY.code==="GB"?"PolicyEngine UK 2.45.4 / policyengine-core 3.23.6":"EUROMOD v3.8.6")+"\\n"\n',
    '    +"Income effect: "+(DERIVED?"derived from national minimum-income data (no microsimulation for this country)":(COUNTRY.code==="GB"?"PolicyEngine UK 2.45.4 / policyengine-core 3.23.6":"EUROMOD v3.8.6"))+"\\n"\n')
sub('    +"Price base: analyst money shown in 2024 terms. Provider figure: "+priceBaseOf(s)+"\\n"\n',
    '    +"Price base: "+priceBaseOf(s).replace(/^PRICE BASE:\\s*/i,"")+"\\n"\n')
# The per-person column header and its caption take the bare currency code ("SEK/benef").
sub("<th>'+CUR+'/benef</th>", "<th>'+CUR.trim()+'/benef</th>")
sub("<b>'+CUR+'/benef</b> is the value", "<b>'+CUR.trim()+'/benef</b> is the value")
sub('    +"Configuration: "+location.href+"\\n";',
    '    +"Configuration: "+(function(){try{return (window.parent!==window?window.parent.location.href:location.href);}catch(e){return location.href;}})()+"\\n";')

# 6. Currency labels: a non-euro code carries a trailing space for amounts ("SEK 1,234"); a label in
#    brackets takes the bare code. Identical for the euro and the pound.
sub('[].forEach.call(document.querySelectorAll(".cursym"),function(e){e.textContent=CUR;});',
    '[].forEach.call(document.querySelectorAll(".cursym"),function(e){e.textContent=CUR.trim();});')

assert "__COUNTRY_JSON__" in t
io.open(OUT, "w", encoding="utf-8", newline="\n").write(t)
print("full_template.html", len(t.encode("utf-8")), "bytes")
