import re
import traceback
from typing import List, Dict, Optional

class PEMTemplateMatcher:
    """
    Library for canonicalizing and matching Python error messages (PEMs).
    """

    def __init__(self):
        # Dictionary: canonical PEM template -> list of raw PEMs (and metadata)
        self.template_db: Dict[str, List[Dict]] = {}

    # ---------- 1. Canonicalize from Live Exception (traceback) ----------

    @staticmethod
    def canonicalize_traceback(tb_list, exc_type):
        """
        Converts a parsed traceback and exception type into a canonical template.
        """
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
        return template

    # ---------- 2. Canonicalize Raw PEM String (Regex) ----------

    @staticmethod
    def canonicalize_raw_pem(raw_pem: str) -> str:
        """
        Uses regex to mask variable info from a PEM string, creating a template.
        """
        # Mask variable names, numbers, file paths, etc.
        pem = re.sub(r"name '.*?' is not defined", "name '<VAR>' is not defined", raw_pem)
        pem = re.sub(r"line \d+", "line <NUM>", pem)
        pem = re.sub(r'File ".*?"', 'File "<PATH>"', pem)
        pem = re.sub(r"in [a-zA-Z_][\w]*", "in <FUNC>", pem)
        # Optionally mask values in common exceptions
        pem = re.sub(r"ZeroDivisionError:.*", "ZeroDivisionError: <MSG>", pem)
        pem = re.sub(r"NameError:.*", "NameError: <MSG>", pem)
        pem = re.sub(r"TypeError:.*", "TypeError: <MSG>", pem)
        pem = re.sub(r"ValueError:.*", "ValueError: <MSG>", pem)
        pem = re.sub(r"IndexError:.*", "IndexError: <MSG>", pem)
        # Add more patterns as needed
        return pem.strip()

    def add_raw_pem(self, raw_pem: str, metadata: Optional[Dict] = None):
        template = self.canonicalize_raw_pem(raw_pem)
        entry = {"pem": raw_pem, "metadata": metadata or {}}
        self.template_db.setdefault(template, []).append(entry)
        return template

    # ---------- 3. Exact or Fuzzy Template Lookup ----------

    def match_pem(self, new_pem: str, fuzzy: bool = False, min_ratio: float = 0.85):
        """
        Canonicalize the new PEM and try to match it in the template DB.
        If fuzzy=True, use difflib to find best match if no exact match found.
        """
        import difflib
        new_template = self.canonicalize_raw_pem(new_pem)
        # Exact match first
        if new_template in self.template_db:
            return new_template, self.template_db[new_template]

        # Optionally do fuzzy match
        if fuzzy:
            matches = difflib.get_close_matches(new_template, self.template_db.keys(), n=1, cutoff=min_ratio)
            if matches:
                match = matches[0]
                return match, self.template_db[match]
        return None, None

    def get_all_templates(self) -> List[str]:
        return list(self.template_db.keys())

    def clear_db(self):
        self.template_db.clear()