from auth.engine import AuthEngine
from blockchain.chain import Blockchain
from config import POW_DIFFICULTY
from database.dao import Database


class AppContext:
    def __init__(self):
        self.db = Database()
        self.auth = AuthEngine(self.db)
        self.keyring = None
        self.user = "investigator"
        self.chain = None
        self.reload_chain()

    def reload_chain(self):
        blocks = self.db.load_blocks()
        self.chain = Blockchain(POW_DIFFICULTY, blocks)
        if not blocks:
            self.db.save_block(self.chain.chain[0])

    def record(self, action, detail, evidence_id=None, sha256=None):
        block = self.chain.add_block({"action": action, "evidence_id": evidence_id,
                                      "sha256": sha256, "actor": self.user, "detail": detail})
        self.db.save_block(block)
        self.db.log(self.user, action, detail)
        return block

    def save_evidence(self, case_id, etype, title, **fields):
        eid = self.db.add_evidence(self.keyring["db"], case_id, etype, title, **fields)
        block = self.record("EVIDENCE_ADDED", f"{etype}: {title}", eid, fields.get("file_sha256"))
        self.db.set_block_index(eid, block.index)
        return eid, block

    def case_options(self):
        return [f"{c['id']} | {c['case_number']} - {c['title']}" for c in self.db.list_cases()]

    def evidence_options(self):
        return [f"{e['id']} | {e['evidence_type']} | {e['case_number']} | {e['title']}"
                for e in self.db.list_evidence()]


def parse_id(text: str):
    try:
        return int(text.split("|")[0].strip())
    except (ValueError, AttributeError):
        return None
