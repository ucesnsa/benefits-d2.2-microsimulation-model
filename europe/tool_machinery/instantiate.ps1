param([Parameter(Mandatory=$true)][string]$countryJson,[Parameter(Mandatory=$true)][string]$outPath)
# Location-independent instantiator: template.html (in this folder) + a COUNTRY block -> a finished tool.
# This is the ONLY sanctioned way to produce a country tool. Never rewrite the tool; only swap the COUNTRY block.
$ErrorActionPreference="Stop"
$here=Split-Path -Parent $MyInvocation.MyCommand.Definition
$U=[Text.Encoding]::UTF8; $u8=New-Object Text.UTF8Encoding $false
$tpl=[IO.File]::ReadAllText((Join-Path $here "template.html"),$U)
$c=[IO.File]::ReadAllText($countryJson,$U)
$null=$c|ConvertFrom-Json          # fail fast if the COUNTRY block is not valid JSON
$out=$tpl.Replace('__COUNTRY_JSON__',$c)
if(([regex]::Matches($out,'__COUNTRY_JSON__')).Count -ne 0){throw "placeholder not fully replaced"}
[IO.File]::WriteAllText($outPath,$out,$u8)
"wrote "+(Split-Path $outPath -Leaf)+" : "+$out.Length+" bytes"
