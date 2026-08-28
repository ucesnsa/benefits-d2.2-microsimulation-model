# LICENCE: EUPL-1.2, because this file imports the `euromod` connector, the European
# Commission's Python interface to the EUROMOD engine, which the European Union
# publishes under the European Union Public Licence v1.2. That licence is reciprocal,
# so it reaches this file through the import. The text is in
# europe/Italy/model/pipeline/LICENSE
# The connector's own package metadata classifies itself Other/Proprietary, which is
# wrong about its own package; NOTICES.md at the repository root records the true
# licence and the evidence for it.

"""
engine.py -- EUROMOD engine access for the EU build.

Responsibilities: load the model once; enforce the STANDING ENGINE RULE (every
simulation must run on the matched v3.8.6 engine, never the connector's bundled
engine, or il_xs_hl06 aborts IT and ES); wrap run() so the guard fires on every
call; read / locate model parameters for the reform layer; and keep the engine
audible.

WHY THE ENGINE IS AUDIBLE
-------------------------
Two calls would silence this module if it made them: Console.SetOut(TextWriter.Null)
on load, and verbose=False on every run. It makes neither. Measured on an IT_2023
baseline, the two suppress between them:

  * Console.SetOut(TextWriter.Null): the whole engine run log on .NET stdout,
    about 380 lines per run. That log carries the line stating how many variables
    the engine actually read from the input, the per-function execution trace, and
    the "FINISHED with N errors/warnings" summary.
  * verbose=False: the connector's own warning list, the programmatic copy of the
    same warnings, printed from the run result in euromod/core.py.

What neither of them touches is the engine's warning stream, which goes to .NET
stderr rather than stdout. So the line

    Warning: Variable(s) ... not found in user-provided lists (zero is used as default)

reaches the terminal either way, and on its own it scrolls past unread: the
"FINISHED with N errors/warnings" line that would prompt anyone to look at it
travels on the channel Console.SetOut closes. That warning is the only announcement
that input variables are missing, which is why the run does not depend on someone
catching it in the scrollback.

The engine is therefore audible by default:

  * the engine's own stdout and stderr are routed to a per-session run log rather
    than to nothing, so the execution trace and the variables-read line survive;
  * every run passes verbose=True, so the connector prints each warning to the
    console exactly once;
  * every run appends its warnings to logs/engine_warnings.log with a header
    naming the country, system, and dataset;
  * every run prints a one-line summary, and a NOT FOUND banner naming every
    variable the model asked for and did not get.

Set BENEFITS_ENGINE_QUIET=1 to silence all of it. That is not the default and
should not become one.

None of this changes any simulated number. It changes only what the run says.
"""
import datetime
import io
import os
import re
import sys

MODEL_PATH = os.environ.get(
    "EUROMOD_MODEL_PATH",
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 "euromod", "EUROMOD_RELEASES_J2.0+"),
)
MATCHED_ENGINE = r"C:\Program Files\EUROMOD\Executable"


def _default_log_dir():
    """europe/logs, resolved the same way from every copy of this module."""
    here = os.path.dirname(os.path.abspath(__file__))
    probe = here
    for _ in range(6):
        if os.path.basename(probe).lower() == "europe":
            return os.path.join(probe, "logs")
        nxt = os.path.dirname(probe)
        if nxt == probe:
            break
        probe = nxt
    return os.path.join(os.path.dirname(here), "logs")


LOG_DIR = os.environ.get("BENEFITS_ENGINE_LOG_DIR", _default_log_dir())
QUIET = os.environ.get("BENEFITS_ENGINE_QUIET", "") == "1"

RUN_LOG = os.path.join(LOG_DIR, "engine_run.log")
WARN_LOG = os.path.join(LOG_DIR, "engine_warnings.log")

_model = None
_console_writer = None          # keep a reference so .NET does not collect it
NOT_FOUND_RE = re.compile(r"Variable\(s\)\s+(.*?)\s+not found in user-provided lists")

LAST_WARNINGS = []
"""Warning lines printed by the connector for the most recent run."""
NOT_FOUND = {}
"""Variables the engine reported as not found, keyed by 'system/dataset'."""


class _Tee:
    """Write to several streams at once. Used to capture the connector's console
    output without taking it away from the console."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for st in self._streams:
            try:
                st.write(s)
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self._streams:
            try:
                st.flush()
            except Exception:
                pass

    def isatty(self):
        return False


def _route_console():
    """Send the .NET engine's stdout and stderr to the run log instead of nulling
    them. Failure here must never stop a run, so it degrades to leaving the
    console alone."""
    global _console_writer
    try:
        import clr  # noqa: F401
        from System import Console
        from System.IO import TextWriter, StreamWriter
        if QUIET:
            Console.SetOut(TextWriter.Null)
            return None
        os.makedirs(LOG_DIR, exist_ok=True)
        w = StreamWriter(RUN_LOG, True)
        w.AutoFlush = True
        Console.SetOut(w)
        Console.SetError(w)
        _console_writer = w
        return RUN_LOG
    except Exception as exc:            # noqa: BLE001
        print(f"engine: could not route the engine console to {RUN_LOG!r} ({exc}); "
              "leaving it on the terminal", file=sys.stderr)
        return None


def _em_assembly_location():
    """The file the live EM_Executable assembly was loaded from, or None if the
    engine has not been loaded yet (it loads on the first run)."""
    try:
        from System import AppDomain
        for a in AppDomain.CurrentDomain.GetAssemblies():
            try:
                if a.GetName().Name == "EM_Executable":
                    return a.Location
            except Exception:
                continue
    except Exception:
        pass
    return None


def assert_matched_engine():
    """STANDING ENGINE RULE guard. Fails loudly if the engine in use is not the
    matched v3.8.6 engine. Run before every simulation. Before the engine is
    loaded, it asserts the connector's resolved path; afterwards, the live
    assembly location."""
    loc = _em_assembly_location()
    if loc is not None:
        if not os.path.normcase(str(loc)).startswith(os.path.normcase(MATCHED_ENGINE)):
            raise RuntimeError(
                f"ENGINE GUARD FAILED: EM_Executable loaded from {loc!r}, not the matched "
                f"v3.8.6 engine at {MATCHED_ENGINE!r}. IT and ES would abort on il_xs_hl06. Aborting.")
        return str(loc)
    # not yet loaded: assert the path the connector will load from
    from euromod.utils import _paths
    env = os.getenv("EUROMOD_PATH", "")
    target = env or _paths.DLL_PATH
    if not os.path.normcase(str(target)).startswith(os.path.normcase(MATCHED_ENGINE)):
        raise RuntimeError(
            f"ENGINE GUARD FAILED: connector would load the engine from {target!r}, not the matched "
            f"v3.8.6 engine at {MATCHED_ENGINE!r}. Install v3.8.6 or set EUROMOD_PATH. Aborting.")
    return target


def load_model():
    """Load the model once, after asserting the engine path."""
    global _model
    if _model is None:
        if not os.path.isdir(MODEL_PATH):
            raise FileNotFoundError(f"EUROMOD model not found at {MODEL_PATH!r}; set EUROMOD_MODEL_PATH.")
        assert_matched_engine()  # pre-load path check
        from euromod import Model
        _model = Model(MODEL_PATH)
        routed = _route_console()
        if routed and not QUIET:
            print(f"engine: run log -> {routed}")
            print(f"engine: warning log -> {WARN_LOG}")
    return _model


def _record(system_name, dataset_id, captured):
    """Keep what the connector said, and say the important part again loudly."""
    global LAST_WARNINGS
    lines = [ln.rstrip() for ln in captured.splitlines()
             if ln.startswith("Warning:") or ln.startswith("Error:")]
    LAST_WARNINGS = lines
    missing = []
    for ln in lines:
        m = NOT_FOUND_RE.search(ln)
        if m:
            missing = [v.strip() for v in m.group(1).split(",") if v.strip()]
    if missing:
        NOT_FOUND[f"{system_name}/{dataset_id}"] = missing
    if QUIET:
        return
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with io.open(WARN_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"\n=== {datetime.datetime.now().isoformat(timespec='seconds')} "
                     f"{system_name} / {dataset_id} ===\n")
            if missing:
                fh.write(f"NOT FOUND ({len(missing)}): {', '.join(missing)}\n")
            for ln in lines:
                fh.write(ln + "\n")
            if not lines:
                fh.write("(no warnings)\n")
    except Exception as exc:            # noqa: BLE001
        print(f"engine: could not append to {WARN_LOG!r} ({exc})", file=sys.stderr)
    print(f"engine: {system_name} / {dataset_id}: {len(lines)} warning(s)"
          + (f", {len(missing)} input variable(s) NOT FOUND" if missing else ""))
    if missing:
        print("  !! NOT FOUND, the model read these and the input did not supply them; "
              "the engine used zero:")
        print("     " + ", ".join(missing))


def run(country_obj, system_name, data, dataset_id, constants=None, bta=False):
    """Run one simulation on the matched engine. The guard fires on every call,
    and the engine's warnings are printed and logged rather than dropped."""
    assert_matched_engine()
    sysobj = country_obj.systems[system_name]
    kw = {"verbose": not QUIET}
    if constants:
        kw["constantsToOverwrite"] = constants
    if bta:
        kw["switches"] = [("BTA", True)]
    if QUIET:
        return sysobj.run(data, dataset_id, **kw)
    buf = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = _Tee(real_stdout, buf)
    try:
        sim = sysobj.run(data, dataset_id, **kw)
    finally:
        sys.stdout = real_stdout
    _record(system_name, dataset_id, buf.getvalue())
    return sim


def get_system(country_obj, system_name):
    return country_obj.systems[system_name]


def read_constant(system_obj, name, group=None):
    """Read a DefConst constant's value string for a resolved system."""
    for p in system_obj.policies:
        for f in (getattr(p, "functions", None) or []):
            if getattr(f, "name", "") != "DefConst":
                continue
            for par in (getattr(f, "parameters", None) or []):
                if (getattr(par, "name", "") or "") == name and (
                        group is None or str(getattr(par, "group", "") or "") == str(group)):
                    return getattr(par, "value", None)
    return None


def find_amount_params(system_obj, policy, func, param_name, unit_suffix):
    """Return the live parameter objects (for in-memory mutation) in `policy` of
    type `func` named `param_name` whose value carries `unit_suffix` (e.g. '#m')."""
    out = []
    for p in system_obj.policies:
        if getattr(p, "name", "") != policy:
            continue
        for f in (getattr(p, "functions", None) or []):
            if getattr(f, "name", "") != func:
                continue
            for par in (getattr(f, "parameters", None) or []):
                if (getattr(par, "name", "") or "") == param_name:
                    v = getattr(par, "value", None)
                    if isinstance(v, str) and v.endswith(unit_suffix):
                        out.append(par)
    return out
