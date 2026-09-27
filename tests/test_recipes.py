import unittest
import json
import time
import tempfile
import datetime
from pathlib import Path

# Load registry.json recipes dynamically
REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "registry.json"

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    REGISTRY = json.load(f)

RECIPES_BY_ID = {r["id"]: r for r in REGISTRY["recipes"]}


class StdlibRecipesTests(unittest.TestCase):
    def test_registry_has_30_recipes(self):
        self.assertEqual(len(REGISTRY["recipes"]), 30)

    def test_all_recipes_have_required_fields(self):
        required_fields = {"id", "name", "replaces", "python_min_version", "modules", "code"}
        for r in REGISTRY["recipes"]:
            self.assertTrue(required_fields.issubset(r.keys()), f"Missing fields in {r.get('id')}")
            self.assertTrue(len(r["code"].strip()) > 0, f"Empty code in {r['id']}")

    def test_scrypt_password_hasher(self):
        code = RECIPES_BY_ID["scrypt-password-hasher"]["code"]
        namespace = {}
        exec(code, namespace)
        hash_password_scrypt = namespace["hash_password_scrypt"]
        verify_password_scrypt = namespace["verify_password_scrypt"]

        password = "super-secret-password-123"
        hashed, salt = hash_password_scrypt(password)
        self.assertIsInstance(hashed, bytes)
        self.assertIsInstance(salt, bytes)
        self.assertEqual(len(salt), 16)

        # Verification
        self.assertTrue(verify_password_scrypt(password, hashed, salt))
        self.assertFalse(verify_password_scrypt("wrong-password", hashed, salt))

    def test_bounded_task_pool(self):
        code = RECIPES_BY_ID["bounded-task-pool"]["code"]
        namespace = {}
        exec(code, namespace)
        BoundedTaskPool = namespace["BoundedTaskPool"]

        with BoundedTaskPool(max_workers=2) as pool:
            results = pool.map(lambda x: x * x, [1, 2, 3, 4, 5])
            self.assertEqual(results, [1, 4, 9, 16, 25])

    def test_ascii_table_formatter(self):
        code = RECIPES_BY_ID["ascii-table-formatter"]["code"]
        namespace = {}
        exec(code, namespace)
        render_table = namespace["render_table"]

        rows = [
            {"service": "auth-service", "status": "UP", "latency_ms": 12},
            {"service": "bus-bridge", "status": "UP", "latency_ms": 5},
        ]
        headers = ["service", "status", "latency_ms"]
        rendered = render_table(rows, headers)
        self.assertIn("auth-service", rendered)
        self.assertIn("bus-bridge", rendered)
        self.assertIn("+--", rendered)
        self.assertIn("| service", rendered)

    def test_token_bucket_rate_limiter(self):
        code = RECIPES_BY_ID["token-bucket-rate-limiter"]["code"]
        namespace = {}
        exec(code, namespace)
        TokenBucketLimiter = namespace["TokenBucketLimiter"]

        limiter = TokenBucketLimiter(refill_rate_per_sec=10.0, max_tokens=2)
        self.assertTrue(limiter.acquire(1))
        self.assertTrue(limiter.acquire(1))
        self.assertFalse(limiter.acquire(1))

    def test_dag_topological_sorter(self):
        code = RECIPES_BY_ID["dag-topological-sorter"]["code"]
        namespace = {}
        exec(code, namespace)
        compute_execution_order = namespace["compute_execution_order"]

        dag = {
            "build": {"lint", "test"},
            "test": {"setup"},
            "lint": {"setup"},
            "setup": set(),
        }
        order = compute_execution_order(dag)
        self.assertEqual(order[0], "setup")
        self.assertIn("lint", order[1:3])
        self.assertIn("test", order[1:3])
        self.assertEqual(order[-1], "build")

    def test_rfc8785_jcs_receipt_signer(self):
        code = RECIPES_BY_ID["rfc8785-jcs-receipt-signer"]["code"]
        namespace = {}
        exec(code, namespace)
        sign_canonical_receipt = namespace["sign_canonical_receipt"]
        verify_canonical_receipt = namespace["verify_canonical_receipt"]

        secret = b"fleet-master-key-xyz"
        payload = {"b": 2, "a": 1, "z": [3, 2, 1]}
        sig = sign_canonical_receipt(secret, payload)
        self.assertIsInstance(sig, str)
        self.assertTrue(verify_canonical_receipt(secret, payload, sig))
        self.assertFalse(verify_canonical_receipt(secret, {"b": 3, "a": 1}, sig))

    def test_data_contract(self):
        code = RECIPES_BY_ID["data-contract"]["code"]
        namespace = {}
        exec(code, namespace)
        DataContract = namespace["DataContract"]

        contract = DataContract(contract_id="C-101", max_budget_usd=50.0, allowed_ops=["read", "write"])
        data = json.loads(contract.to_json())
        self.assertEqual(data["contract_id"], "C-101")
        self.assertEqual(data["max_budget_usd"], 50.0)

        with self.assertRaises(ValueError):
            DataContract(contract_id="C-102", max_budget_usd=-5.0)

    def test_in_memory_sqlite_kv(self):
        code = RECIPES_BY_ID["in-memory-sqlite-kv"]["code"]
        namespace = {}
        exec(code, namespace)
        SQLiteKVStore = namespace["SQLiteKVStore"]

        store = SQLiteKVStore()
        store.set("foo", {"bar": 42})
        self.assertEqual(store.get("foo"), {"bar": 42})
        self.assertIsNone(store.get("absent"))

        # Test TTL expiration
        store.set("short-lived", "temp", ttl_seconds=0.05)
        self.assertEqual(store.get("short-lived"), "temp")
        time.sleep(0.06)
        self.assertIsNone(store.get("short-lived"))
        store.conn.close()

    def test_sliding_window_counter(self):
        code = RECIPES_BY_ID["sliding-window-counter"]["code"]
        namespace = {}
        exec(code, namespace)
        SlidingWindowCounter = namespace["SlidingWindowCounter"]

        counter = SlidingWindowCounter(window_seconds=1.0, max_hits=2)
        self.assertTrue(counter.record_and_check())
        self.assertTrue(counter.record_and_check())
        self.assertFalse(counter.record_and_check())

    def test_cron_pattern_matcher(self):
        code = RECIPES_BY_ID["cron-pattern-matcher"]["code"]
        namespace = {}
        exec(code, namespace)
        is_cron_due = namespace["is_cron_due"]

        # Monday is weekday 0 in python datetime.weekday()
        # 2026-09-21 was a Monday
        dt = datetime.datetime(2026, 9, 21, 14, 30)
        self.assertTrue(is_cron_due("30 14 * * 0", dt))
        self.assertTrue(is_cron_due("*/15 14 * * 0", dt))
        self.assertFalse(is_cron_due("0 14 * * 0", dt))

    def test_event_emitter(self):
        code = RECIPES_BY_ID["event-emitter"]["code"]
        namespace = {}
        exec(code, namespace)
        EventEmitter = namespace["EventEmitter"]

        emitter = EventEmitter()
        received = []
        emitter.on("alert", lambda msg: received.append(msg))
        emitter.emit("alert", "P0 security event")
        self.assertEqual(received, ["P0 security event"])

    def test_ip_address_validator(self):
        code = RECIPES_BY_ID["ip-address-validator"]["code"]
        namespace = {}
        exec(code, namespace)
        is_ip_in_network = namespace["is_ip_in_network"]
        is_private_ip = namespace["is_private_ip"]

        self.assertTrue(is_ip_in_network("192.168.1.50", "192.168.1.0/24"))
        self.assertFalse(is_ip_in_network("10.0.0.1", "192.168.1.0/24"))
        self.assertTrue(is_private_ip("10.0.0.1"))
        self.assertFalse(is_private_ip("8.8.8.8"))

    def test_uuidv7_monotonic_generator(self):
        code = RECIPES_BY_ID["uuidv7-monotonic-generator"]["code"]
        namespace = {}
        exec(code, namespace)
        generate_uuidv7 = namespace["generate_uuidv7"]

        u1 = generate_uuidv7()
        u2 = generate_uuidv7()
        self.assertEqual(u1.version, 7)
        self.assertEqual(u2.version, 7)
        self.assertTrue(str(u1) <= str(u2))

    def test_atomic_file_writer(self):
        code = RECIPES_BY_ID["atomic-file-writer"]["code"]
        namespace = {}
        exec(code, namespace)
        write_file_atomic = namespace["write_file_atomic"]

        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sub" / "output.txt"
            write_file_atomic(target, "hello atomic world")
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "hello atomic world")

    def test_env_config_loader(self):
        code = RECIPES_BY_ID["env-config-loader"]["code"]
        namespace = {}
        exec(code, namespace)
        get_env_var = namespace["get_env_var"]

        import os
        os.environ["TEST_NUM_WORKERS"] = "16"
        self.assertEqual(get_env_var("TEST_NUM_WORKERS", 4, int), 16)
        self.assertEqual(get_env_var("ABSENT_VAR", 4, int), 4)

    def test_priority_task_queue(self):
        code = RECIPES_BY_ID["priority-task-queue"]["code"]
        namespace = {}
        exec(code, namespace)
        PriorityQueue = namespace["PriorityQueue"]

        pq = PriorityQueue()
        pq.push("low-priority", priority=100)
        pq.push("high-priority", priority=10)
        pq.push("medium-priority", priority=50)

        self.assertEqual(len(pq), 3)
        self.assertEqual(pq.pop(), "high-priority")
        self.assertEqual(pq.pop(), "medium-priority")
        self.assertEqual(pq.pop(), "low-priority")
        self.assertIsNone(pq.pop())


if __name__ == "__main__":
    unittest.main()
