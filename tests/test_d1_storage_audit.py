"""Read-only D1 storage inspection invariants without Cloudflare credentials."""
from __future__ import annotations
import unittest
from scripts.arvexq_d1_storage_audit import audit, summarize, FREE_DB_LIMIT, PAID_DB_LIMIT

class ReadOnlyD1StorageTest(unittest.TestCase):
    def test_plan_limits_are_not_confused(self):
        self.assertEqual(FREE_DB_LIMIT,500_000_000)
        self.assertEqual(PAID_DB_LIMIT,10_000_000_000)
        rows=[{"name":"primary","uuid":"1234","file_size":480_000_000}]
        free=summarize(rows,plan="free")
        paid=summarize(rows,plan="paid")
        unknown=summarize(rows,plan="unknown")
        self.assertTrue(free["critical"])
        self.assertFalse(paid["warning"])
        self.assertIsNone(unknown["critical"])
        self.assertEqual(free["writes_performed"],0)
        self.assertEqual(free["databases"][0]["mb"],480.0)

    def test_no_fake_capacity_when_d1_omits_size(self):
        with self.assertRaisesRegex(ValueError,"missing"):
            summarize([{"name":"missing"}],plan="free")

    def test_only_get_endpoints_and_no_writes(self):
        requested=[]
        def get(path,token):
            requested.append((path,token))
            if path.endswith("/d1/database?per_page=100"):
                return {"success":True,"result":[{"name":"production","uuid":"abc"},{"name":"old","uuid":"def"}]}
            if path.endswith("/abc"):
                return {"success":True,"result":{"name":"production","uuid":"abc","file_size":485_000_000}}
            raise AssertionError("not entitled to visit other databases")
        result=audit("account-id","hidden",database_name="production",plan="free",get=get)
        self.assertTrue(result["critical"])
        self.assertEqual(len(requested),2)
        self.assertTrue(all(path.startswith("/accounts/") for path,_ in requested))
        self.assertEqual({token for _,token in requested},{"hidden"})

    def test_no_credentials_no_query(self):
        with self.assertRaises(RuntimeError):
            audit("","",get=lambda *_: self.fail("never network"))

if __name__=="__main__":
    unittest.main()
