import re
import traceback
import builtins
from typing import List, Dict, Optional

class PEMTemplateMatcher:
    """
    Canonicalize and match Python error messages (PEMs).
    Supports live exceptions and raw PEM logs.
    """

    def __init__(self, extra_exceptions: Optional[List[str]] = None):
        # Gather all built-in exception names
        self.exception_names = set(
            obj.__name__ for obj in vars(builtins).values()
            if isinstance(obj, type) and issubclass(obj, BaseException)
        )
        # Add user-supplied/custom exception names
        if extra_exceptions:
            self.exception_names.update(extra_exceptions)

        # Template DB: canonical template -> list of raw PEMs and metadata
        self.template_db: Dict[str, List[Dict]] = {}

    # --------- 1. Manual/regex masking for common patterns ----------
    @staticmethod
    def manual_masking(pem: str) -> str:
        pem = re.sub(r"name '.*?' is not defined", "name '<VAR>' is not defined", pem)
        pem = re.sub(r"line \d+", "line <NUM>", pem)
        pem = re.sub(r'File ".*?"', 'File "<PATH>"', pem)
        pem = re.sub(r"in [a-zA-Z_][\w]*", "in <FUNC>", pem)
        pem = re.sub(r"'[A-Za-z0-9_]+'", "'<STR>'", pem)  # quoted variable/values
        pem = re.sub(r"\d+\.\d+|\d+", "<NUM>", pem)        # standalone numbers
        return pem

    # --------- 2. Auto-mask all built-in/custom exceptions ----------
    def exception_masking(self, pem: str) -> str:
        for exc_name in self.exception_names:
            pem = re.sub(fr"{exc_name}:.*", f"{exc_name}: <MSG>", pem)
        return pem

    # --------- 3. Canonicalize raw PEM string (combine both) --------
    def canonicalize_raw_pem(self, raw_pem: str) -> str:
        pem = self.manual_masking(raw_pem)
        pem = self.exception_masking(pem)
        return pem.strip()

    # --------- 4. Canonicalize live exception using traceback -------
    @staticmethod
    def canonicalize_traceback(tb_list, exc_type):
        skeleton = []
        for frame in tb_list:
            skeleton.append('File "<PATH>", line <NUM>, in <FUNC>')
        skeleton.append(f"{exc_type}: <MSG>")
        return "\n".join(skeleton)

    def add_live_exception(self, exception: Exception, metadata: Optional[Dict] = None):
        tb_list = traceback.extract_tb(exception.__traceback__)
        exc_type = type(exception).__name__
        template = self.canonicalize_traceback(tb_list, exc_type)
        raw_pem = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        entry = {"pem": raw_pem, "metadata": metadata or {}}
        self.template_db.setdefault(template, []).append(entry)
        return template, raw_pem

    # --------- 5. Add raw PEM string to DB -------------------------
    def add_raw_pem(self, raw_pem: str, metadata: Optional[Dict] = None):
        template = self.canonicalize_raw_pem(raw_pem)
        entry = {"pem": raw_pem, "metadata": metadata or {}}
        self.template_db.setdefault(template, []).append(entry)
        return template, raw_pem

    # --------- 6. Exact/fuzzy template lookup ----------------------
    def match_pem(self, new_pem: str, fuzzy: bool = False, min_ratio: float = 0.85):
        import difflib
        new_template = self.canonicalize_raw_pem(new_pem)
        # Exact match
        if new_template in self.template_db:
            return new_template, self.template_db[new_template]
        # Fuzzy match (optional)
        if fuzzy:
            matches = difflib.get_close_matches(new_template, self.template_db.keys(), n=1, cutoff=min_ratio)
            if matches:
                match = matches[0]
                return match, self.template_db[match]
        return None, None

    def _extract_message_from_raw(self, raw: str, exc_type: Optional[str] = None) -> Optional[str]:
        # Try to find the exception message in the last non-empty line
        lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
        if not lines:
            return None
        last = lines[-1]
        # If exc_type known, prefer that line
        if exc_type:
            for ln in reversed(lines):
                if ln.startswith(f"{exc_type}:"):
                    last = ln
                    break
        if ":" in last:
            return last.split(":", 1)[1].strip()
        return last

    def format_template_for_display(self, template: str, entries: Optional[List[Dict]] = None) -> str:
        # If template ends with '<MSG>', try to substitute a representative message for display
        lines = template.splitlines()
        if not lines:
            return template
        last = lines[-1]
        m = re.match(r"^([A-Za-z_][\w]*)\:\s*<MSG>$", last)
        if m and entries:
            exc_type = m.group(1)
            msg = None
            # Pick the first entry's raw PEM to extract a message
            raw = None
            for e in entries:
                raw = e.get("pem")
                if raw:
                    break
            if raw:
                msg = self._extract_message_from_raw(raw, exc_type=exc_type)
            if msg:
                lines[-1] = f"{exc_type}: {msg}"
                return "\n".join(lines)
        return template

    def get_all_templates(self) -> List[str]:
        return list(self.template_db.keys())

    def clear_db(self):
        self.template_db.clear()

# ------------------ EXAMPLE USAGE ------------------

if __name__ == "__main__":
    matcher = PEMTemplateMatcher(extra_exceptions=["CustomAppException"])

    # Add a live exception
    try:
        def foo(): bar()
        def bar(): 1/0
        foo()
    except Exception as e:
        live_tmpl, live_raw = matcher.add_live_exception(e, metadata={"example": "ZeroDivisionError"})
        print("\n[Live exception template (canonical)]:\n", live_tmpl)
        print("\n[Live exception template (display)]:\n", matcher.format_template_for_display(live_tmpl, matcher.template_db.get(live_tmpl)))
        print("\n[Live exception (raw)]:\n", live_raw)

    # Add a raw PEM (string)
    raw_pem = "NameError: name 'foo' is not defined"
    raw_tmpl, raw_raw = matcher.add_raw_pem(raw_pem, metadata={"example": "NameError historical"})
    print("\n[Raw PEM template (canonical)]:\n", raw_tmpl)
    print("\n[Raw PEM template (display)]:\n", matcher.format_template_for_display(raw_tmpl, matcher.template_db.get(raw_tmpl)))
    print("\n[Raw PEM (original)]:\n", raw_raw)

    # Add a custom PEM (user-defined exception)
    matcher.add_raw_pem("CustomAppException: failed to connect", metadata={"example": "custom"})

    # Match a new PEM
    new_pem = "NameError: name 'bar' is not defined"
    match, entries = matcher.match_pem(new_pem)
    print("\n[Match found?]", bool(match))
    if match:
        print("[Matched template]:", matcher.format_template_for_display(match, entries))
        print("[Previous instances]:", entries)
    else:
        print("[No match found]")

    # Fuzzy match example
    almost_pem = "NameError: variable 'baz' isn't defined"
    match, entries = matcher.match_pem(almost_pem, fuzzy=True)
    print("\n[Fuzzy match found?]", bool(match))
    if match:
        print("[Fuzzy matched template]:", matcher.format_template_for_display(match, entries))
        print("[Previous instances]:", entries)
    else:
        print("[No fuzzy match found]")