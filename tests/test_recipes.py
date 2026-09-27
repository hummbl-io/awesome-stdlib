import datetime
import json
import tempfile
import time
import unittest
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

    def test_python_json_hmac_signer(self):
        code = RECIPES_BY_ID["python-json-hmac-signer"]["code"]
        namespace = {}
        exec(code, namespace)
        sign_json_receipt = namespace["sign_json_receipt"]
        verify_json_receipt = namespace["verify_json_receipt"]

        secret = b"fleet-master-key-xyz"
        payload = {"b": 2, "a": 1, "z": [3, 2, 1]}
        sig = sign_json_receipt(secret, payload)
        self.assertIsInstance(sig, str)
        self.assertTrue(verify_json_receipt(secret, payload, sig))
        self.assertFalse(verify_json_receipt(secret, {"b": 3, "a": 1}, sig))

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

        # Cron uses Sunday=0/7 and Monday=1, unlike datetime.weekday().
        # 2026-09-21 was a Monday
        dt = datetime.datetime(2026, 9, 21, 14, 30)
        self.assertTrue(is_cron_due("30 14 * * 1", dt))
        self.assertTrue(is_cron_due("*/15 14 * * 1", dt))
        self.assertFalse(is_cron_due("0 14 * * 1", dt))

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

    def recipe_namespace(self, ident):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        recipe = next(row for row in data["recipes"] if row["id"] == ident)
        namespace = {}
        # Execute only these explicitly reviewed, local, side-effect-free recipe definitions.
        self.assertIn(ident, {"cron-pattern-matcher", "python-json-hmac-signer", "http-json-client"})
        exec(compile(recipe["code"], f"<recipe:{ident}>", "exec"), namespace)
        return namespace

    def test_cron_sunday_aliases_and_monday(self):
        due = self.recipe_namespace("cron-pattern-matcher")["is_cron_due"]
        sunday = datetime.datetime(2026, 9, 27)
        monday = datetime.datetime(2026, 9, 28)
        self.assertTrue(due("0 0 * * 0", sunday))
        self.assertTrue(due("0 0 * * 7", sunday))
        self.assertFalse(due("0 0 * * 0", monday))
        self.assertTrue(due("0 0 * * 1", monday))

    def test_cron_restricted_days_use_or_and_wildcards_use_and(self):
        due = self.recipe_namespace("cron-pattern-matcher")["is_cron_due"]
        self.assertTrue(due("0 0 13 * 1", datetime.datetime(2026, 9, 13)))
        self.assertTrue(due("0 0 13 * 1", datetime.datetime(2026, 9, 28)))
        self.assertFalse(due("0 0 13 * 1", datetime.datetime(2026, 9, 29)))
        self.assertFalse(due("0 0 * * 1", datetime.datetime(2026, 9, 13)))
        self.assertFalse(due("0 0 13 * *", datetime.datetime(2026, 9, 28)))

    def test_cron_lists_ranges_steps_and_field_validation(self):
        due = self.recipe_namespace("cron-pattern-matcher")["is_cron_due"]
        self.assertTrue(due("*/15 0,12 * 1-5/2 *", datetime.datetime(2026, 3, 1, 12, 30)))
        self.assertFalse(due("*/15 0,12 * 1-5/2 *", datetime.datetime(2026, 2, 1, 12, 30)))
        self.assertTrue(due("0 0 * */2 *", datetime.datetime(2026, 1, 1)))
        for invalid in ("*/0 * * * *", "60 * * * *", "* 24 * * *", "* * 0 * *",
                        "* * * 13 *", "* * * * 8", "* * * * 4-2", "* * * * mon",
                        "* * * *", "1/2 * * * *"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                due(invalid, datetime.datetime(2026, 9, 27))

    def test_json_hmac_roundtrip_tamper_and_nonfinite_rejection(self):
        ns = self.recipe_namespace("python-json-hmac-signer")
        sign, verify = ns["sign_json_receipt"], ns["verify_json_receipt"]
        signature = sign(b"test-key", {"n": 1, "text": "a  b"})
        self.assertTrue(verify(b"test-key", {"text": "a  b", "n": 1}, signature))
        self.assertFalse(verify(b"test-key", {"text": "a b", "n": 1}, signature))
        with self.assertRaises(ValueError):
            sign(b"test-key", {"n": float("nan")})

    def test_http_json_preserves_empty_object_payload(self):
        from unittest.mock import MagicMock, patch
        ns = self.recipe_namespace("http-json-client")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{}'
        with patch("urllib.request.urlopen", return_value=response) as request:
            ns["http_json_request"]("https://example.invalid", "POST", {})
        self.assertEqual(request.call_args.args[0].data, b'{}')



if __name__ == "__main__":
    unittest.main()
